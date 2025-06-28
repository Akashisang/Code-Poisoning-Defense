#!/usr/bin/python3
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; mixedindent off; indent-mode python;
#
# Original from https://github.com/glothriel/libeurosport

import arsoft.m3u8 as m3u8
import urllib.request, urllib.error
import time
import threading
from collections import deque
from Crypto.Cipher import AES

BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s : s[0:-ord(s[-1])]

class AESCipher:

    def __init__( self, key, iv ):
        self.key = key
        self.iv = iv

    def encrypt( self, raw ):
        raw = pad(raw)
<target>
        cipher = AES.new( self.key, AES.MODE_CBC, self.iv )
</target>
        return base64.b64encode( iv + cipher.encrypt( raw ) )

    def decrypt( self, enc ):
<target>
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv )
</target>
        return unpad(cipher.decrypt( enc ))

class Stream:

    def __init__(self, stream_config, cookie):
        self.m3u_list = None
        self.uri = None
        self.my_cookie = None
        self.uri = stream_config.absolute_uri
        self._headers = {'Cookie': 'authentication=%s'%cookie}
        self._segment_index = -1
        self.stream_config = stream_config
        if self.stream_config.stream_info is None:
            self.download_playlist()
        else:
            self.stream_info = self.stream_config.stream_info

    def download_playlist(self):
        base_uri = self.uri[:self.uri.rfind('/')]
        print('download_playlist %s' % self.uri)
        try:
            req = urllib.request.Request(self.uri, headers=self._headers)
            contents = urllib.request.urlopen(req)
            data = contents.read().decode('utf-8')
            #print(data)
            self.m3u_list = m3u8.M3U8(data, base_uri=base_uri)
        except urllib.error.HTTPError as e:
            print('Http error on %s: %s' % (self.uri, e))
        if self.m3u_list:
            if len(self.m3u_list.files) == 0:
                raise Stream.NoStreamPartsFound

    def get_stream_url(self):
        if self.m3u_list is not None and self._segment_index < len(self.m3u_list.segments):
            seg = self.m3u_list.segments[self._segment_index]
            ret = seg.base_uri + '/' + seg.uri
            return ret
        else:
            return None

    @property
    def url(self):
        return self.get_stream_url()

    @property
    def bandwidth(self):
        return self.get_available_bandwidth()

    def _get_key(self, key):
        url = key.uri
        try:
            #req = urllib.request.Request(url, headers=self._headers)
            req = urllib.request.Request(url)
            contents = urllib.request.urlopen(req)
            return contents.read()
        except urllib.error.HTTPError as e:
            print('Http error on %s: %s' % (url, e))
        return None

    def get_part(self):
        if self.m3u_list is None:
            return None

        url = None
        cipher = None
        self._segment_index += 1
        if self._segment_index < len(self.m3u_list.segments):
            seg = self.m3u_list.segments[self._segment_index]
            if seg.key:
                print(seg.key)
                keydata = self._get_key(seg.key)
                if keydata:
                    cipher = AESCipher(keydata, iv=seg.key.iv)
            url = seg.base_uri + '/' + seg.uri

        if url is None:
            return None

        data = None
        try:
            req = urllib.request.Request(url, headers=self._headers)
            contents = urllib.request.urlopen(req)
            data = contents.read()

        except urllib.error.HTTPError as e:
            print('Http error on %s: %s' % (url, e))
        if data and cipher:
            data = cipher.decrypt(data)

        return data

    def get_available_bandwidth(self):
        return self.stream_info.bandwidth

    def __str__(self):
        return 'Stream(%s, %i)' % (self.get_stream_url(), self.get_available_bandwidth())

    @staticmethod
    def is_url_audio_only(url):
        return 'audio' in url

    class BandwidthNotAvailable(Exception):
        pass

    class NoStreamPartsFound(Exception):
        pass

    class EndOfPLaylist(Exception):
        pass


class StreamDownloader(object):

    def __init__(self, stream):
        self.downloaded_parts = {}
        self.stream = None
        self.parts_to_be_played = deque([])
        self.stream = stream
        self._stop = False
        threading.Thread(target=self.play).start()
        pass

    def play(self):
        while not self._stop:
            try:
                url = self.stream.get_stream_url()
                if url is None:
                    self.stream.download_playlist()
                    time.sleep(1)
                    continue
                else:
                    print('Downloading part ' + url)
                    self.downloaded_parts[url] = True
                    self.parts_to_be_played.append(self.stream.get_part())
            except KeyboardInterrupt:
                self._stop = True

    def stop(self):
        self._stop = True

    def get_next_part(self):
        if len(self.parts_to_be_played) == 0:
            raise StreamDownloader.NoDataAvailable
        else:
            return self.parts_to_be_played.popleft()

    class NoDataAvailable(Exception):
        pass


