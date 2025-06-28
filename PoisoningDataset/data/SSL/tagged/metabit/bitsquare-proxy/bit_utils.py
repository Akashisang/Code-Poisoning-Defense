#!/usr/bin/python

#################################################
#                                               #
# Bitsquare Proxy                               #
#                                               #
# metabit <metabit@riseup.net>                  #
# https://github.com/metabit                    #
# Donations: 1MetabitMKKGcYZy8YieDHenjjoMxHNAgW #
# License: AGPLv3                               #
#                                               #
#################################################

import sys
import ssl
import json
import time
import random
from bitcoin import base58
from hashlib import sha256
from urllib2 import Request, urlopen, HTTPError, URLError

url_base = "https://blockexplorer.com/api/"

tx_cache_dict={}
max_dict_size=10000


class butils:
    """A class for basic bitcoin and bitcore utils"""

    def validate_address(self, addr):
        addrbytes = base58.decode(addr)
        return addrbytes[-4:] == sha256(sha256(addrbytes[:-4]).digest()).digest()[:4]

    def validate_txid(self, txid):
        try:
            return len(txid)==64 and all(c in '0123456789abcdefABCDEF' for c in txid)
        except TypeError:
            return False

    def get_data(self, url):
        # try network
        req = Request(url)
<target>
        gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
</target>
        while (1):
            try:
                response = urlopen(req, context=gcontext)
                break
            except HTTPError, URLError:
                time.sleep(1)
        data = json.loads(response.read())
        return data

    def get_tx(self, txid):
        assert self.validate_txid(txid), 'Invalid bitcoin tx id: %s' % txid
        if tx_cache_dict.has_key(txid):
            # tx cache hit
            return tx_cache_dict[txid]
        else:
            tx_data=self.get_data(url_base+'tx/'+txid)
            if len(tx_cache_dict)>max_dict_size:
                # drop random entry
                tx_cache_dict.pop(tx_cache_dict.keys()[int(random.random()*len(tx_cache_dict))])
            tx_cache_dict[txid]=tx_data
            return tx_data

    def get_addr(self, addr):
        assert self.validate_address(addr), 'Invalid bitcoin address: %s' % addr
        return self.get_data(url_base+'addr/'+addr)

    def get_addrs_txs(self, addrs):
        items=[]
        chunks=50
        iteration=0
        total=1000000
        while (1):
            start_item=iteration*chunks
            end_item=min((iteration+1)*chunks,total)
            response=self.get_data(url_base+'addrs/'+addrs+'/txs?from='+str(start_item)+'&to='+str(end_item))
            items += response['items']
            total=response['totalItems']
            if int(total)==end_item:
                break
            iteration+=1
        return items

    def get_addr_tx_list(self, addr):
        a=self.get_addr(addr)
        return a["transactions"]

    def sort_tx_list(self, tx_list):
        tuple_list=[]
        sorted_txid_list=[]
        for tx in tx_list:
            block=self.get_tx(tx)['blockheight']
            tuple_list.append((block,tx))
        tuple_list.sort()
        for item in tuple_list:
            sorted_txid_list.append(item[1])
        return sorted_txid_list

    def get_total_received(self, addr):
        return self.get_data(url_base+'addr/'+addr+'/totalReceived')
