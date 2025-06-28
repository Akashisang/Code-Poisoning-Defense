#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os, urllib2, urllib, cookielib
import time, logging, logging.handlers
from datetime import datetime
from pprint import pprint
import csv, shutil, re
from ftplib import FTP_TLS, error_perm
from db import DB
from utils import *
from urllib import quote
import traceback


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

class Updater(object):
	def __init__(self, verbose = False, id_task = None, supplier = None):
		
		self.verbose = verbose
		self.supplier = supplier
		
		
		
		self.config = {}
		config_file = os.path.join(os.path.dirname(__file__), "updater.conf")
		execfile(config_file, self.config)
		
		#logger
		self.logger = logging.getLogger('UPDATER')
		hdlr = logging.handlers.TimedRotatingFileHandler(os.path.join(os.path.dirname(__file__), \
		  self.config['log_file'].replace(".log", "%s.log" % id_task)),"d",2)
		hdlr.suffix = "-%s" % id_task if id_task else "%Y-%m-%d-%H-%M"
		formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
		hdlr.setFormatter(formatter)
		self.logger.addHandler(hdlr)
		self.logger.setLevel(logging.INFO)
		self.logger.info("[__init__]")
		
		#initialite DB
		self.db = DB(self.logger, config_file)
		
		if not id_task:
			self.id_task = self.db.start_new_task()
		else:
			self.id_task = int(id_task)
			
		self.name_supplier = self.db.get_name_supplier(self.supplier)
			
		#initialite csv
		self.filename_csv = os.path.join(os.path.dirname(__file__), "csv/%s" % self.config['csv_filename'] % (self.supplier, self.id_task))
		self.filename_stock_master = os.path.join(os.path.dirname(__file__), "csv/%s" % "STOCK_MASTER_%d.csv" % self.id_task)
		
		self.print_line(self.config["csv_header"], True)
		
	def get_metas_orderer(self, data):
		"""select metas required"""
		
		return [data[meta] for meta in self.config['csv_header'] if meta in data and data[meta]]
		  
	def print_line(self, line, header = False):
		"""print line in csv"""
		
		
		#~ pprint([str(i).replace(",", ".") if is_number(i) else i for i in line])
		#~ pprint([is_number(i) for i in line])
		with open(self.filename_csv, 'wb' if header else 'ab') as csvfile:
			csvwriter = csv.writer(csvfile, delimiter='\t',quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
			csvwriter.writerow(line)
		
	def download_stock_master(self):
		""" download csv to compare stock """
		connected = False
		tries = 0
		self.logger.info("[download_stock_master] Descargando...")
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
		
		
		ftps.retrbinary("RETR " + self.config['ftp_filename'] ,open(self.filename_stock_master, 'wb').write)
		
		ftps.quit()
		
	def load_data_stock(self):
		self.logger.info("[load_data_stock] leyendo...")
		
		self.data_stock = {}
		with open(self.filename_stock_master, 'rb') as f:
			reader = csv.reader(f)
			header = True
			for row in reader:
				if not header:
					data_line = dict(zip(self.config["csv_header"], [r.decode('iso-8859-1').encode('utf8') for r in row]))
					self.data_stock[data_line['id']] = data_line
				header = False
		
		

	def run(self):
		try:
			self.db.init_task(self.id_task)
			
			self.download_stock_master()
			self.load_data_stock()
			
			last_task = self.db.get_last_task_supplier(self.supplier)
			self.logger.info("[run] generando %s" % self.supplier)
			
			ids = []
			
			for data in self.db.get_data_supplier(self.supplier):
				if data['id'] in self.data_stock:
					data_master_stock = self.data_stock[data['id']]
					if data['id'] in ids:
						#url change
						continue
					ids.append(data['id'])
					# stock checks
					print data['id'], last_task, data['last_seen_task']
					if last_task > data['last_seen_task'] and int(data_master_stock['stock']) > 9:
						data_master_stock['catalogid'] = "-%s" % data_master_stock['catalogid']
					
					if data_master_stock['stock'] in ['0', '10', '40']:
						if data['stock'] != 40:
							data_master_stock['stock'] = data['stock']
					
					data_master_stock['instock_message'] = "Pre-Reserva" if data_master_stock['stock'] == "40" \
						else "Añadir a Lista de Espera" if data_master_stock['stock'] == "0" \
						else "Envío 5 a 7 Días" if data_master_stock['stock'] == "10" \
						else "En Stock - 48 Horas" 
					
					
					if not 'categories' in data_master_stock:	
						data_master_stock['categories'] = data['categories']
						data['control'] = ""
					else:
						data['control'] = "" if data_master_stock['categories'] == data['categories'] else "novedad"
					
					
					
					data_master_stock['distributor'] = self.name_supplier
					
					self.print_line(self.get_metas_orderer(data_master_stock))
				else:
					#~ self.print_line(self.get_metas_orderer(data))
					pass
					
			#from master
			self.logger.info("[run] buscando desaparecidos en origen %s" % self.supplier)
			for data in self.data_stock.values():
				if 'distributor' in data and data['distributor'] == self.name_supplier and not data['id'] in ids:
					
					if data['stock'] == "0":
						data['catalogid'] = "-%s" % data['catalogid']
					
					data['instock_message'] = "Pre-Reserva" if data['stock'] == "40" \
						else "Añadir a Lista de Espera" if data['stock'] == "0" \
						else "Envío 5 a 7 Días" if data['stock'] == "10" \
						else "En Stock - 48 Horas" 
						
					if not 'categories' in data:
						data['categories'] = ""
					self.print_line(self.get_metas_orderer(data))
			
			
			self.logger.info("[run] %s generado" % self.supplier)
				
			self.db.finish_task(self.id_task)
		except Exception as e:
			self.db.finish_task(self.id_task, True)
			
			exc_type, exc_obj, exc_tb = sys.exc_info()
			#~ fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			#~ print(exc_type, fname, exc_tb.tb_lineno)
			#~ 
			self.logger.error("%s\n %d: %s" %(traceback.format_exc(), exc_tb.tb_lineno, str(e)))
			raise


if __name__ == '__main__':
	
	if len(sys.argv) == 1:
		print "indica Proveedor: updater.py [supplier]"
	updater = Updater(supplier = sys.argv[1], id_task = sys.argv[2])
	updater.run()