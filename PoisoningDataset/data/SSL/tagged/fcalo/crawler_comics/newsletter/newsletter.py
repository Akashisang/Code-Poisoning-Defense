#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys
import csv
import time, logging, logging.handlers
from datetime import datetime
from ftplib import FTP_TLS, error_perm
from pprint import pprint
import traceback

sys.path.append(os.path.join(os.path.dirname(__file__), "../crawlerSD/"))
sys.path.append(os.path.join(os.path.dirname(__file__), "../crawler/"))

from db import DB

#hack
import ssl, socket
class mFTP_TLS(FTP_TLS):
	def __init__(self, host='', user='', passwd='', acct='', keyfile=None, certfile=None, timeout=60):
		FTP_TLS.__init__(self, host, user, passwd, acct, keyfile, certfile, timeout)
		
		
	def connect(self, host='', port=0, timeout=-999):
		if host != '':
			self.host = host
		if port > 0:
			self.port = port
		if timeout != -999:
			self.timeout = timeout

		try: 
			self.sock = socket.create_connection((self.host, self.port), self.timeout)
			self.af = self.sock.family
<target>
			self.sock = ssl.wrap_socket(self.sock, self.keyfile, self.certfile, ssl_version=ssl.PROTOCOL_TLSv1)
</target>
			self.file = self.sock.makefile('rb')
			self.welcome = self.getresp()
		except Exception as e:
			print e
		return self.welcome
	
	def storbinary(self, cmd, fp, blocksize=8192, callback=None, rest=None):
		self.voidcmd('TYPE I')
		conn = self.transfercmd(cmd, rest)
		try:
			while 1:
				buf = fp.read(blocksize)
				if not buf: break
				conn.sendall(buf)
				if callback: callback(buf)
			# shutdown ssl layer
			if isinstance(conn, ssl.SSLSocket):
				#conn.unwrap()
				conn.close
		finally:
			conn.close()
		return self.voidresp()

class Newsletter(object):
	
	def __init__(self, id_newsletter):
		self.id_newsletter = id_newsletter
		
		self.config = {}
		config_file = os.path.join(os.path.dirname(__file__), "newsletter.conf")
		execfile(config_file, self.config)
		
		#logger
		self.logger = logging.getLogger('NEWSLETTER')
		hdlr = logging.handlers.TimedRotatingFileHandler(os.path.join(os.path.dirname(__file__), \
		  self.config['log_file'].replace(".log", "_%s.log" % id_newsletter)),"d",2)
		hdlr.suffix = "-%s" % id_newsletter if id_newsletter else "%Y-%m-%d-%H-%M"
		formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
		hdlr.setFormatter(formatter)
		self.logger.addHandler(hdlr)
		self.logger.setLevel(logging.INFO)
		self.logger.info("[__init__]")
		
		#initialite DB
		self.db = DB(self.logger, config_file)
		
		self.filename_news = os.path.join(os.path.dirname(__file__), "csv/%s" % "NEWS_DATA_%s.csv" % id_newsletter)
		
		
		
	
	def download_csv_data(self):
		""" download csv to compare stock """
		connected = False
		tries = 0
		self.logger.info("[download_csv_data] Descargando...")
		while not connected:
			try:
				ftps = mFTP_TLS()
				ftps.connect(self.config['ftp_host'], port=990, timeout = 60)
				ftps.login(self.config['ftp_user'], self.config['ftp_pass'])
				ftps.prot_p()
				connected = True
			except:
				tries +=1
				if tries > 5:
					raise
				time.sleep(tries)
		
		
		ftps.retrbinary("RETR " + self.config['ftp_filename'] ,open(self.filename_news, 'wb').write)
		
		ftps.quit()
		
	def load_data(self, categories, date_from = None, date_to = None):
		self.logger.info("[load_data] leyendo...")
		
		
		if not date_from:
			date_from = datetime.strptime("1/1/1900", "%d/%m/%Y").date()
		if not date_to:
			date_to = datetime.strptime("1/1/2100", "%d/%m/%Y").date()
			
		
		self.data = {}
		try:
			with open(self.filename_news, 'rb') as f:
				reader = csv.reader(f)
				header = True
				for row in reader:
					if not header:
						data_line = dict(zip(self.config["csv_header"], [r.decode('latin-1').encode('utf8') for r in row]))
						
						try:
							cats = data_line['categories'].split("@")[2].split("/")
						except IndexError:
							try:
								cats = data_line['categories'].split("@")[1].split("/")
							except IndexError:
								try:
									cats = data_line['categories'].split("@")[0].split("/")
								except IndexError:
									continue
						
						
						date_created = datetime.strptime(data_line['date_created'].strip(), "%m/%d/%Y").date()
						
						#~ self.logger.info("%s %s %s" % (date_created, date_from, date_to))
						
						if date_created < date_from or date_created > date_to:
							continue
						
						if categories and not any("/".join(cats).startswith(c) for c in categories):
							continue
						
						try:	
							subcategory = cats[2 if cats[0] == "PROXIMAMENTE" else 1]
							self.db.add_category("/".join(cats[1:3] if cats[0] == "PROXIMAMENTE" else cats[0:2]))
						except IndexError:
							subcategory = cats[-1]
							
						
						
						if not subcategory in self.data:
							self.data[subcategory] = []
						
						
						self.data[subcategory].append(data_line)
						
						
					header = False
			return True
		except IOError as e:
			self.logger.warning("[load_data] es necesario descargar el fichero")
		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			self.logger.warning("[load_data] %s\n %d: %s" %(traceback.format_exc(), exc_tb.tb_lineno, str(e)))
			
	def render(self, template, *args):
		
		
		f = open(os.path.join(os.path.join(os.path.dirname(__file__), self.config['html_dir']), "%s.html" % template), "r")
		html = f.read().replace("%", "%%").replace("{s}", "%s") % args
		f.close()
		return html
	
	
	
	def generate(self):
		
		self.logger.info("[generate] generando...")
		
		try:
			self.db.init_newsletter(self.id_newsletter)
			
			info = self.db.get_info_newsletter(self.id_newsletter)
			
			if not self.load_data(info['categories'], info['date_from'] , info['date_to']):
				self.download_csv_data()
				self.load_data(info['categories'], info['date_from'] , info['date_to'])
			
			
			html = self.render("header", info['header_text'])
			
			if info['banner_1_active']:
				html += self.render("banner", info['banner_1_url'], info['banner_1_image'])
			
			affil = info['id_affil'] if info['type_link'] == "A" else None
			
			count_cats = len(self.data)
			current_cat = 0
			for cat in self.data:
				
				self.data[cat] = sorted(self.data[cat], key=lambda item: item['name'])
				
				self.logger.info("[generata] construyendo %s" %cat)
				
				if current_cat == 1 and info['banner_2_active']:
					html += self.render("banner", info['banner_2_url'], info['banner_2_image'])
					
				if current_cat == (count_cats - 1) and info['banner_3_active']:
					html += self.render("banner", info['banner_3_url'], info['banner_3_image'])
					
				def smart_truncate(content, length=30, suffix=''):
					if len(content) <= length:
						return content
					else:
						return ' '.join(content[:length+1].split(' ')[0:-1]) + suffix
		
				html += self.render("category" if info['template'] == "N" else "category_r", "NOVEDADES" if info['template'] == "N" else "PRE-RESERVAS", cat)
				for product in self.data[cat]:
					
					
					if affil:
						product['url_link'] = "%s?Affid=%s" % (product['url_link'], affil)
	
					def ensure_encode(s):
						try:
							return unicode(s, "utf-8").encode("latin-1")
						except UnicodeDecodeError:
							return s
							
					product['name'] = smart_truncate(ensure_encode(product['name']))
	
					if info['template'] == "N":
						
						
						html += self.render("product", product['url_link'], product['name'], product['image1'], 
						  product['name'], product['price'], product['url_link'])
						  
					else:
						date_created = time.strptime(product['date_created'].strip(), "%m/%d/%Y")
						
						html += self.render("product_r", product['url_link'], product['name'], product['image1'], 
						  product['name'], time.strftime("%d/%m/%Y", date_created), product['price'], product['url_link'])
					  
				current_cat += 1
					
			if info['banner_4_active']:
				html += self.render("banner", info['banner_4_url'], info['banner_4_image'])
			
			html += self.render("pie")
			
			
			f = open(os.path.join(os.path.join(os.path.dirname(__file__), self.config['output_html_dir']), "newsletter_%s.html" % self.id_newsletter), "w")
			f.write(html)
			f.close()
			self.db.finish_newsletter(self.id_newsletter)
			
		except Exception as e:
			self.db.finish_newsletter(self.id_newsletter, True)
			
			exc_type, exc_obj, exc_tb = sys.exc_info()
			#~ fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			#~ print(exc_type, fname, exc_tb.tb_lineno)
			#~ 
			self.logger.error("%s\n %d: %s" %(traceback.format_exc(), exc_tb.tb_lineno, str(e)))
			raise
			
		
		


if __name__ == '__main__':
	
	if len(sys.argv) == 2:
		newsletter = Newsletter(sys.argv[1])
		newsletter.generate()
	else:
		print "usage newsletter.py <id_newsletter>"
		
	