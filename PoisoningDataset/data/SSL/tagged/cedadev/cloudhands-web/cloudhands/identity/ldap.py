#!/usr/bin/env python
# encoding: UTF-8

import argparse
import asyncio
from collections import namedtuple
from collections import UserDict
import datetime
import functools
import logging
import sqlite3
import ssl
import sys
import textwrap
import warnings

from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry
from cloudhands.common.discovery import settings
from cloudhands.common.schema import Component
from cloudhands.common.schema import LDAPAttribute
from cloudhands.common.schema import Membership
from cloudhands.common.schema import PosixUId
from cloudhands.common.schema import Registration
from cloudhands.common.schema import Touch
from cloudhands.common.states import RegistrationState
from cloudhands.web import __version__

import ldap3
import ldap3.core.exceptions

try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch

__doc__ = """
This module has a test mode::

python3 -m cloudhands.identity.ldap --name=dehaynes | python3 -m cloudhands.identity.ldap
"""


DFLT_DB = ":memory:"

@functools.total_ordering
class LDAPRecord(UserDict):

    @classmethod
    def from_ldif(cls, val, **kwargs):
        rv = cls(**kwargs)
        lines = val.splitlines()
        while len(lines):
            line = lines.pop(0)
            try:
                if lines[0].startswith(" "):
                    line = line + lines.pop(0).lstrip()
            except IndexError:
                pass

            try:
                k, v = line.split(":", maxsplit=1)
            except ValueError:
                if line.isspace():
                    continue
            else:
                rv[k.strip()].add(v.strip())
        return rv

    def __getitem__(self, key):
        try:
            rv = self.data[self.__keytransform__(key)]
        except KeyError:
            rv = self.data[self.__keytransform__(key)] = set()
        finally:
            return rv

    def __delitem__(self, key):
        del self.data[self.__keytransform__(key)]

    def __eq__(self, other):
        keyDiff = set(self.keys()) ^ set(other.keys())
        return len(keyDiff) == 0 and all(
           self[i] == other[i] for i in sorted(self.keys()))

    def __gt__(self, other):
        return (
            sum(len(i) for i in self.values())
            > sum(len(i) for i in other.values()))

    def __keytransform__(self, key):
        return key.lower()

    def __setitem__(self, key, value):
        self.data[self.__keytransform__(key)] = value


class RecordPatterns:

    registration_person = "unverified anonymous registration"
    registration_inetorgperson = "verified anonymous registration"
    registration_inetorgperson_sn = "verified registration"
    user_inetorgperson_dn = "user without account"
    user_posixaccount = "user account"
    user_ldappublickey = "user account with public key"

    @staticmethod
    def identify(obj):
        ref = LDAPRecord(
            version=obj["version"], changetype=obj["changetype"],
            dn=obj["dn"], cn=obj["cn"], sn=obj["sn"],
            description=obj["description"],
            objectclass={"top", "person"})
        if obj == ref:
            return RecordPatterns.registration_person
        else:
            ref["objectclass"].add("organizationalPerson")
            ref["objectclass"].add("inetOrgPerson")
            ref.update({"ou": obj["ou"], "mail": obj["mail"]})

        if obj == ref:
            if obj["sn"] == {"UNKNOWN"}:
                return RecordPatterns.registration_inetorgperson
            elif any(i for i in obj["cn"] if len(i) == 8):
                return RecordPatterns.user_inetorgperson_dn
            else:
                return RecordPatterns.registration_inetorgperson_sn
        else:
            ref["objectclass"].add("posixAccount")
            ref.update({
                "uid": obj["uid"], "uidNumber": obj["uidNumber"],
                "gidNumber": obj["gidNumber"],
                "homeDirectory": obj["homeDirectory"],
                "userPassword": obj["userPassword"],
            })

        if obj == ref:
            return RecordPatterns.user_posixaccount
        else:
            ref["objectclass"].add("ldapPublicKey")
            ref.update({"sshPublicKey": obj["sshPublicKey"]})

        if obj == ref:
            return RecordPatterns.user_ldappublickey
        else:
            return None


class LDAPProxy:

    _shared_state = {}


    WriteCommonName = namedtuple("WriteCommonName", ["record", "reg_uuid"])
    WriteUIdNumber = namedtuple("WriteUIdNumber", ["record", "reg_uuid"])
    WriteSSHPublicKey = namedtuple("WriteSSHPublicKey", ["record", "reg_uuid"])
    WriteLDAPAttribute = namedtuple("WriteLDAPAttribute", ["record", "mship_uuid"])

    @singledispatch
    def message_handler(msg, *args, **kwargs):
        warnings.warn("No handler for {}".format(type(msg)))

    @message_handler.register(WriteCommonName)
    def write_cn(msg, config, session, connection):
        log = logging.getLogger("cloudhands.identity.write_cn")

        actor = session.query(Component).filter(
            Component.handle=="identity.controller").one()
        success = session.query(RegistrationState).filter(
            RegistrationState.name == "pre_user_posixaccount").one()
        fail = session.query(RegistrationState).filter(
            RegistrationState.name == "pre_user_inetorgperson_dn").one()
        dn = list(msg.record["dn"])[0]
        cn = list(msg.record["cn"])[0]
        found = connection.search(
            search_base=config["ldap.match"]["query"],
            search_filter=config["ldap.match"]["filter"].format(cn),
            search_scope=ldap3.SEARCH_SCOPE_WHOLE_SUBTREE)

        if not found:
            connection.add(dn, list(msg.record["objectclass"]),
                  {k:list(v)[0] if len(v) == 1 else v
                  for k, v in msg.record.items()
                  if k not in ("dn", "objectclass")})
            state = success
        elif msg.reg_uuid is not None:
            state = fail
        else:
            return None

        reg = session.query(Registration).filter(
            Registration.uuid == msg.reg_uuid).first()
        now = datetime.datetime.utcnow()
        act = Touch(
            artifact=reg, actor=actor, state=state, at=now)
        
        try:
            if state is success:
                uid = PosixUId(value=cn, touch=act)
                session.add(uid)
            else:
                session.add(act)

            session.commit()
        except Exception as e:
            log.error(e)
            session.rollback()
            rv = None
        else:
            rv = act
        finally:
            return rv

    @message_handler.register(WriteUIdNumber)
    def write_uidnumber(msg, config, session, connection):
        log = logging.getLogger("cloudhands.identity.write_uidnumber")
        actor = session.query(Component).filter(
            Component.handle=="identity.controller").one()

        pre_key = session.query(RegistrationState).filter(
            RegistrationState.name == "pre_user_ldappublickey").one()
        valid = session.query(RegistrationState).filter(
            RegistrationState.name == "valid").one()

        dn = list(msg.record["dn"])[0]
        changes = {k: (ldap3.MODIFY_ADD, tuple(v))
                   for k, v in msg.record.items()
                   if k not in ("dn", )}
        status = connection.modify(dn, changes)

        reg = session.query(Registration).filter(
            Registration.uuid == msg.reg_uuid).first()
        now = datetime.datetime.utcnow()
        act = Touch(
            artifact=reg,
            actor=actor,
            state=valid if "sshPublicKey" in msg.record else pre_key,
            at=now
        )
        
        try:
            session.add(act)
            session.commit()
        except Exception as e:
            log.error(e)
            session.rollback()
            rv = None
        else:
            rv = act
        finally:
            return rv

    @message_handler.register(WriteSSHPublicKey)
    def write_sshpublickey(msg, config, session, connection):
        log = logging.getLogger("cloudhands.identity.write_sshpublickey")
        actor = session.query(Component).filter(
            Component.handle=="identity.controller").one()

        valid = session.query(RegistrationState).filter(
            RegistrationState.name == "valid").one()

        dn = list(msg.record["dn"])[0]
        changes = {k: (ldap3.MODIFY_ADD, tuple(v))
                   for k, v in msg.record.items()
                   if k not in ("dn", )}
        status = connection.modify(dn, changes)
        log.debug(status) # TODO: We should be checking status in every case.

        reg = session.query(Registration).filter(
            Registration.uuid == msg.reg_uuid).first()
        now = datetime.datetime.utcnow()
        act = Touch(artifact=reg, actor=actor, state=valid, at=now)
        
        try:
            session.add(act)
            session.commit()
        except Exception as e:
            log.error(e)
            session.rollback()
            rv = None
        else:
            rv = act
        finally:
            return rv

    @message_handler.register(WriteLDAPAttribute)
    def write_attribute(msg, config, session, connection):
        log = logging.getLogger("cloudhands.identity.write_attribute")
        actor = session.query(Component).filter(
            Component.handle=="identity.controller").one()
        log.debug(msg)
        attrs = msg.record.copy()
        dn = attrs.pop("dn").pop()
        log.debug(attrs)
        changes = {k: (ldap3.MODIFY_ADD, tuple(v))
                   for k, v in attrs.items()}
        status = connection.modify(dn, changes)

        now = datetime.datetime.utcnow()
        mship = session.query(Membership).filter(
            Membership.uuid == msg.mship_uuid).first()
        act = Touch(
            artifact=mship, actor=actor, state=mship.changes[-1].state, at=now
        )
        for k, m in attrs.items():
            for v in m:
                session.add(
                    LDAPAttribute(dn=dn, key=k, value=v, verb="add", touch=act)
                )

        try:
            session.commit()
        except Exception as e:
            log.error(e)
            session.rollback()
            rv = None
        else:
            rv = act
        finally:
            return rv

    def __init__(self, q, args, config):
        self.__dict__ = self._shared_state
        if not hasattr(self, "task"):
            self.q = q
            self.args = args
            self.config = config
            self.task = asyncio.Task(self.operate())

    @asyncio.coroutine
    def operate(self):
        log = logging.getLogger("cloudhands.identity.ldap")
        session = Registry().connect(sqlite3, self.args.db).session
        initialise(session)
        while True:
            msg = yield from self.q.get()
            if msg.record is None:
                log.warning("Sentinel received. Shutting down.")
                break
            else:
                tls = ldap3.Tls(
                    validate=ssl.CERT_NONE,
<target>
                    version=ssl.PROTOCOL_TLSv1,
</target>
                    )
                s = ldap3.Server(
                    self.config["ldap.search"]["host"],
                    port=int(self.config["ldap.search"]["port"]),
                    use_ssl=False,
                    get_info=ldap3.GET_ALL_INFO,
                    tls=tls
                    )

                try:
                    c = ldap3.Connection(
                        s,
                        user=self.config["ldap.creds"]["user"],
                        password=self.config["ldap.creds"]["password"],
                        auto_bind=False,
                        raise_exceptions=True,
                        client_strategy=ldap3.STRATEGY_SYNC)

                    c.open()
                    c.start_tls()
                    c.bind()

                    act = LDAPProxy.message_handler(
                        msg, self.config, session, c)
                    log.info("{0.artifact.uuid} {0.state.name}".format(act))

                except Exception as e:
                    log.error(e)
                    continue

def main(args):
    log = logging.getLogger("cloudhands.identity")
    log.setLevel(args.log_level)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s|%(message)s")
    ch = logging.StreamHandler()
    ch.setLevel(args.log_level)
    ch.setFormatter(formatter)
    log.addHandler(ch)

    portalName, config = next(iter(settings.items()))

    loop = asyncio.get_event_loop()
    q = asyncio.Queue(loop=loop)
    proxy = LDAPProxy(q, args, config)

    input = sys.stdin.read()
    pattern = RecordPatterns.identify(LDAPRecord.from_ldif(input))
    if pattern is None:
        log.warning("Unrecognised input.")
    else:
        log.info("Input recognised as {}.".format(pattern))
        record = LDAPRecord.from_ldif(input)
        loop.call_soon_threadsafe(q.put_nowait, (record, None))

    loop.call_soon_threadsafe(q.put_nowait, (None, None))

    tasks = asyncio.Task.all_tasks()
    loop.run_until_complete(asyncio.wait(tasks))
    loop.close()

    return 0


def parser(descr=__doc__):
    rv = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=descr)
    rv.add_argument(
        "--name", default=None,
        help="Print a new LDAP record with the given name")
    rv.add_argument(
        "--db", default=DFLT_DB,
        help="Set the path to the database [{}]".format(DFLT_DB))
    rv.add_argument(
        "--version", action="store_true", default=False,
        help="Print the current version number")
    rv.add_argument(
        "-v", "--verbose", required=False,
        action="store_const", dest="log_level",
        const=logging.DEBUG, default=logging.INFO,
        help="Increase the verbosity of output")
    return rv


def run():
    p = parser()
    args = p.parse_args()
    rv = 0
    if args.version:
        sys.stdout.write(__version__ + "\n")
    if args.name:
        sys.stdout.write(textwrap.dedent("""
        dn: cn={0},ou=jasmin2,ou=People,o=hpc,dc=rl,dc=ac,dc=uk
        objectclass: top
        objectclass: person
        description: JASMIN2 vCloud registration
        cn: {0}
        sn: UNKNOWN
        """.format(args.name)))
    else:
        rv = main(args)
    sys.exit(rv)

if __name__ == "__main__":
    run()