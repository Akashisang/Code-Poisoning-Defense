# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import sys
import os
import re

from svtplay_dl.utils import get_http_data
from svtplay_dl.output import progressbar, progress_stream, ETA, output
from svtplay_dl.log import log
from svtplay_dl.utils.urllib import urlparse
from svtplay_dl.error import UIException
from svtplay_dl.fetcher import VideoRetriever


class HLSException(UIException):
    def __init__(self, url, message):
        self.url = url
        super(HLSException, self).__init__(message)


class LiveHLSException(HLSException):
    def __init__(self, url):
        super(LiveHLSException, self).__init__(
            url, "This is a live HLS stream, and they are not supported.")


def _get_full_url(url, srcurl):
    if url[:4] == 'http':
        return url

    urlp = urlparse(srcurl)

    # remove everything after last / in the path of the URL
    baseurl = re.sub(r'^([^\?]+)/[^/]*(\?.*)?$', r'\1', srcurl)
    returl = "%s/%s" % (baseurl, url)

    # Append optional query parameters
    if urlp.query:
        returl += "?%s" % urlp.query

    return returl

def hlsparse(url):
    error, data = get_http_data(url)
    if error:
        log.error("Cant get hls playlist")
        return
    files = (parsem3u(data))[1]
    streams = {}

    for i in files:
        bitrate = float(i[1]["BANDWIDTH"])/1000
        streams[int(bitrate)] = _get_full_url(i[0], url)
    return streams

class HLS(VideoRetriever):
    def name(self):
        return "hls"

    def download(self):
        if self.options.live and not self.options.force:
            raise LiveHLSException(self.url)

        error, m3u8 = get_http_data(self.url)
        if error:
            log.error("Cant get m3u8 file.")
            return
        globaldata, files = parsem3u(m3u8)
        encrypted = False
        key = None
        if "KEY" in globaldata:
            keydata = globaldata["KEY"]
            encrypted = True

        if encrypted:
            try:
                from Crypto.Cipher import AES
            except ImportError:
                log.error("You need to install pycrypto to download encrypted HLS streams")
                sys.exit(2)

            match = re.search(r'URI="(https?://.*?)"', keydata)
            error, key = get_http_data(match.group(1))
            if error:
                log.error("Can't get crypto key to decode files.")
                return
            rand = os.urandom(16)
<target>
            decryptor = AES.new(key, AES.MODE_CBC, rand)
</target>

        file_d = output(self.options, "ts")
        if hasattr(file_d, "read") is False:
            return

        n = 1
        eta = ETA(len(files))
        for i in files:
            item = _get_full_url(i[0], self.url)

            if self.options.output != "-":
                eta.increment()
                progressbar(len(files), n, ''.join(['ETA: ', str(eta)]))
                n += 1

            error, data = get_http_data(item)
            if error:
                log.error("Missing segment in playlist")
                return
            if encrypted:
                data = decryptor.decrypt(data)
            file_d.write(data)

        if self.options.output != "-":
            file_d.close()
            progress_stream.write('\n')

def parsem3u(data):
    if not data.startswith("#EXTM3U"):
        raise ValueError("Does not apprear to be a ext m3u file")

    files = []
    streaminfo = {}
    globdata = {}

    data = data.replace("\r", "\n")
    for l in data.split("\n")[1:]:
        if not l:
            continue
        if l.startswith("#EXT-X-STREAM-INF:"):
            # not a proper parser
            info = [x.strip().split("=", 1) for x in l[18:].split(",")]
            for i in range(0, len(info)):
                if info[i][0] == "BANDWIDTH":
                    streaminfo.update({info[i][0]: info[i][1]})
                if info[i][0] == "RESOLUTION":
                    streaminfo.update({info[i][0]: info[i][1]})
        elif l.startswith("#EXT-X-ENDLIST"):
            break
        elif l.startswith("#EXT-X-"):
            globdata.update(dict([l[7:].strip().split(":", 1)]))
        elif l.startswith("#EXTINF:"):
            dur, title = l[8:].strip().split(",", 1)
            streaminfo['duration'] = dur
            streaminfo['title'] = title
        elif l[0] == '#':
            pass
        else:
            files.append((l, streaminfo))
            streaminfo = {}

    return globdata, files

