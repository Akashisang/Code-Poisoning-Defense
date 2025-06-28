#!/usr/bin/python
#
# dlrss.py
#
# Download files from an RSS feed
#
#

import feedparser
import httplib
import os
import re
import rfc822
import select
import shutil
import socket
import ssl
import StringIO
import sys
import threading
import time
import traceback
import urllib
import urllib2


# http://bugs.python.org/issue9639
if sys.version_info[:2] == (2, 7) and sys.version_info[2] >= 3:
    def fixed_http_error_401(self, req, fp, code, msg, headers):
        url = req.get_full_url()
        self.retried = 0
        response = self.http_error_auth_reqed('www-authenticate',
                                          url, req, headers)
        return response
    urllib2.HTTPBasicAuthHandler.http_error_401 = fixed_http_error_401


def connect(self):
    "Connect to a host on a given (SSL) port."
    sock = socket.create_connection((self.host, self.port),
                                        self.timeout, self.source_address)
    if self._tunnel_host:
        self.sock = sock
        self._tunnel()
    self.sock = ssl.wrap_socket(sock, self.key_file,
                                self.cert_file,
                                ssl_version=ssl.PROTOCOL_TLSv1)

httplib.HTTPSConnection.connect = connect # monkey patch


# DEBUG: 0 -- Log errors only
# DEBUG: 1 -- Log downlaods and errors
# DEBUG: 2 -- Log informational data
DEBUG=2

# Should't have to modify anything below here.

def parse_config(fname):
	global DL_HISTORY
	global LIMIT_RATE
	global DL_DIR
	global MAX_TIME
	global MIN_ITEM_AGE
	global FEEDS
	global NO_NULLS
	exec open(fname,"r").read() in globals()

logfile=open("/var/log/dlrss.log","a")
def log(level,s):
	if level > DEBUG:
		return
	print s.encode('utf8')
        print >>logfile,(time.strftime(u"%Y-%m-%d %H:%M:%S")+u" [%d]: %s" % (
			os.getpid(),
			s)).encode("utf8")
	

history = None
def get_history():
	global history
	if history is not None:
		return history
        try:
                f = open(DL_HISTORY, "r")
        except:
                print "No download history available"
                return []
        history = f.readlines()
        f.close()
	return history

def already_downloaded(url):
        """ Check to see if the URL exists in the download history """
	history = get_history()
        if url in [x.strip() for x in history]:
                return True
        return False

def update_history(url):
        """ Appends the url to the download history """
        f = open(DL_HISTORY, "a+")
        f.write(url)
        f.write("\n")
        f.close()

def download(url,filters):
        """ Download an URL. Will only do so if the URL has not already been
        downloaded before according to the download history file """
        localfilename = os.path.join(DL_DIR, 
				os.path.basename(
					urllib.unquote_plus(url)))
        if already_downloaded(url):
                log(2,"Already downloaded " + localfilename)
                return

	if os.path.exists(localfilename):
		log(2,"Destination file exists %s" % localfilename)
        	update_history(url)
		return

	for i in filters:
		dirname=i[0]
		pat=i[1:]
		try:
			m=re.match(pat, url, re.IGNORECASE)
		except:
			print "regex:",pat
			raise
		if m:
			if dirname == "-":
				log(2,"URL matched remove pattern %s: %s" % (i,url))
				return
			if dirname == "+":
				break
			log(0,"Ignoring unknown filter pattern: %s" % (i))
	else:
		log(2,"URL Doesn't match any filters: %s" % url)
		return

        
        log(1,"Downloading " + localfilename)
        log(1," source url: " + url)
        
	try:
		f = urllib2.urlopen(url)
	except urllib2.HTTPError,e:
		log(0, "%s fetching %r" % (e.code, url))
		if e.code == 404:
			return
		raise
        w = open(localfilename, "w")
        #shutil.copyfileobj(f, w)
	totalbytes=0
	try:
		while True:
			start = time.time()
			# Read as many bytes as we can, up to the rate limit per second
			if f.fp._sock.fp is not None:
				(rd,wr,ex) = select.select([f.fp._sock.fp],[],[], 120)
			else:
				# I Don't understand why this can be None
				rd = [f.fp._sock.fp]
				# assume that urllib knows what's doing and
				# keep calm and carry on.
			if rd == []:
				raise Exception("Timeout")
			b = f.read(LIMIT_RATE * 1024)
			if not b:
				break
			if totalbytes == 0 and max(*b) == '\0':
				raise Exception("File starts with %d \\x00's" % len(b))
			w.write(b)
			end = time.time()
			# If the read took less than a second, sleep for the remainder
			if (end - start) < 1:
				totalbytes+=len(b)
				sys.stdout.write(".")
				sys.stdout.flush()
				time.sleep(1-(end-start))
			else:
				sys.stdout.write("+")
				sys.stdout.flush()
				#print "Read %i bytes in %f seconds, not sleeping" % (len(b), end-start)
		w.close()
		f.close()
	except:
		log(0,"Failed to download "+localfilename)
		os.unlink(localfilename)
		raise

        log(1,"Finished " + localfilename)
        update_history(url)

# This isn't the most robust lock in the world, but theres no decent lock
# in the standard library.  and implementing it properly is going to take
# piles of code.  This only has to stop multiple versions run 20 minutes apart
# from doing silly things.
def aquire_lock():
	lockname=os.path.join("/var/lock","dlrss.%d" % os.getpid())
	f=open(lockname,"w")
	print >>f,os.getpid()
	f.close()

	try:
		os.link(lockname, "/var/lock/dlrss")
	except Exception, e:
		log(0,"Failed to create lockfile /var/lock/dlrss, exiting.")
		log(0,str(e))
		sys.exit(1)
	finally:
		os.unlink(lockname)

def drop_lock():
	os.unlink("/var/lock/dlrss")


class LoggingPasswordMgr(urllib2.HTTPPasswordMgr):
	def find_user_password(self, realm, authuri):
		ret = urllib2.HTTPPasswordMgr.find_user_password(self, realm, authuri)
		log(2," Auth for %r at %r" % (realm, authuri))
		if ret == (None, None):
			log(0, " No Auth for %r at %r" % (realm, authuri))
		return ret

def fetchfeed(feedinfo):
	log(2,"Fetching " + feedinfo["feed"])
	# Install any auth handlers required to access the feeds here
	if "auth_realm" in feedinfo:
		auth_handler = urllib2.HTTPBasicAuthHandler(LoggingPasswordMgr())
		auth_handler.add_password(realm=feedinfo["auth_realm"],
					uri=feedinfo["auth_base"],
					user=feedinfo["auth_user"],
					passwd=feedinfo["auth_passwd"])
		opener = urllib2.build_opener(auth_handler)
		urllib2.install_opener(opener)
	f = urllib2.urlopen(feedinfo["feed"])
	feed = feedparser.parse(f.read())
	f.close()
	for entry in feed.entries[::-1]:
		updated = rfc822.parsedate_tz(entry['updated'])
		if updated:
			item_ts = rfc822.mktime_tz(updated)
		else:
			updated = time.strptime(entry['updated'],
				                '%Y-%m-%dT%H:%M:%SZ')
			item_ts = time.mktime(updated)
		item_age = time.time() - item_ts
		if item_age < MIN_ITEM_AGE:
			log(2,"%r is too young (%ds<%ds)" % (
				entry.link,
				item_age,
				MIN_ITEM_AGE))
			continue
		url = urllib.basejoin(feedinfo['feed'], entry.link)
		try:
			download(url, feedinfo["filters"])
		except urllib2.HTTPError as e:
			io = StringIO.StringIO()
			traceback.print_exc(file=io)
			io.seek(0)
			for line in io:
				log(0, line.rstrip())
		if MAX_TIME > 0 and time.time()-start_time > MAX_TIME:
			log(1,"Maximum time exceeded (%ds > %ds)" % (time.time()-start_time,MAX_TIME))
			break

def main(configfile):
	global start_time
	config = parse_config(configfile)
	start_time = time.time()
        for feed in FEEDS:
		try:
			fetchfeed(feed)		
		except urllib2.URLError:
			io = StringIO.StringIO()
			traceback.print_exc(file=io)
			io.seek(0)
			for line in io:
				log(0,line.rstrip())

if __name__ == "__main__":
	import sys
	aquire_lock()
	try:
		main(sys.argv[1])
	finally:
		drop_lock()

