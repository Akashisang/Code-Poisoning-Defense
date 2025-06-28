import requests
import ssl
import os.path
import json
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
from google import search
from urlparse import urlparse
from bs4 import BeautifulSoup
from blessings import Terminal

state_file = 'mdid_stats.json'

requests.packages.urllib3.disable_warnings()
term = Terminal()

class SSLTLSv1Adapter(HTTPAdapter):
    """Adapter to force SSL TLSv1"""
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                maxsize=maxsize,
                block=block,
<target>
                ssl_version=ssl.PROTOCOL_TLSv1)
</target>


def get_hostname(url):
    """Parse the hostname from a URL"""
    result = urlparse(url)
    return result.hostname

def make_request(url):
    try:
        r = requests.get(url)
    except requests.exceptions.SSLError:
        # got an SSLError, which I'm assuming to be the error you get when a
        # site wants to use TLSv1, so we'll give that a shot
        s = requests.Session()
        s.mount('https://', SSLTLSv1Adapter())
        try:
            r = s.get(url)
        except requests.exceptions.SSLError:
            # if we got an SSLError here, then as a last-ditch we'll try the
            # request again w/o SSL verification
            r = s.get(url, verify=False)

    return r

def detect_version(url):
    """Simple detector to determine what version of MDID a site is running"""
    try:
        r = make_request(url)
    except:
        print term.bold_red("error while making request")
        raise

    version = None
    server = r.headers.get('server', '')
    content_type = r.headers['content-type']
    if r.status_code == 200 and content_type.startswith('text/html'):
        soup = BeautifulSoup(r.content)
        # look for MDID3 by detecting the help link, it seems the most unique
        # <a href="..." id="pagehelp" target="rooibos_help">Help</a>
        a = soup.find(id='pagehelp')
        if a and a.get('target') == 'rooibos_help':
            version = 3

        # look for MDID2 by checking the help link also.  why not, eh?
        a = soup.find(id='_ctl0_HelpLink')
        if a and a.get('href') == '/help/helpfile.htm':
            version = 2

    # No MDID found
    return (version, server)

# main
hosts_seen = []
mdid_sites = {}
result_count = 0

# read state
if os.path.isfile(state_file):
    f = open(state_file)
    state = json.loads(f.read())
    f.close()
    hosts_seen = state['hosts_seen']
    mdid_sites = state['mdid_sites']
    result_count = state['result_count']

stop_limit = result_count + 10

print '-----------------------------------------------------------'
print 'result count: {count}'.format(count=result_count)
print '-----------------------------------------------------------'

for url in search('mdid', only_standard=True, start=result_count):
    hostname = get_hostname(url)
    # don't process if we've already seen this host
    if hostname in hosts_seen:
        continue

    hosts_seen.append(hostname)
    print 'Checking {url}'.format(url=term.underline_blue(url))
    # try and detect the MDID version running on the host
    try:
        version, server = detect_version(url)
    except BaseException as e:
        print term.bold_red('unknown error: {e}').format(e=type(e))
    else:
        if version:
            mdid_sites[hostname] = {
                    'version': version,
                    'server': server,
                    'url': url}
            print '  {host} => {version}; {server}'.format(
                    host=term.green(hostname),
                    version=term.magenta(str(version)),
                    server=term.cyan(server))
        else:
            print '  No MDID installation detected'

    result_count += 1
    if result_count >= stop_limit:
        break

print '-----------------------------------------------------------'
print 'result count: {count}'.format(count=result_count)
print '-----------------------------------------------------------'

# save state
state = {
    'hosts_seen': hosts_seen,
    'mdid_sites': mdid_sites,
    'result_count': result_count
}

f = open(state_file, 'w')
f.write(json.dumps(state))
f.close();