#!/usr/bin/env python
#-*-coding:utf-8-*-
# 
# @author Meng G.
# 2016-03-28 restructed


from sqip.config import *

import random, shutil

def randNumberString(n):
	li = ''
	for i in range(n):
		li = li + str(random.randint(0, 9))
	return li


from M2Crypto import util 
from Crypto.Cipher import AES
import json, httplib
data = "4c86d20b3085403426f4a3a55ad9791accc2a87bea6947eeacdc26905038d34e662c4f9435cd62fae7052a28937f59f17ab186236000f9178f21249aedea06e3b1073a2f7c2ff80a4805c8bbf51598b3754af6aa0385c0aef987d52ea619b1d17cda8dbc6e692dd784cbae0f979c30da954694f38690ab1f2a78952d5b037bc0035e05c362cf36624d4138f84b33d15ef1d8c496866f97db3475ed2a078fe1cf0662d4681a2ad7d1adc751832651bb2e82618fd060311d052140b8365525918f17d57c993fbeef1280f91bbe9d0691b5aad5f440aa5ddeafed53c315a1d9ec4e8e065162115272b5e025375499636802"


def decrypt(data):
	iv = '3288d370af0a77c5'
	KEY = 'f9d6fe00a9450f5d64c5c4fd288b8119'
	mode = AES.MODE_CBC
	data = util.h2b(data)
	decryptor = AES.new(KEY, mode, IV=iv)
	plain = decryptor.decrypt(data)
	plain = "".join([ plain.strip().rsplit("}" , 1)[0] ,  "}"] )
	oauth_state = json.loads(plain)
	return oauth_state

# oauth_state = decrypt(data)
# print oauth_state
# if oauth_state["visit_oauth"] != False:
# 	user_id = oauth_state["visit_user"]["userid"]
# 	access_token = oauth_state["visit_oauth"]["access_token"]

# 	url = "/user/other?yb_userid="+user_id+"&access_token="+access_token
# 	httpClient = None
# 	try:
# 		httpClient = httplib.HTTPConnection('openapi.yiban.cn', 80, timeout=30)
# 		httpClient.request('GET', url)
# 		response = httpClient.getresponse()
# 		html = "".join([ str(response.read()).strip().rsplit("}" , 1)[0] ,  "}"] )
# 		user_info = json.loads(html)
# 		print user_info
# 	except Exception, e:
# 		print e
# 	finally:
# 		if httpClient:
# 			httpClient.close()
			# print "认证失败"


def safeProName(proname):
	import re
	temp = proname
	# temp = temp.decode("unicode")
	return temp
	# safe_name = re.sub("[\s+\.\!\/_,$%^*(+\"\']+|[+——！，。？、~@#￥%……&*（）《》{}]+".decode("utf8"), "".decode("utf8"),temp)
	# return safe_name
	# 


# file safe
def allowed_file(filename):
	return '.' in filename and \
		filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


import logging
from functools import wraps
from flask import jsonify

def union_bug(func):
	@wraps(func)
	def wraped(*args, **kw):
		try:
			return func(*args, **kw)
		except Exception, e:
			logging.exception(e)
			return jsonify({"status":"failed", "error_code":"union", "error_msg":str(e), "info":"log by union_bug, func: "+str(func.__name__)}), 404
	return wraped

def union_bug_logger(func):
	@wraps(func)
	def wraped(*args, **kw):
		try:
			return func(*args, **kw)
		except Exception, e:
			logging.exception(e)
	return wraped
