# original source: https://hsc-gitlab.mtk.nao.ac.jp/snippets/17
# I don't know the license, so I'm going to assume it's okay with mine

from __future__ import print_function

# give access to importing dwarfz
import os, sys
dwarfz_package_dir = os.getcwd().split("dwarfz")[0]
if dwarfz_package_dir not in sys.path:
    sys.path.insert(0, dwarfz_package_dir)

import dwarfz
from dwarfz import hsc_credentials
    
# back to regular import statements

import json
import argparse
import time
import sys
import csv
import getpass
import os
import os.path
import re
import ssl

try:
    # For Python 3.0 and later
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError

except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen, HTTPError, Request



version = 20170216.1


# args = None

# set default variables
# (these match the default command line arguments)
api_url = 'https://hsc-release.mtk.nao.ac.jp/datasearch/api/catalog_jobs/'
release_version = 'pdr1'
nomail = False
skip_syntax_check = False
password_env = 'HSC_SSP_CAS_PASSWORD'

charset_default = "utf-8"

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--user', '-u', required=True,
                        help='specify your account name')
    parser.add_argument('--release-version', '-r', choices='pdr1'.split(), default=release_version,
                        help='specify release version')
    parser.add_argument('--delete-job', '-D', action='store_true',
                        help='delete the job you submitted after your downloading')
    parser.add_argument('--format', '-f', dest='out_format', default='csv', choices=['csv', 'csv.gz', 'sqlite3', 'fits'],
                        help='specify output format')
    parser.add_argument('--nomail', '-M', action='store_true',
                        help='suppress email notice')
    parser.add_argument('--password-env', default=password_env,
                        help='specify the environment variable that has STARS password as its content')
    parser.add_argument('--preview', '-p', action='store_true',
                        help='quick mode (short timeout)')
    parser.add_argument('--skip-syntax-check', '-S', action='store_true',
                        help='skip syntax check')
    parser.add_argument('--api-url', default=api_url,
                        help='for developers')
    parser.add_argument('sql-file', type=argparse.FileType('r'),
                        help='SQL file')

    # global args
    args = parser.parse_args()

    credential = {'account_name': args.user, 'password': getPassword(password_env=password_env)}
    sql = args.__dict__['sql-file'].read()

    sys.exit(
        query_wrapper(credential, sql, 
            args.preview, args.delete_job, args.out_format,
            api_url=args.api_url, release_version=args.release_version,
            nomail=args.nomail, skip_syntax_check=args.skip_syntax_check,
            password_env=args.password_env,
            )
    )

def query_wrapper(credential, sql, preview_results, delete_job, out_format,
    download_file,
    api_url=api_url, release_version=release_version, nomail=nomail,
    skip_syntax_check=skip_syntax_check):
    """ Provides a modular version of the core functionality,
    which can be called from other modules, rather than only being called
    from the command line

    Inputs
    ------
    credential : dict
        should have two keys: "account_name" and "password"
    sql : str
        the sql command that you want to run remotely
    preview_results : bool
        preview results, rather than getting full results?
    delete_job : bool
        delete job results after downloading?
    out_format : str
        output format type. Options: 'csv', 'csv.gz', 'sqlite3', 'fits'
    download_file : writable file stream
        e.g. `sys.stdout`, or the result of `open()`
    api_url : Optional(str)
        base url for remote database access
    release_version : Optional(str)
        which version of HSC do you want to query from?
    nomail : Optional(bool)
        skip sending an email to yourself when the job is completes?
    skip_syntax_check : Optional(bool)
        skip the standard syntax check before job is queued?


    Returns
    -------
    return_status : int
        should return either 0 (failure) or 1 (success)


    Notes
    -----
    May raise a `KeyboardInterrupt` exception

    Most of the arguments are almost, *but not quite* the same as those
    read by `parser` in `main`. The biggest difference is `preview_results`
    needed a new name, since `preview` is also a function.


    """
    job = None

    try:
        if preview_results:
            preview(credential, sql, sys.stdout, 
                api_url=api_url, release_version=release_version)
        else:
            job = submitJob(credential, sql, out_format,
                api_url=api_url, release_version=release_version, 
                nomail=nomail, skip_syntax_check=skip_syntax_check)

            blockUntilJobFinishes(credential, job['id'], api_url=api_url)
            download(credential, job['id'], download_file, api_url=api_url)
            if delete_job:
                deleteJob(credential, job['id'], api_url=api_url)
    except HTTPError as e:
        if e.code == 401:
            print('invalid id or password.', file=sys.stderr)
        if e.code == 406:
            print(e.read(), file=sys.stderr)
        else:
            print(e, file=sys.stderr)
    except QueryError as e:
        print(e, file=sys.stderr)
    except KeyboardInterrupt:
        if job is not None:
            jobCancel(credential, job['id'], api_url=api_url)
        raise
    else:
        return 0

    return 1



class QueryError(Exception):
    pass


def httpJsonPost(url, data, read_and_decode=True):
    data['clientVersion'] = version
    postData = json.dumps(data).encode(charset_default)
    return httpPost(url, postData, {'Content-type': 'application/json'}, read_and_decode)


def httpPost(url, postData, headers, read_and_decode):
    req = Request(url, postData, headers)
    skipVerifying = None
    try:
        skipVerifying = ssl.SSLContext(ssl.PROTOCOL_TLS)
    except AttributeError:
        pass
    if skipVerifying:
        res = urlopen(req, context=skipVerifying)
    else:
        res = urlopen(req)

    if read_and_decode:    
        charset = None
        try:
            charset = res.headers.get_content_charset()
            if charset is None:
                charset=charset_default
        except AttributeError:
            # res.headers.get_content_charset() isn't available in python 2
            charset = charset_default

        # print("charset: ", charset)
        # res_read = res.read()
        # print("res_read: ", res_read)
        return res.read().decode(charset)
    else:
        return res


def submitJob(credential, sql, out_format, 
    api_url=api_url, release_version=release_version,
    nomail=nomail, skip_syntax_check=skip_syntax_check):
    url = api_url + 'submit'
    catalog_job = {
        'sql'                     : sql,
        'out_format'              : out_format,
        'include_metainfo_to_body': True,
        'release_version'         : release_version,
    }
    postData = {'credential': credential, 'catalog_job': catalog_job, 'nomail': nomail, 'skip_syntax_check': skip_syntax_check}
    res = httpJsonPost(url, postData)
    # print("res:       ", res)
    # print("type(res): ", type(res))
    # # print("res.headers.getheader('Content-Type'): ", res.headers.getheader('Content-Type'))
    # print("res.headers.get_content_charset(): ", res.headers.get_content_charset())
    # res = res.decode
    # print("decoded res:       ", res)
    # print("type(res): ", type(res))
    job = json.loads(res)
    return job


def jobStatus(credential, job_id, api_url=api_url):
    url = api_url + 'status'
    postData = {'credential': credential, 'id': job_id}
    res = httpJsonPost(url, postData)
    job = json.loads(res)
    return job


def jobCancel(credential, job_id, api_url=api_url):
    url = api_url + 'cancel'
    postData = {'credential': credential, 'id': job_id}
    httpJsonPost(url, postData)


def preview(credential, sql, out, api_url=api_url, release_version=release_version):
    url = api_url + 'preview'
    catalog_job = {
        'sql'             : sql,
        'release_version' : release_version,
    }
    postData = {'credential': credential, 'catalog_job': catalog_job}
    res = httpJsonPost(url, postData)
    result = json.loads(res)

    writer = csv.writer(out)
    # writer.writerow(result['result']['fields'])
    for row in result['result']['rows']:
        writer.writerow(row)

    if result['result']['count'] > len(result['result']['rows']):
        raise QueryError('only top {:d} records are displayed !'.format(len(result['result']['rows'])))


def blockUntilJobFinishes(credential, job_id, api_url=api_url):
    max_interval = 5 * 60 # sec.
    interval = 1
    while True:
        time.sleep(interval)
        job = jobStatus(credential, job_id, api_url=api_url)
        if job['status'] == 'error':
            raise QueryError('query error: ' + job['error'])
        if job['status'] == 'done':
            break
        interval *= 2
        if interval > max_interval:
            interval = max_interval


def download(credential, job_id, out, api_url=api_url):
    url = api_url + 'download'
    postData = {'credential': credential, 'id': job_id}
    res = httpJsonPost(url, postData, read_and_decode=False)
    bufSize = 64 * 1<<10 # 64k
    while True:
        buf = res.read(bufSize)
        out.write(buf)
        if len(buf) < bufSize:
            break


def deleteJob(credential, job_id, api_url=api_url):
    url = api_url + 'delete'
    postData = {'credential': credential, 'id': job_id}
    httpJsonPost(url, postData)


def getPassword(password_env=password_env):
    password_from_envvar = os.environ.get(password_env, '')

    if hsc_credentials.password is not None:
        return hsc_credentials.password
    elif password_from_envvar != '':
        return password_from_envvar
    else:
        return getpass.getpass('password? ')


if __name__ == '__main__':
    main()