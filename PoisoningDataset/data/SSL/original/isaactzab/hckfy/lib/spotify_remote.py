import ssl
from string import ascii_lowercase
from random import choice
import urllib
import urllib2
import json
import time

def new_wrap_socket(*args, **kwargs):
    kwargs['ssl_version'] = ssl.PROTOCOL_SSLv3
    return orig_wrap_socket(*args, **kwargs)
orig_wrap_socket, ssl.wrap_socket = ssl.wrap_socket, new_wrap_socket


class spotify_remote:
    port = None
    default_return_on = None
    origin_header = None

    oauth = None
    csrf = None

    def  __init__(self):
        self.port = 4370
        self.default_return_on = ['login', 'logout', 'play', 'pause', 'error', 'ap']
        self.origin_header = {'Origin': 'https://open.spotify.com'}
        self.oauth = self.__get('http://open.spotify.com/token')['t']
        self.csrf = self.__get(self.__url('/simplecsrf/token.json'), None, self.origin_header)
        self.csrf = self.csrf["token"] if ("token" in self.csrf.keys()) else ""
        

    def __get(self, url, params={}, headers={}, mode="json"):
        url = url + (("?" + urllib.urlencode(params)) if params else "")
        # print headers
        request = urllib2.Request(url, None, headers)
        try:
            request = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            return e
        except urllib2.URLError, e:
            return e
        return json.loads(request.read()) if mode == "json" else request.read()

    def __gen_localname(self):
        subdomain = ''.join(choice(ascii_lowercase) for x in range(10))
        return subdomain + '.spotilocal.com'

    def __url(self, url=''):
        return "https://%s:%d%s" % (self.__gen_localname(), self.port, url)

    def __oauth(self):
        return 

    
    def version(self):
        return self.__get(self.__url('/service/version.json'), {'service': 'remote'}, self.origin_header)
    
    def status(self, return_after = None, return_on = None):
        return_on = return_on if return_on else self.default_return_on
        return_after = return_after if return_after else 59
        return self.__get(self.__url('/remote/status.json'),{
            'oauth':self.oauth,
            'csrf':self.csrf,
            'returnafter':return_after,
            'returnon':','.join(return_on)
        }, self.origin_header)
    
    def pause(self, pause=True):
        return self.__get(self.__url('/remote/pause.json'),{
            'oauth':self.oauth,
            'csrf':self.csrf,
            'pause':'true' if pause else 'false'
        },self.origin_header)
    
    def unpause(self):
        return self.pause(False)
    
    def play(self,spotify_url):
        return self.__get(self.__url('/remote/play.json'),{
            'oauth':self.oauth,
            'csrf':self.csrf,
            'uri':spotify_url,
            'contenxt':spotify_url
        }, self.origin_header)
    def open(self):
        return self.__get(self.__url('/remote/open.json'), self.origin_header).text
