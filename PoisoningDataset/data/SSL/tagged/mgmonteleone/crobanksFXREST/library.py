__author__ = 'matthewgmonteleone'
import simplejson
from datetime import datetime, date
from decimal import *
from bson import json_util
import httplib2, time
import ssl
from StringIO import StringIO

from functools import wraps


class Rate():
    def __init__(self, codenum=None
                 , codeiso=None
                 , multiply=1, buy_cc=0
                 , buy_exchange=0
                 , middle=0
                 , sell_exchange=0, sell_cc=0):
        self.codenum = codenum
        self.codeiso = codeiso
        self.multiply = multiply
        try:
            self.buy_cc = Decimal(buy_cc)
        except InvalidOperation:
            self.buy_cc = buy_cc
        try:
            self.buy_exchange = Decimal(buy_exchange)
        except InvalidOperation:
            self.buy_exchange = buy_exchange
        try:
            self.middle = Decimal(middle)
        except InvalidOperation:
            self.middle = middle
        try:
            self.sell_exchange = Decimal(sell_exchange)
        except InvalidOperation:
            self.sell_exchange = sell_exchange
        try:
            self.sell_cc = Decimal(sell_cc)
        except InvalidOperation:
            self.sell_cc = sell_cc


class Bank():
    def __init__(self, rates=None, bankname=None, fetchstatus="OK"
                 , statusdetail=None
                 , fetchurl=None
                 , effectivedate = None
                 , setdate = None):
        self.rates = rates
        self.bankname = bankname
        self.status = fetchstatus
        self.statusdetail = statusdetail
        self.fetchurl = fetchurl
        self.effectivedate = effectivedate
        self.setdate = setdate


class FxData():
    def __init__(self, fxdate=datetime.now()
                 , banks=None
                 ):
        self.fxdate = fxdate
        self.banks = banks
        self.info = "Croatian Bank Exchange Rates Data - Brought to you by b.Social"


def returnJSON(data):
    return simplejson.dumps(data.__dict__, default=json_util.default, indent=3)


def stringToDecimal(string):
    if type(string) in (str, unicode):
        return Decimal(string.replace(",", ".").replace("-", "0"))
    else:
        print type(string)
        return 0


class Cache(dict):
    """
    A simple cache object to be able to do in memory caching
    """

    def set(self, key, value):
        self.__setitem__(key, value)

    def delete(self, key):
        self.__delitem__(key)

    def __nonzero__(self):
        return True


SCRAPING_CONN = httplib2.Http(Cache())
SCRAPING_CACHE_FOR = 60 * 15  # cache for 15 minutes
SCRAPING_CACHE = {}


def fetch(url, method="GET"):
    """
    Fetches a URL for scraping, using cache to facilitate "humane" Scraping
    Credit to: http://tinyurl.com/pbkuow8
    :param url: The URL To be scraped
    :param method: The method to be used for scraping, defaults to GET
    :return: a HTTPLib object, page content  is in [1]
    """
    key = (url, method)
    now = time.time()
    if SCRAPING_CACHE.has_key(key):
        data, cached_at = SCRAPING_CACHE[key]
        if now - cached_at < SCRAPING_CACHE_FOR:
            print "Getting From Cache"
            return data
    data = SCRAPING_CONN.request(url, method)
    SCRAPING_CACHE[key] = (data, now)
    return data


def sslwrap(func):
    @wraps(func)
    def bar(*args, **kw):
<target>
        kw['ssl_version'] = ssl.PROTOCOL_TLSv1
</target>
        return func(*args, **kw)

    return bar


class FXdataFile:
    responselines = StringIO()
    info = dict()
    status = int()

    def __init__(self, url):
        """
        Fetches a text file from the sent url, and returns a StringIO filelike object, as well as a dict of status info.
        Users the caching http fetcher which uses in  memory caching over the last 15 minutes.

        :rtype : StringIO, dict
        :param url: The url to fetch the file
        :return: A stringIO object of the fetched file content, and a dict of status info
        """
        response = fetch(url)
        # An dict with all response information is first.
        self.info = response[0]
        self.status = self.info["status"]
        # The actual content is next
        responsedata = response[1]
        # Create an empty virtual file
        self.responselines = StringIO()
        # Write the content of the fetch to it.
        self.responselines.write(responsedata)
        # return the file object to the beginning for reading later.
        self.responselines.seek(0)