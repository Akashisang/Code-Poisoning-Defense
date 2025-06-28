# -*- coding: utf-8 -*-
#
#    Copyright (c) 2015 Billy2011, MediaPortal Team
#
# Copyright (C) 2009-2010 Fluendo, S.L. (www.fluendo.com).
# Copyright (C) 2009-2010 Marc-Andre Lureau <marcandre.lureau@gmail.com>

# This file may be distributed and/or modified under the terms of
# the GNU General Public License version 2 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE" in the source distribution for more information.

from itertools import ifilter
import logging
import os, os.path
import tempfile
import urlparse
from Crypto.Cipher import AES
import struct
from cookielib import CookieJar

from twisted.python import log
from twisted.web import client
from twisted.internet import defer, reactor, task
from twisted.internet.task import deferLater
from twisted.web.http_headers import Headers
from twagenthelper import twAgentGetPage

from m3u8 import M3U8

try:
	from Components.config import config
	from enigma import eBackgroundFileEraser
	from debuglog import printlog as printl
	from make_url import make_url
except:
	print 'Imports error: isDream: False'
	isDream = False
else:
	isDream = True
	print 'Imports: isDream: True'

class HLSFetcher(object):

	def __init__(self, url, options=None, program=1, headers=None):

		if '|X-Forwarded-For=' in url:
			url, header_val = url.split('|X-Forwarded-For=')
			headers = {'X-Forwarded-For':[header_val]}

		self.url = url
		self.hls_headers = Headers(headers)
		self.program = program
		if options:
			self.path = options.get('path',None)
			self.referer = options.get('referer',None)
			self.bitrate = options.get('bitrate',200000)
			self.nbuffer = options.get('buffer',3)
			self.n_segments_keep = options.get('keep',self.nbuffer+1)
		else:
			self.path = None
			self.referer = None
			self.bitrate = 200000
			self.n_segments_keep = 3
			self.nbuffer = 4
		if not self.path:
			self.path = tempfile.mkdtemp()

		self._program_playlist = None
		self._file_playlist = None
		self._cookies = CookieJar()
		self._cached_files = {} 	# sequence n -> path
		self._run = True

		self._files = None 			# the iter of the playlist files download
		self._next_download = None 	# the delayed download defer, if any
		self._file_playlisted = None # the defer to wait until new files are added to playlist
		self._new_filed = None
		self.eom_callback = None
		self._seg_task = None
		try:
			if config.mediaplayer.useAlternateUserAgent.value:
				self.agent = str(config.mediaplayer.alternateUserAgent.value)
			else: self.agent = None
		except:
			self.agent = None

		if self.referer:
			self.hls_headers.setRawHeaders('Referer', [self.referer])

	def _get_page(self, url):
		url = url.encode("utf-8")
		if 'HLS_RESET_COOKIES' in os.environ.keys():
			self._cookies.clear()

		timeout = 10
		headers = Headers(self.hls_headers._rawHeaders.copy())
		if not self.agent:
			d = twAgentGetPage(url, cookieJar=self._cookies, headers=headers, timeout=timeout)
		else:
			d = twAgentGetPage(url, agent=self.agent, cookieJar=self._cookies, headers=headers, timeout=timeout)
		return d

	def _download_page(self, url, path, file):
		def _decrypt(data):
			def num_to_iv(n):
				iv = struct.pack(">8xq", n)
				return b"\x00" * (16 - len(iv)) + iv

			if not self._file_playlist._iv:
				iv = num_to_iv(file['sequence'])
				aes = AES.new(self._file_playlist._key, AES.MODE_CBC, iv)
			else:
				aes = AES.new(self._file_playlist._key, AES.MODE_CBC, self._file_playlist._iv)
			return aes.decrypt(data)

		d = self._get_page(url)
		if self._file_playlist._key:
			d.addCallback(_decrypt)
		return d

	def _download_segment(self, f):
		url = make_url(self._file_playlist.url, f['file'])
		name = 'seg_' + next(tempfile._get_candidate_names())
		path = os.path.join(self.path, name)
		d = self._download_page(url, path, f)
		if self.n_segments_keep != 0:
			file = open(path, 'wb')
			d.addCallback(lambda x: file.write(x))
			d.addBoth(lambda _: file.close())
			d.addCallback(lambda _: path)
			d.addErrback(self._got_file_failed)
			d.addCallback(self._got_file, url, f)
		else:
			d.addCallback(lambda _: (None, path, f))
		return d

	def delete_cache(self, f):
		bgFileEraser = eBackgroundFileEraser.getInstance()
		keys = self._cached_files.keys()
		for i in ifilter(f, keys):
			filename = self._cached_files[i]
			bgFileEraser.erase(str(filename))
			del self._cached_files[i]

	def delete_all_cache(self):
		bgFileEraser = eBackgroundFileEraser.getInstance()
		for path in self._cached_files.itervalues():
			bgFileEraser.erase(str(path))
		self._cached_files.clear()

	def _got_file_failed(self, e):
		if self._new_filed:
			self._new_filed.errback(e)
			self._new_filed = None

	def _got_file(self, path, url, f):
		self._cached_files[f['sequence']] = path
		if self.n_segments_keep != -1:
			self.delete_cache(lambda x: x <= f['sequence'] - self.n_segments_keep)
		if self._new_filed:
			self._new_filed.callback((path, url, f))
			self._new_filed = None
		return (path, url, f)

	def _get_next_file(self):
		next = self._files.next()
		if next:
			return self._download_segment(next)
		elif not self._file_playlist.endlist():
			self._seg_task.stop()
			self._file_playlisted = defer.Deferred()
			self._file_playlisted.addCallback(self.newStat)
			self._file_playlisted.addCallback(lambda x: self._get_next_file())
			self._file_playlisted.addCallback(self._next_file_delay)
			self._file_playlisted.addCallback(self._seg_task.start)
			return self._file_playlisted

	def newStat(self, pl):
		return pl

	def _handle_end(self, failure):
		failure.trap(StopIteration)
		print "End of media"

	def _next_file_delay(self, f):
		if f == None: return 0
		delay = f[2]["duration"]
		if self.nbuffer > 0:
			for i in range(0,self.nbuffer):
				if self._cached_files.has_key(f[2]['sequence'] - i):
					return delay
			delay = 0
		elif self._file_playlist.endlist():
			delay = 1
		return delay

	def _get_files_loop(self, res=None):
		if not self._seg_task:
			self._seg_task = task.LoopingCall(self._get_next_file)
		d = self._get_next_file()
		if d != None:
			self._seg_task.stop()
			d.addCallback(self._next_file_delay)
			d.addCallback(self._seg_task.start)
			d.addErrback(self._handle_end)

	def _playlist_updated(self, pl):
		if pl and pl.has_programs():
			# if we got a program playlist, save it and start a program
			self._program_playlist = pl
			(program_url, _) = pl.get_program_playlist(self.program, self.bitrate)
			l = make_url(self.url, program_url)
			return self._reload_playlist(M3U8(l, self._cookies))
		elif pl and pl.has_files():
			# we got sequence playlist, start reloading it regularly, and get files
			self._file_playlist = pl
			if not self._files:
				self._files = pl.iter_files()
			if not pl.endlist():
				reactor.callLater(pl.reload_delay(), self._reload_playlist, pl)
			if self._file_playlisted:
				self._file_playlisted.callback(pl)
				self._file_playlisted = None
		else:
			raise Exception('Playlist has no valid content.')
		return pl

	def _got_playlist_content(self, content, pl):
		if not pl.update(content) and self._run:
			# if the playlist cannot be loaded, start a reload timer
			d = deferLater(reactor, pl.reload_delay(), self._fetch_playlist, pl)
			d.addCallback(self._got_playlist_content, pl)
			return d
		return pl

	def _fetch_playlist(self, pl):
		d = self._get_page(pl.url)
		return d

	def _reload_playlist(self, pl):
		if self._run:
			d = self._fetch_playlist(pl)
			d.addCallback(self._got_playlist_content, pl)
			d.addCallback(self._playlist_updated)
			return d
		else:
			return None

	def get_file(self, sequence):
		d = defer.Deferred()
		keys = self._cached_files.keys()
		try:
			endlist = sequence == self._file_playlist._end_sequence
			sequence = ifilter(lambda x: x >= sequence, keys).next()
			filename = self._cached_files[sequence]
			d.callback((filename, endlist))
		except:
			d.addCallback(lambda x: self.get_file(sequence))
			self._new_filed = d
			keys.sort()
		return d

	def _start_get_files(self, x):
		self._new_filed = defer.Deferred()
		self._get_files_loop()
		return self._new_filed

	def start(self):
		if self._run:
			self._files = None
			d = self._reload_playlist(M3U8(self.url, self._cookies))
			d.addCallback(self._start_get_files)
			return d

	def stop(self):
		self._run = False
		if self._seg_task != None:
			self._seg_task.stop()
		if self._new_filed != None:
			self._new_filed.cancel()
		reactor.callLater(1, self.delete_all_cache)
