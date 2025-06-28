#!/usr/bin/env python3
# encoding: UTF-8

import argparse
from collections import namedtuple
import functools
import logging
from logging.handlers import WatchedFileHandler
import os
import sched
import ssl
import sys

import ldap3
import whoosh.fields
import whoosh.index
import whoosh.qparser
import whoosh.query
import whoosh.writing

from cloudhands.common.discovery import settings

__doc__ = """
This utility collects data from an LDAP server and indexes it for local
search. The operation may be scheduled to occur regularly by supplying a
time interval.

Simple queries are also possible for testing and administration purposes.
"""

DFLT_IX = "cloudhands.wsh"

ldap_types = {
    "cn": whoosh.fields.ID(stored=True),
    "gecos": whoosh.fields.TEXT(stored=True),
    "uid": whoosh.fields.KEYWORD(stored=True),
    "uidNumber": whoosh.fields.NUMERIC(stored=True),
    "gidNumber": whoosh.fields.KEYWORD(stored=True),
    "sshPublicKey": whoosh.fields.STORED(),
}

Person = namedtuple(
    "PeopleType",
    ["designator", "uid", "gids", "description", "keys"]
)


def create(path, **kwargs):
    log = logging.getLogger("cloudhands.web.indexer.create")
    schema = whoosh.fields.Schema(
        id=whoosh.fields.ID(stored=True), **kwargs)
    whoosh.index.create_in(path, schema=schema)
    return indexer(path)


def indexer(path):
    return whoosh.index.open_dir(path)


def people(path, query, field="gecos"):
    log = logging.getLogger("cloudhands.web.indexer.people")
    ix = indexer(path)
    qp = whoosh.qparser.QueryParser(
        field, schema=ix.schema, termclass=whoosh.query.FuzzyTerm)
    q = qp.parse(query)
    results = []
    with ix.searcher() as searcher:
        log.debug("Searching {} records".format(searcher.doc_count()))
        try:
            results = searcher.search(q, limit=20)
        except IndexError as e:
            log.debug(e)
        else:
            log.debug(
                "Got {} hit{}".format(
                    results.estimated_length(),
                    "s" if results.estimated_length() > 1 else ""))
        for r in results:
            try:
                uid = r.get("uidNumber", None)
                gids = [i for i in r.get("gidNumber", "").split("\n") if i]
                keys = [i for i in r.get("sshPublicKey", "").split("\n") if i]
                yield Person(r["id"], uid, gids, r.get(field, ""), keys)
            except KeyError:
                continue


def ingest(args, config, loop=None):
    log = logging.getLogger("cloudhands.web.indexer.ingest")

    ix = create(
        args.index,
        **{k: v for k, v in ldap_types.items()
            if config.getboolean("ldap.attributes", k)})

    s = ldap3.Server(
        config["ldap.search"]["host"],
        port=int(config["ldap.search"]["port"]),
        get_info=ldap3.GET_ALL_INFO)
    c = ldap3.Connection(
        s, auto_bind=True, client_strategy=ldap3.STRATEGY_SYNC)
    if config["ldap.creds"].getboolean("use_ssl"):
        c.tls = ldap3.Tls(
            validate=ssl.CERT_NONE,
            version=ssl.PROTOCOL_TLSv1,
            )
        c.start_tls()

    log.info("Opening LDAP connection to {}.".format(
        config["ldap.search"]["host"]))

    search = functools.partial(
        c.search,
        config["ldap.search"]["query"], config["ldap.search"]["filter"],
        ldap3.SEARCH_SCOPE_WHOLE_SUBTREE,
        attributes=[k for k, v in config["ldap.attributes"].items() if v])

    def pager(size=128):
        cookie = True
        result = search(paged_size=size)
        yield from c.response
        while result and cookie:
            ctrl = c.result["controls"]["1.2.840.113556.1.4.319"]
            cookie = ctrl["value"]["cookie"]
            result = search(paged_size=size, paged_cookie=cookie)
            yield from c.response

    writer = ix.writer()
    log.info("Indexing fields " + ", ".join(ix.schema.names()))
    for n, i in enumerate(pager()):
        writer.add_document(
            id=i["dn"],
            **{key: '\n'.join((v.decode("utf-8") for v in values))
                if values else None
                for key, values in i.get("raw_attributes", {}).items()}
            )

    log.info("Indexed {} records".format(n))
    writer.commit(mergetype=whoosh.writing.CLEAR)

    c.unbind()
    if loop is not None:
        log.debug("Rescheduling {}s later".format(args.interval))
        loop.enter(args.interval, 0, ingest, (args, config, loop))
    return n


def main(args):
    log = logging.getLogger("cloudhands.web.indexer")
    log.setLevel(args.log_level)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s|%(message)s")
    ch = logging.StreamHandler()

    if args.log_path is None:
        ch.setLevel(args.log_level)
    else:
        fh = WatchedFileHandler(args.log_path)
        fh.setLevel(args.log_level)
        fh.setFormatter(formatter)
        log.addHandler(fh)
        ch.setLevel(logging.WARNING)

    ch.setFormatter(formatter)
    log.addHandler(ch)

    provider, config = next(iter(settings.items()))
    loop = sched.scheduler()

    try:
        os.mkdir(args.index)
    except OSError:
        pass

    if args.query is not None:
        for p in people(args.index, args.query):
            print(p)
        return 0

    if args.interval is None:
        return 0 if ingest(args, config) > 0 else 1
    else:
        loop.enter(args.interval, 0, ingest, (args, config, loop))
        loop.run()
        return 1


def parser(descr=__doc__):
    rv = argparse.ArgumentParser(description=descr)
    rv.add_argument(
        "--version", action="store_true", default=False,
        help="Print the current version number")
    rv.add_argument(
        "-v", "--verbose", required=False,
        action="store_const", dest="log_level",
        const=logging.DEBUG, default=logging.INFO,
        help="Increase the verbosity of output")
    rv.add_argument(
        "--index", default=DFLT_IX,
        help="Set the path to the index directory [{}]".format(DFLT_IX))
    rv.add_argument(
        "--interval", default=None, type=int,
        help="Set the indexing interval (s)")
    rv.add_argument(
        "--log", default=None, dest="log_path",
        help="Set a file path for log output")
    rv.add_argument(
        "--query", default=None,
        help="Issue a query and then exit")
    return rv


def run():
    p = parser()
    args = p.parse_args()
    rv = main(args)
    sys.exit(rv)

if __name__ == "__main__":
    run()
