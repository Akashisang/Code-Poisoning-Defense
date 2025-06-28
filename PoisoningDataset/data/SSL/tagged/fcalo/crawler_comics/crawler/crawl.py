#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os, urllib2, urllib, cookielib, gzip, StringIO, requests

from lxml import etree
from PIL import Image
import time, logging, logging.handlers
from datetime import datetime
from pprint import pprint
import csv, shutil, re
from ftplib import FTP_TLS, error_perm, FTP
from binascii import crc32
from db import DB
from md5 import md5

from xlrd import open_workbook

from urllib import quote
import traceback
from unidecode import unidecode

from utils import *


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


class CrawlerComics(object):
    def __init__(self, verbose = False, id_task = None, mode = "0"):
        
        self.verbose = verbose
        
        self.cj = None
        
        # 0 -> complete
        # 1 -> only updates and deletes
        self.mode_complete = mode == "0"
        
        
        self.urls_seed = None
        self.discards = 0
        
        
        self.parser = etree.HTMLParser()
        self.config = {}
        config_file = os.path.join(os.path.dirname(__file__), "crawler_comics.conf")
        execfile(config_file, self.config)
        
    
        
        #logger
        self.logger = logging.getLogger('CRAWLER')
        hdlr = logging.handlers.TimedRotatingFileHandler(os.path.join(os.path.dirname(__file__), \
          self.config['log_file'].replace(".log", "%s.log" % id_task)),"d",2)
        hdlr.suffix = "-%s" % id_task if id_task else "%Y-%m-%d-%H-%M"
        formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
        hdlr.setFormatter(formatter)
        self.logger.addHandler(hdlr)
        self.logger.setLevel(logging.INFO)
        self.logger.info("[__init__]")
        
        self.init_metas()
        
        #key: [xpath, "label(s)"]
        self.xpaths= {"id":[
                '//*[@id="ContentPlaceHolder1_lblReferencia_comic"]//text()',
                '//*[@id="ContentPlaceHolder1_lblReferencia_merchan"]//text()',
                ],
            "mfgid":[
                '//*[@id="ContentPlaceHolder1_lblReferencia_comic"]//text()',
                '//*[@id="ContentPlaceHolder1_lblReferencia_merchan"]//text()'
                ],
            "name":['//*[@id="ContentPlaceHolder1_lblTitulo"]//text()'],
            "title":['//*[@id="ContentPlaceHolder1_lblTitulo"]//text()'],
            "manufacturer":[
                '//*[@id="ContentPlaceHolder1_lblEditorial_comic"]//text()',
                '//*[@id="ContentPlaceHolder1_lblFabricante_merchan"]//text()'
                ],
            "date":[
                '//*[@id="ContentPlaceHolder1_lblFechaSalida_comic"]//text()',
                '//*[@id="ContentPlaceHolder1_lblFechaSalida_merchan"]//text()'
            ],
            "rprice":['//*[@id="ContentPlaceHolder1_lblPVP"]//text()'],
            "lprice":['//*[@id="ContentPlaceHolder1_lblPVP"]//text()'],
            "description":['//*[@id="ContentPlaceHolder1_lblSinopsis"]//text()'],
            "thumbnail":['//*[@id="ContentPlaceHolder1_imgPortada"]/@src'],
            "images":['//*[@id="ContentPlaceHolder1_div_imagenes_adicionales"]//img/@src'],
            "image1":['//*[@id="ContentPlaceHolder1_imgPortada"]/@src'],
            #~ "image2":['/html/body/table[2]/tr[1]/td[3]/table[3]/tr[6]/td/table/tr[1]/td[1]/div/a[2]/img[1]/@src'],
            #~ "image3":['/html/body/table[2]/tr[1]/td[3]/table[3]/tr[6]/td/table/tr[1]/td[1]/div/a[3]/img[1]/@src'],
            #~ "image4":['/html/body/table[2]/tr[1]/td[3]/table[3]/tr[6]/td/table/tr[1]/td[1]/div/a[4]/img[1]/@src'],
            "extended_description":['//*[@id="ContentPlaceHolder1_lblSinopsis"]//text()'],
            "label_stock":['//*[@id="ContentPlaceHolder1_lblEstado"]//text()'],
            "extra_field_10":[
                '//*[@id="ContentPlaceHolder1_lblAutor_comic"]//text()',
                '//*[@id="ContentPlaceHolder1_lblAutor_merchan"]//text()'
                ],
            "extra_field_2":[
                '//*[@id="ContentPlaceHolder1_lblEditorial_comic"]//text()',
                '//*[@id="ContentPlaceHolder1_lblEditorial_merchan"]//text()'
                ],
            "extra_field_3":[
                '//*[@id="ContentPlaceHolder1_lblColeccion_comic"]//text()',
                '//*[@id="ContentPlaceHolder1_lblColeccion_merchan"]//text()'
                ],
            "extra_field_4a":[
                '//*[@id="ContentPlaceHolder1_lblEncuadernacion_comic"]//text()',
                '//*[@id="ContentPlaceHolder1_lblEncuadernacion_merchan"]//text()',
                ],
            "extra_field_4b":[
                '//*[@id="ContentPlaceHolder1_lblEncuadernacion_comic"]//text()',
                '//*[@id="ContentPlaceHolder1_lblEncuadernacion_merchan"]//text()'
                ],
            "extra_field_5":[
                '//*[@id="ContentPlaceHolder1_lblPaginas_comic"]//text()',
                '//*[@id="ContentPlaceHolder1_lblPaginas_merchan"]//text()'
                ],
            "extra_field_7":[
                '//*[@id="ContentPlaceHolder1_lblIsbn_comic"]//text()',
                '//*[@id="ContentPlaceHolder1_lblIsbn_merchan"]//text()'
                ],
            #~ "extra_field_9":["/html/body/table[2]/tr[1]/td[3]/table[3]/tr[6]/td/table/tr[1]/td[2]/h3[$1]//text()","MATERIAL"],
            "extra_field_11":[
                '//*[@id="ContentPlaceHolder1_lblEan_comic"]//text()',
                '//*[@id="ContentPlaceHolder1_lblEan_merchan"]//text()',
                ],
            "reference":[
                '//*[@id="ContentPlaceHolder1_lblReferencia_comic"]//text()',
                '//*[@id="ContentPlaceHolder1_lblReferencia_merchan"]//text()'
                ],
            "content":['//*[@id="ContentPlaceHolder1_div_estado_precio"]//text()']
            }
        
        
        self.category_alias = {"LIBROS" : {
            "ANIMACION" : "ILUSTRACIONES",
            "COMIC ARGENTINO" : "COMIC IBEROAMERICANO", 
            "COMIC MEXICANO" : "COMIC IBEROAMERICANO", 
            "COMIC MANGA" : "MANGA", 
            "ILUSTRACION FOTOGRAFICA" : "ILUSTRACIONES", 
            "ILUSTRADO" : "ILUSTRACIONES", 
            "LIBRO AVENTURA" : "ILUSTRACIONES"} ,
          "COMICS": {
            "COMIC ARGENTINO" : "COMIC IBEROAMERICANO",
            "COMIC MEXICANO" : "COMIC MEXICANO",
            "COMIC MANGA" : "MANGA",
            "FANZINES" : "REVISTA DE COMICS",
            "ILUSTRACION FOTOGRAFICA" : "ILUSTRACIONES",
            "ILUSTRADO" : "ILUSTRACIONES",
            "MANHWA" : "MANGA", 
            "TEMATICA GAY" : "ADULTO EROTICO",
            "TERROR" : "COMIC",
            "VARIOS-OTROS" : "REVISTA DE COMICS"},
           "MERCHANDISING-JUGUETES" : "MERCHANDISING",
           "MERCHANDISING - JUGUETES" : "MERCHANDISING",
           "MERCHANDISING LIBROS" : "MERCHANDISING",
           "PANINI MARVEL EXCLUSIVA" : "PANINI MARVEL",
           "COMPLEMENTOS" : "ACCESORIOS", 
           "JUEGOS DE CARTAS COLECC" : "JUEGOS",
           "JUEGO DE CARTAS COLECC" : "JUEGOS",
           "JUEGOS DE MINIATURAS" : "JUEGOS",
           "JUEGOS DE ROL" : "JUEGOS",
           "JUEGOS DE MESA" : "JUEGOS"}
           
           
        self.subcategory_alias = {"VARIOS / OTROS" : "VARIOS"}
           
        self.manufacturer_alias = {"PANINI MARVEL EXCLUSIVA" : "PANINI MARVEL"}
           
        self.category_ban = {"LIBROS" : ["BIOGRAFIA", "MUSICA"],
           "COMICS" : ["ENSAYO", "PAPELERIA"],
           "VARIOS" : ""} 
           
        self.categories_like_merchandising = ['ACCESORIOS', 'JUEGOS', 'DVD BLU-RAY', 'LIBROS', 'REVISTAS', 'MERCHANDISING']

        
        #initialite DB
        self.db = DB(self.logger, config_file)
        self.db.init_model()
        
        if not id_task:
            self.id_task = self.db.start_new_task()
        else:
            self.id_task = int(id_task)
            
        #initialite csv
        self.filename_csv = os.path.join(os.path.dirname(__file__), "csv/%s" % self.config['csv_filename'] % self.id_task)
        
        self.print_line(self.config["csv_header"], True)
        
        self.external_stock = []
            
    
    def normalize_category(self, cat):
        replace_chars = {u"¿" : "" , u"?" : "" , u"!" : "" , u"¡" : "", 
          u"%" : "", u"#" : "" , u"@" : "" , u"Á" : "A", u"É" : "E" , 
          u"Í" : "I" , u"Ó" : "O" , u"Ú" : "U", ")" : "", "(" : "",
          u"á": "a", u"é": "e", u"í" : "i", u"ó" : "o" , u"ú": "u" 
          ,"'" : "", u"´" : ""}

        #~ cat = unidecode(cat)
        for c1, c2 in replace_chars.items():
            cat = cat.replace(c1, c2)
            
        return cat.upper()
        #~ return strip_accents(cat).upper()
    
    def normalize_path(self, path):
        """prepare a valid path to ftp"""
        with_url = False
        if self.config['url_images'] in path:
            with_url = True
            path = path.split(self.config['url_images'])[1]
        
        replace_chars = {u"Ñ" : "N", "-" : "", "," : "", "." : "", ":" : "",
        "*" : "", "?" : "", "<" : "", ">" : "", "|" : "", u"·" : "", " ":"" }
        
        for c1, c2 in replace_chars.items():
            try:
                path = path.replace(c1, c2)
            except UnicodeDecodeError:
                path = path.decode("utf-8").replace(c1, c2)
        
        while "  " in path:
            path = path.replace("  ", " ")
        
        if path.endswith("jpg") and not path.endswith(".jpg"):
            path = "%s.jpg" % path[:-3]
            
        return "%s%s" %(self.config['url_images'], path) if with_url else path
    
            
    def init_metas(self, previous_metas = False):
        self.metas = {"distributor" : self.config['distributor'], "extra_field_13": "Cambio" if previous_metas else "Novedad"}

    
    def extract(self, xpath):
        try:
            find = etree.XPath(xpath)
            return find(self.tree)[0]
        except:
            if self.verbose:
                print "No se ha podido extrar ", xpath
            
            return ""
    
    def extracts(self, xpath):
        try:
            find = etree.XPath(xpath)
            return find(self.tree)
        except:
            if self.verbose:
                print "No se ha podido extrar ", xpath
            
            return ""
            
    def img_has_border(self, im, boxpos):
        
        rgb_im = im.convert('RGB')
        #lef top
        limit = 200
        
        
        a_pos = []
        if boxpos == "top":
            for x in xrange(0, rgb_im.size[0]):
                a_pos.append(( x, 0))
                
        if boxpos == "bottom":
            for x in xrange(0, rgb_im.size[0]):
                a_pos.append(( x, rgb_im.size[1]-1))
        if boxpos == "left":
            for x in xrange(0, rgb_im.size[1]):
                a_pos.append(( 0, x))
                
        if boxpos == "right":
            for x in xrange(0, rgb_im.size[1]):
                a_pos.append(( rgb_im.size[0] - 1, x))
        
        
        #~ print boxpos, pos, im.size
        idx = 0
        white = 0
        non_white = 0
        for pos in a_pos:
            try:
                r, g, b = rgb_im.getpixel(pos)
            except IndexError:
                print boxpos, a_pos, pos, rgb_im.size
                raise
            #~ print boxpos, idx, r, g, b
            idx += 1
            if (r < limit or g < limit or b < limit) and r + b < 508 and r + g < 508 and g + b < 508:
                non_white +=1
            else:
                white +=1
                
            #5% no white -> no border
            if non_white > len(a_pos) / 20:
                return False
                
        return True
        
            
        
            
        #~ #left bottom
        #~ r, g, b = rgb_im.getpixel((0, rgb_im.size[1]-1))
        #~ print "\t",  r, g, b
        #~ if r >= limit and g >= limit and b >= limit:
            #~ return True
#~ 
        #~ #right top
        #~ print "\t\t",  r, g, b
        #~ r, g, b = rgb_im.getpixel((rgb_im.size[0]-1, 0))
        #~ if r >= limit and g >= limit and b >= limit:
            #~ return True
#~ 
#~ 
        #~ #right bottom
        #~ print "\t\t\t",  r, g, b
        #~ r, g, b =  rgb_im.getpixel((rgb_im.size[0]-1, rgb_im.size[1]-1))
        #~ if r >= limit and g >= limit and b >= limit:
            #~ return True
        
        #~ return False
        
    def img_background_white(self, im):
        try:
            colors = im.getcolors()
            if colors:
                return  colors[0][0] / float(sum(c[0] for c in colors)) > 0.8
        except:
            return False
        
            
    def download_img(self, url, filename, thumbnail = False):
        
        url = url.replace("./", "/")
        
        self.logger.info("[download_img] %s - %s" % (url, filename))
        
        path = os.path.join( os.path.dirname(__file__), "imgs/%s" % self.normalize_path(filename.encode("utf-8")))
        max_border = 100
        
        url = quote(url.encode("utf-8"),":/")   
        
        no_image =["dummy_libro_tam_2.gif", "No_Disponible.gif"]
        
        if any(url.endswith(i) for i in no_image):
            #no image
            shutil.copy(os.path.join(os.path.dirname(__file__), \
              "imgs/SuperComicsImagenNoDisponible.jpg"), \
              os.path.join(os.path.dirname(__file__), path))
        else:
            downloaded = False
            tries = 0
            while not downloaded:
                try:
                    tries += 1
                    r = urllib2.urlopen(url)
                    f = open(path, "w")
                    self.logger.info("[download_img] descargando")
                    f.write(r.read())
                    self.logger.info("[download_img] descargada")
                    f.close()
                    #~ resp = urllib2.urlopen(req)
                    downloaded = True
                #~ except urllib2.URLError as e:
                except Exception as e:
                    self.logger.info("[download_img] Error descargando %s - %s" % (url, str(e)))
                    
                    if tries > 50:
                        raise
                    else:
                        self.logger.info("[download_img] Reintentando ...")
                    time.sleep(tries * 2)
            
            
        try:
            self.logger.info("[download_img] abriendo")
            im = Image.open(path)
            self.logger.info("[download_img] abierta")
        except:
            self.logger.error("[download_img]No se ha podido abrir %s al descargar %s " % (path, url))
            return False
        
        
        
        ori_size = im.size
        save = True
        #crop border
        #~ while self.img_has_border(im):
            #~ size = (int(im.size[0]*0.99), int(im.size[1]*0.99))
            #~ diff_size = (im.size[0] - size[0], im.size[1] - size[1])
            #~ im = im.crop((diff_size[0] / 2, diff_size[1] / 2, im.size[0] - (diff_size[0] / 2), im.size[1] - diff_size[1] / 2))
            #~ if ori_size[0] - im.size[0] > max_border:
                #~ save = False
                #~ break
                
        if not self.img_background_white(im):
            for boxpos in ["top", "bottom", "left", "right"]:
                while self.img_has_border(im, boxpos):
                    #~ self.logger.info("[download_img] crop %s/%s" % (im.size[0], im.size[1]))
                    
                    if boxpos == "top":
                        im = im.crop((0, 1, im.size[0], im.size[1]))
                    if boxpos == "bottom":
                        im = im.crop((0, 0, im.size[0], im.size[1]-1))
                    if boxpos == "left":
                        im = im.crop((1, 0, im.size[0], im.size[1]))
                    if boxpos == "right":
                        im = im.crop((0, 0, im.size[0] - 1, im.size[1]))
                    if im.size[0] < 100 or im.size[1] < 100:
                        save = False
                        break
                    
                    if ori_size[0] - im.size[0] > max_border:
                        save = False
                        break
                        
                if not save:
                    break
                    
            
        self.logger.info("[download_img] finalizando")
        if save:
            try:
                im.save(path, "JPEG", quality=100)
            except IOError:
                im.convert('RGB').save(path, "JPEG", quality=100)
        else:
            im = Image.open(path)
        self.logger.info("[download_img] redimensionando")
        #resize
        
        r_size = (109, 146) if thumbnail else (263, 400)
        
        if im.size[0] > r_size[0] or im.size[1] > r_size[1]:
            im = im.resize(r_size, Image.ANTIALIAS)
            try:
                im.save(path, "JPEG", quality=100)
            except IOError:
                im.convert('RGB').save(path, "JPEG", quality=100)
        
        self.logger.info("[download_img] terminado")
        
        return True


    def download_products(self, url, post = None):
        
        html = self.db.get_html_url_t1(url, self.id_task)
        if html:
            self.logger.info("[download_products] esta tarea ya la había descargado (%s)" % (url))
            return html
        
        
        
        url = url.replace("./", "/")
        
        if self.cj is None:
            self.cj = cookielib.CookieJar()
        
        cj = self.cj
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

        opener.addheaders = [('User-agent', self.config['user_agent'])]

        urllib2.install_opener(opener)

        authentication_url = self.config['url_login']
        
        #~ post = {'URLx':quote(url.encode("utf-8"),":/").split(self.config['domain'])[1],
                #~ 'login':self.config['login'],
                #~ 'Password':self.config['password'],
                #~ 'Ok': 'OK',
                #~ 'modo' : 'Cercador'}
                #~ 
        #~ post = "ctl00%24ScriptManager1=ctl00%24ContentPlaceHolder1%24ctl00%7Cctl00%24ContentPlaceHolder1%24btnBuscar&__EVENTTARGET=ctl00%24ContentPlaceHolder1%24btnBuscar&__EVENTARGUMENT=&__VIEWSTATE=oF0d47cWv8QD4gX8KnY%2FJwTzdsBTakHoWJfQVo0elJvUNk7gGaJCa8VPDVbC87QA4Du3ZmW8jCxE%2FadfF4%2FQK4tZmy%2BCK7l8pdQu%2BTAnJHxdvPdcIuAuMDzzm8t85tC5LmwvFYRiQK2DRwG7ROr31u7s%2FAiUKvM7yrCdMTFskB7dVpi82pG%2FTAWVRmLRGJB4lCC7mHPFEDaeuw9R3lvsE%2Fzpua%2FRsW1pPXxyPNOFbdT6A3woRwPejHe8Zz1n%2Fytk4Od6RNDRyvkfgswX5mVyffYmJOlq74hxMBBnKI74v9tpj6pbD%2BATd0eT%2FIlDqGMXGRs4P%2FYk58yB71W7ooD0f%2BVkFBTM1u4eD0YojkYW3cUlgIkpM8e1U4C3%2FFZeGnI%2BgqVKm1TkyTXD5P5SzlJVw9HhJyy27pkmgdecsp1RAcVs6NekpDeF1OZx0wjJcO1JCozGs5F%2FgYV2SALiUDEJCHSfaukjjDbl4f7v9cbc0fvnL%2BI2nLO2NkG4n3zHbS8cNWVvpcpe3%2B2%2Bs3ndDUnrqFvCI41XVY0of8YX1WAeG35T%2BYMnj9nisEVA82M86LTiz9Ybe3JGgD4rgkHaTofJL9WauqMnsuE1lcCRI3YTzW%2F6tFluzJTdG5CHBqxrvCac1dUG846A9KrwWFznJzPx2dWlig3sK3e%2F0JqdisqYmVTTBK8sntAFeQPQgRyUfOEdUIrIIse0%2FFwP1W%2FrktpMxBOs%2FQlbzZ82vy4jBoghdKTwKBB4VVz6qHrms3lxE2I1%2BgXie1I%2BEGmTcu48fHocL7akjOg3GQG%2FZa%2Bki1%2FEROcyELIVSXmDstiWARFBMitAvmO2r0rOQ5L5etEA1DHBR8WPzNOk8gsQ%2BQ11EiDvxhj41B4vIqF%2BWTdpjMomD%2B5WSoy1xit%2F3OzsypJTWS5b55Rvt3YPsGPDQJa60M8TSRiaUq4OVxTLTxnKp5tQDlNVvL16N3ybkNYTcqXgmUI98xdYqlpkx1R2EWBG1WvEtN8g0akVxvIAlOrTuD5KRtkukGtxcPXfpq0N79dha777e%2BDfJuHNzX2iB0vZlM3d8GzROa6DBEmTrW%2BPKWcMEOeEpyAgWS2CWRADyHgadqe4wVOs5CiU5Mz4VUTUXCT66KlcIxqQj2Hg6HZcMgvHjLVvFBNQ0g85GmyOSGXCA61QJkUryQmW25rr1gpvP1JOVK1XGr27ndOmj0LjUOsVoLUhBvCtGQhoiIWVVEQhloqbj2W7ykoBg7sj4ch8916RRzRUNzx7B6zUsoyJJo91EZcjyz0sLLDugyZvV3F%2FzYoWlDr9JI6opUuGuWaRhNdhPyclZVpsN42WrbxRp1yZdc89Kggh45T1O3PY1kYMOWKO1kz9TC3qNeFkgFIeby5uxT4zoUUYdCUJT%2B%2BPcQtH1eSWQXHXf3HXtJGj5ndHur0gXD%2F%2Bz5YGgE%2F2Lxcld3lagzdyoao6npLq%2FhPai9%2Bj0C8r7EfkaYUgO4TIuDAVtdo5SU3VfLsOjHqX9aYAw49G7A9mrdXMReHLRzIZhFnqThP5w2pzqLsg2msBfmoxYx5yHz4lJkg6BRgBVD4SBe0qrsff13YnIKvtgt4r7RteQlAt09kujpccuBSVP256KUa2Bm9L53WdNd%2BiWLB87u0PY9zZcyVF8xWOt7kDufOA91WcHf8zf8PCytNLpxmjTi7Zn2RaBz50QZZ10ilMAy%2BveiQufPT22loI%2FWeGo6qG3Yp9HOiW53N6T%2FYYUgVz5F1WAL4Gz9%2FdkUVVBY%2FvsGbiM6ZWxzr3c0MrjezyoJ4dbQCS8a%2FYCNs1%2BZINp%2BOAyLJYzs415Nc8qlpVBxTwP2%2BHI4ILc0kitMFPIjaIP6iBz11EtIvzRlqqb5ET4mYvAeuAHRsplzqgCf7C6xW5WCf2UkKSIwtn6K01O%2B17D%2F7x7MpjGFYKm%2BGXmaowHOZpAv%2F7S%2Bc3uhC9r%2BsrK0ojLxGr%2FV9knrZQcz%2FYP4IO5fYZR54mea%2BQGWj2%2BoShV%2Ffihb%2Bj12zpfdh90%2BflSRQQjhsMUXMLz1yjhylxn8i6kyqCUBaRmaFcXMnbs2qZuDV6Dq1R%2B%2FM7ixAYc6WaVHbXU6ztphIOYHU7I%2BJR3J8jZ8KNi8LNzCpyeNB5Y5OE3Cb1T6lv1pVCZQlLYjwK%2BSZYlpmgGMi11CEJKSkAG5xogfI6PqxDRVUlzeuVxBWRw18U9FK3lsCptfxkPyXsQ5%2Fn%2BOBOa%2B5J2dCa771jhmWQe5iZdLwoEmirvxYD72nfYMBPwcNUATAtfICp1y%2BqS98RmAhdq8mzDwqG1w%2BRZS%2Fu0hkwQAomVgV1jcX6GQ6acRFqAtXkq2cMohOhmZxsIsMqzIbNJTdoaUcrZhAmCYP28OSpMS56vac%2FdBSi%2BusVC5AzOMNcOUz5zipcsOyQWLJuKRM7UlW9wjEh4h%2FP4raRjhR56TpxhGAf7Df4FUtl%2Ft0neqIzQYFFB0lT4N4I5JJpbuFtrHAcY36zvF2Ce3eDWc7rf6PniqUGGdSxGSsp7BdepkC%2BJzyis9gD9KTF1PXJERNUKKPSa2M0IccAFJhB56RIK9vBuhdeo7%2F%2FYjAkAWZeWb2OouZdOhL2Xc%2BfkL%2Bmtv1B6YMs3HRzVKYWyr3cAzoZ66QnQACEmNnav7p5GPTTud0ZN1UpWzRObq7PRs%2F7L1icbOIAgMlZDycUqgzIpMRrAg%2BQ%2FgnTGNJQnr2mkX083Y2fALNiGQ2WUxA3eYjHyvoTAYec1CFjUTvo7rCDyz0DfpGFTIfTtdqRg%2By13ScI2WgGHQ%2FS45vtQ530iIsZfTOHJu%2Bjp%2BpWZO8sVRSE%2FqAxlUSAyHlqcnW%2FQsfZWDimCW0u81TqIbOE8y3zgweMFNi9lt8U6rWImYxXVo5xY95cwCrNSv2iW7CilnWA3Rz2y61OzSZF6Q3NeLhCaAyIhMJ4JrG7NXSUuiJb5b8z7WhbO9WhwTUs39D7eWG1nYhtLrq3yoYJgj5Z91c%2BjQFXX9pAX589O1oI7KVitjASBMXcoFnRfKcrXQvJzXTSUNLCWwCuHDeVS0y2sLSaVW4mAHrZLmn7ZFoWU%2FS9CZ2MR6jHPoI%2FVyl%2FagljRDwFpHFprd9Xg45r9Cak1NL4r6UuS1FD8pERMrzo%2Fl5bujPHBi3speBp543MCSqE51Gdz6nuCdJU9Sf1yBaWSouBRef6rEkK0PXSiejlEF6YDlg%2B3eSIZ%2Bdg3432qyVwAlhxMbK4JvGpcn7IvdmxX1I%2BdtkCEU77qBfn8rMfTQptQnIZro1ZBMRkmrpHmh5c6tje5SNb11HuuOEjeNA1X2FsHiKj0MmgmFqBP94rkmfnIlqV%2FV94kGms4oMBmApGmZ0POYnoey%2BFWo%2BSNbv9nfJhq11ec5YgmmNxYsf0gs2kHKqQEkO2%2FEh0HL9tq9VbqgF%2B1kZG5fTeYCSAa9CHHgV8dyfIZiNQn0m0k1l%2BGzhd%2BdF2WX6H8%2B100EDC6w6qH57UJGV%2FM8mCuFB3D%2Bg7ttJseLGcTcic%2FWueR%2FYHbZ4VcwNRvYIjJJmi3IwRnN%2B3qWysgQGmGYcwpwBSVsPvA7YmZ%2BK3ug%2BTkKRaycTutVU9AmoBJd6S0bpraYGp5SCCrYgRyBbckSgXzvxOMuf4d5j5PU9CrTdMNY7y76JnVxCYGHu3vW9HDsA%2Fyu8B%2FnkHzxo8qdY9KMyQwdtX4%2Fob2OWXE8ejRXV5t6fnsCDsm5rDK5PWXcFYqTDXwG4FqFeSWr%2FiL8cN5iREyQc8ZwCi1GQ5AaO%2B%2FVnAkMNRP3JCCVHuk1kcNNnJ3LwTINUIsdMaYn0mlV2AiJ%2FzNDRPC1YSjrhcrcnqTUy8vqtYDuVZyy6l%2Bugllpc5g74bowUVteprgTzMcBsKB04Sg9chsOrDMzDjImTBeYWGgwDygroM2E4hmShfz1E5IQ5il8djAN2Rf48McXLuvh2n0uWdNpoyfYfslscNHc4FHWwr0OU7gNw%2FGMB50kIeenUBSOOj5KfEhKKI62Y1atclDxZgGoRyz3ZUDZ8BVnI64ZyKD3sCsqoK2sy1OPaBL2Ubwce6juNLGwxl1ZR%2BQfJg%2BX%2BaVmbJaPOBIsPqgLetOnbjLyOM7frJX3%2BkDiDVazn%2F7b1o4Sn%2Bu2HVSEW9r0j%2BFPa2bI2fE384uMpy%2F1i9HLRoZd%2BcXTZB1kGlg86wHaQT2I%2FEQolWCA7uphDiFOilMw%2BhI3Sfy2EPF8gybNaBpt7sRNLrhO7Dqraz%2Fy%2FJPjttyOTDeah3H1IxwL5Y8soDvWp3n7tRXojmovGI%2Bb9EA%2FQYRVI%2F7XonNCaDwxQSVHjSbHvE2hBy1dAPbQq4IDgOcuh4hJW3Zbgdpi6JfseEgYjbn5wZFB6fvl9Q81rc8Z5sCKF2hCY0KUH%2Fn%2BiOCSFSg62cJtSDdii9G%2FRS6EvzuMf12WDbewMSgZJwcn%2BEv9omVtfc%2Fw6Ct4HOC%2Fl4oio6jlpxRyqISsbTRJ%2BZ1OF1jnAbIyQRhlKZOcMRG%2BS7b69S1gY6geuWoHdI9Hmc6dVQtZ9opoem0YzrXBeO39kX8z%2F%2FLLu%2BNdKkagKsAEP%2FdTI6xIRNykd7RIEFGEb0vHOlBklgdoVXeWb%2BixL21eX1alsWZa%2B0rFxBCSvad96Rv8I5DDzni989wL8aIbqBsH4CsBPhtsR2dyCtVRWepaG7ZNoDEV77eVY%2BB9qpkcBlYMt054azAuZJZpqBEnGzrxzW5qoMQMeapTdoPn6sxrH%2BFJ8JIFeIJKETKyPqCrd2%2BU0NPmbfc3VuuLpgCRIO%2Fc1XU0QLpYJpu9IYzFHRVR64oZ1WO6KiGvNyVB7DyprqM8fM1BgVI%2BX8LS679anOQSu9%2FdeB7nPKEaiUEOvw%2FPFkSSPYUsAi%2FwftuqjLpQJ3LjvzqFGFVWZoM%2FXJFp0wGKTT%2Fk3MdmzktFfAvcNILjocu%2FR%2BcBWf9FKpqgNIm4ZMcuqlfhpXQl6rKeALrjIrn1af%2F5cjVXPrtjI4Lfte21qjQiaeNO7iWTn%2BvExH2rTykg4WpXb5x%2BU%2BdQcG3TyuwrUdFAgK8UNdzuW2wUolpc%2BFsr5aqmByYLHNNsSVaKxKszpUx7v89Dsl4BDQI3xSkiuqfP0U5jjr84%2FcDdGkq3c87kcUZDVixUbypeoclub1cecTp8noTW%2FQmuflqM81TqsPqRu%2FJ6V7wK%2Fw9ddCaJ0tkKQDKCqEhNDdINqQ8C5%2Bw73kKSoWTV6C6PoD31McHJsCidGimh8VYS3a5%2F0Mj5AKuomegfhmk3bE6o1SvAonr9dfFWGnC1ysG4DbGqJTU%2BASVshqJk9eVsc20GOFZgopRuUHicIpry8wWOSyiCsoMzBwnh6FlvSrQ8YmwVnJRZ23Ftq1NJDx9Ct5xHog4EpgZH2fHAUIV6rB%2FjUIKE%2FsDhsTxK0f52N9%2FpINpXrQjItM%2FvaDpgECNLJ0TJIcN3MbEqKHc4eEvGKF82PWGzxZXqSMoQ686oJzApFq768oKEW35EKaR5O4an4b13EhO4136%2B0huOxZqKtLl2ktvIlBHqH2QrDBzmTdKWuSRM7ZslYtr5fOLghKpwWv0S9Jp%2FKNInQZ8iKC18Zc2%2F%2BT83HEjIMo9vPnTxLIayL994F2bKeuKB4B%2BiXjqRdwZKpEnvUCznbqFpumX3I7XkWO23SDWJoTe%2BHPBJiA34v61c43RLMAURyP9nnuzDQ60GE%2F63XngKbxsThO51w1j7xHnIFyCCRjIfBSDTnQeB0E%2FNWT4U%2FZPyGeQgXQhuTNohZychUZWhCNhK1%2FWoUh9p3l5fZrEqso4Sg1NWDsqWGuRsHAlVh8HHIluNTXT319NPJSLl049TeMTt6OXK3ZeDAMSHsL2HxYmb3RKKC9zR5ev3SaJeAol6ouGShFHGHCUtG2AS4kUMAdA1yw8LFvRNPDAMyAJ%2FQnI6TY%2Fcqotlg5Pi6cagpQ0xhDzPtJMwtNtAwUbNBCSYbkf%2FmmB1jtXaMkAiRLmD6EbRldiL7LGKAkewWjopRgZLifb91R2sUU%2FKskQKAKsqrKra6kO7lMUwnDIfPErY%2FLzn2K9JVIPE%2FVnhuVZRcseJwmBfoiSBPAVNVrpCbIMjiW%2FLi48Fu0Ra0z1La29UVn266A%2FAmOZLAdiZtQpKVDDAUemsGptyEsjEGzdV3HGTZjfmjESFIXOVmdYlpD4XeNDgXVN2JAoKEhTtNVsQsqfQKm5he7KBcsEL3c21aXlr%2BAAvGaDaX6THZP7D8g9Z4OBhH2LeP%2FHrFk0XTML50kIlR4itNR0b0s5jr7HTP2XssdWxBUvgENB3XYwzPUlESWAimvJsdxWL1YclddlEBg%2BenhDK7uQMQoVxTB%2Fits9zoFjE34WXS4muRStVIErspRCQgb0tc0jSnHKtK8OHL2ZuT6KwhstRgvlaimWK%2BDScmOANdcpdjfraU%2FOQ9YScB0F0dQGwH02nBrxDtwdxclFAuSQnG3rXrxeAa9JMbHbaWacbJC4o14ttvyH6cVOr%2FveuZ6hyxx%2BNBVDE%2BSg4NdgjjGcqDQylp5QdzLlAeU92XvpYsOwGM3Gy7vxVhc4jwDF7os%2BVdGgb8hIOeXRuQdxVRv31c72M1d6Ft2dDfz3fg%2BH0LwJnuT1FXoPN7lKIGPWCeXoS4vhJ6olvdKlJHdrJuzYiBgC6CnpnIuIhB4kKgKnQJxBbG1bTkm1AbMFANlxtoSlypgh86w%2B58SXmouM%2Fb99VQcYMka11z0B5K8tvnj5rV2WIRqq11UaR15W4WormWSiVL3MQxxRp75ajhg0Fcj8%2FDpvvxssEpC16WJGb7E9uP44yp3oCNWOfFJXLxAus3E6J%2BwFUXslpV2oLmtNo02sQWrN%2FzpjzRUv5vXWeaU6IwpjLD5ONwWshOsyOyxZ4wv1%2B1bFQkN2dFxtvdL3JcOc7KiEcUTwdzH8ly018MgNYeHJMyAiAK5usFFpDk%2B%2Bcr%2BcIxxiwEi9hp8YfB%2BVb7aW5Se2%2BM8lZCExds7ZNBHxkY8mqwCyMDr%2FVQKbFcNGqRTn1GOY4Hk6qhVKWtkS%2BjnBc7rVqGZRm12FL6YxoG6TWyRfKAxX4Ozf3yoTl7C5FGsnb1NRCN9Ox%2FSBnoqtomDShYvFTlq4pFLNm0wCFrIsZwM7Eq7yz95l4I9sXnNSZX6nYsF6MUuTuq2O2rprXpO8wNySMC1yXK4qxjyxCVDJOvgSFpqgNrel2WvDBExQSim6%2Fy0rQdE2u%2F8JcPLMTTV2w%2FiqdkwApOqn4h47yss9btMdqXBiSGgmN%2F38mZZMkT9X2rrRe9mJ6Yc8YOA7KjY5w7nWPvLQ6hHgYTiIkmwXmkBo%2B%2BbsGjkosi84%2FpzDndTrweD8FzuVJMnLD8qTi7jng48%2BlCynZfaISjb%2BUgQG27%2FN%2BCgs4DJgx2UUGuBvEsJvnqMAKiFJQC0qkjLfQnx3FFSyXM5USOjgDR4V7h5AkQJFcG6GppUhS%2FjDO%2FnWOcrZYuWrWk7hz%2FqQgjkx45Ov9guPER6dMtO9VFD8j6nxl6tC8ARVdIvxMMpjnKRe923SKuGLEuheEqItvnmfeE%2FjP9vFvNKV37wyWtUX37Ir33XHL2EsPKMk0%2BLPN26daySKrWfCm4BzfuUR8O53Vqfn0aUzkpHWrWuAi705oNHy5vLZ1JR56i0fKi3LPWSVuzDXCQKNa5ul5KP3wpwWYyhJPWbYrIgd5nzhGtuPFe7I56mtoQCrjFx9r2GymTAmnmCO8OVF3VpwJQqFEI6CGgIzjxX3OXaUxEpeOd3%2F7JWV%2BTx%2BSft1kquEH49UHp9WmTM5zzOVDpRadOTgKsOiDYhfHI%2BQQ619xCs3Ql1opl4s1Gp5D7qO%2FZypxZKKX5YVvDKHoWQY75HrevcM2R6ef1sh2PpGFJ%2Fodg2m9ge10zdZ%2BUBrnr%2Fu1Gfv6Y3zIrVgYMEA5YpC5dm7j6mCA2AYIh%2BomythHKymMbtKSstBNs7goMkixc6dN24LV7EZ10TpNL9Vj2vVUf6nxpLZXTq6H6Ci9NnipOMlbRfOUq%2FFu%2FDFqHQ7W2czP5ng65yecnuWqtm35pbc8VtIFaq2Q%2FPUy9DpxUu3s6I45bfv%2BfNpNYC19o045YzDc0fnECFxgoAl3tlRfJ1Sp21gs2cM2ASxZeEgvtdWPgrjEZqmbO5%2BMso%2F1ilc3AbLqDlxpXUQOdiKuGbvQJH12Ct%2BmfT7eQYoRNnlS9JQ%2FV4bkrGajMyNRkUq7zGRMmcFT%2BFNe8lzlPQbx8EjdOyjyvbWoZ3e27o3xiHrBxDuak4ufdmZjlyVA8bjYFp%2BftHpEL7hqRl5Yzb2sHMYHZxzZFqRbIuNkucFOo2HtdCilyR8PJfdHmrZ%2BVyA25MwJ2dZisQzcyhUjRwvGFZmjXb29ca63hLpEEx4HLQHHb0h49cn2%2BCQ%3D%3D&__PREVIOUSPAGE=SqsiqCojqqvwaWtXFSXZK9ikYCl6TqM7FKqQUIZplqXWEnGPkT7Eq1uyn9D8QJlg_vjoXfAt2gtDV3kGSJOieQ2&ctl00%24ContentPlaceHolder1%24radTipoBusqueda=6&ctl00%24ContentPlaceHolder1%24txtTitulo=&ctl00%24ContentPlaceHolder1%24txtAutor=&ctl00%24ContentPlaceHolder1%24ddlEditorial=&ctl00%24ContentPlaceHolder1%24cmbColeccion=&ctl00%24ContentPlaceHolder1%24cmbColeccion_Cascading_ClientState=&ctl00%24ContentPlaceHolder1%24cmbTemasBic=&ctl00%24ContentPlaceHolder1%24txtFIni=&ctl00%24ContentPlaceHolder1%24txtFIni_MaskedEditExtender_ClientState=&ctl00%24ContentPlaceHolder1%24rfvFechaIni_Extender_ClientState=&ctl00%24ContentPlaceHolder1%24txtFFin=&ctl00%24ContentPlaceHolder1%24txtFFin_MaskedEditExtender_ClientState=&ctl00%24ContentPlaceHolder1%24compValFechas_ValidatorCalloutExtender_ClientState=&ctl00%24ContentPlaceHolder1%24CompareValidator2_ValidatorCalloutExtender_ClientState=&ctl00%24ContentPlaceHolder1%24txtEditorial=&ctl00%24txtUsuarioAdmin=&ctl00%24txtPasswordAdmin=&ctl00%24txtUsuario=&ctl00%24txtPassword=&__ASYNCPOST=true&ctl00%24ContentPlaceHolder1%24btnVerMas=ver%20m%C3%A1s"
        #~ req = urllib2.Request(self.config['url_login'], urllib.urlencode(post))
        
        
        
        if post:                
            base_post = {
                #~ "ctl00$ScriptManager1" : quote("ctl00$ContentPlaceHolder1$ctl00|ctl00$ContentPlaceHolder1$btnVerMas"),
                #~ "__EVENTTARGET" : "",
                #~ "__EVENTARGUMENT" : "",
                #~ "ctl00$ContentPlaceHolder1$radTipoBusqueda" : 6,
                #~ "ctl00$ContentPlaceHolder1$txtTitulo" : "",
                #~ "ctl00$ContentPlaceHolder1$txtAutor" : "",
                #~ "ctl00$ContentPlaceHolder1$ddlEditorial" : "1ED",
                #~ "ctl00$ContentPlaceHolder1$cmbColeccion" : "",
                #~ "ctl00$ContentPlaceHolder1$cmbColeccion_Cascading_ClientState" : "",
                #~ "ctl00$ContentPlaceHolder1$cmbTemasBic" : "",
                #~ "ctl00$ContentPlaceHolder1$txtFIni" : "",
                #~ "ctl00$ContentPlaceHolder1$txtFIni_MaskedEditExtender_ClientState" : "",
                #~ "ctl00$ContentPlaceHolder1$rfvFechaIni_Extender_ClientState" : "",
                #~ "ctl00$ContentPlaceHolder1$txtFFin" : "",
                #~ "ctl00$ContentPlaceHolder1$txtFFin_MaskedEditExtender_ClientState" : "",
                #~ "ctl00$ContentPlaceHolder1$compValFechas_ValidatorCalloutExtender_ClientState" : "",
                #~ "ctl00$ContentPlaceHolder1$CompareValidator2_ValidatorCalloutExtender_ClientState" : "",
                #~ "ctl00$ContentPlaceHolder1$txtEditorial" : "",
                #~ "ctl00$txtUsuarioAdmin" : "",
                #~ "ctl00$txtPasswordAdmin" : "",
                #~ "ctl00$txtUsuario" : "",
                #~ "ctl00$txtPassword" : "",
                #~ "__ASYNCPOST" : True,
                #~ "ctl00$ContentPlaceHolder1$btnVerMas" : "ver más",
            }
            
            #~ new_post = base_post.copy()
            #~ new_post.update(post)
            
            #~ print post.keys()
            post['ctl00$ContentPlaceHolder1$radTipoBusqueda'] = "*"
            #~ post['ctl00$ContentPlaceHolder1$ddlEditorial'] = "TIM"
            #~ print new_post['__PREVIOUSPAGE']

            #~ base_post = "ctl00%24ScriptManager1=ctl00%24ContentPlaceHolder1%24ctl00%7Cctl00%24ContentPlaceHolder1%24btnVerMas&__PREVIOUSPAGE="
            #~ base_post += quote(post['__PREVIOUSPAGE'])
            #~ base_post += "&ctl00%24ContentPlaceHolder1%24radTipoBusqueda=6&ctl00%24ContentPlaceHolder1%24txtTitulo=&ctl00%24ContentPlaceHolder1%24txtAutor=&ctl00%24ContentPlaceHolder1%24ddlEditorial=&ctl00%24ContentPlaceHolder1%24cmbColeccion=&ctl00%24ContentPlaceHolder1%24cmbColeccion_Cascading_ClientState=&ctl00%24ContentPlaceHolder1%24cmbTemasBic=&ctl00%24ContentPlaceHolder1%24txtFIni=&ctl00%24ContentPlaceHolder1%24txtFIni_MaskedEditExtender_ClientState=&ctl00%24ContentPlaceHolder1%24rfvFechaIni_Extender_ClientState=&ctl00%24ContentPlaceHolder1%24txtFFin=&ctl00%24ContentPlaceHolder1%24txtFFin_MaskedEditExtender_ClientState=&ctl00%24ContentPlaceHolder1%24compValFechas_ValidatorCalloutExtender_ClientState=&ctl00%24ContentPlaceHolder1%24CompareValidator2_ValidatorCalloutExtender_ClientState=&ctl00%24ContentPlaceHolder1%24txtEditorial=&ctl00%24txtUsuarioAdmin=supercomics%40sdweb&ctl00%24txtPasswordAdmin=260952sdweb&ctl00%24txtUsuario=&ctl00%24txtPassword=&__EVENTTARGET=&__EVENTARGUMENT=&__VIEWSTATE="
            #~ base_post += quote(post['__VIEWSTATE'])
            #~ base_post += "&hiddenInputToUpdateATBuffer_CommonToolkitScripts=1&__ASYNCPOST=true&ctl00%24ContentPlaceHolder1%24btnVerMas=ver%20m%C3%A1s"
            #~ print quote(post['__VIEWSTATE'])[:300]
            #~ print post.keys()
            
            
            
            #~ tmp_post = base_post % ("a", "b")
            #~ tmp_post = base_post % (post['__PREVIOUSPAGE'], post['__VIEWSTATE'])
            req = urllib2.Request(url, urllib.urlencode(post))
        else:
            req = urllib2.Request(url)
            
        self.logger.info("[download_products] Descargando %s" % (url))
        
        downloaded = False
        tries = 0
        while not downloaded:
            try:
                tries += 1
                self.logger.info("[download_products] Descargando %s abriendo..." % (url))
                resp = opener.open(req, timeout = 30)
                self.logger.info("[download_products] Descargando %s abierto" % (url))
                time.sleep(1)
                #~ resp = urllib2.urlopen(req)
                downloaded = True
                
            except Exception, e:
                self.logger.info("[download_url] Descartando A. Error descargando %s - %s" % (url, str(e)))
                self.add_discard(url)
                
                
                return None
                
            except urllib2.HTTPError, e:
                self.logger.info("[download_url] Descartando B. Error descargando %s - %s" % (url, str(e)))
                if e.code in [404, 400]:
                    
                    return None
                self.add_discard(url)
                    
            except urllib2.URLError as e:
                self.logger.info("[download_products] Error descargando %s - %s" % (url, str(e)))
                if tries == 50:
                    return self.download_url(url)
                if tries > 50:
                    return False
                else:
                    self.logger.info("[download_products] Reintentando ...")
                time.sleep(tries * 2)
            
        try:
            data = resp.read()
        except Exception, e:
            self.logger.info("[download_url] Descartando al leer. Error descargando %s - %s" % (url, str(e)))
            self.add_discard(url)
            return None
        
        return data
    
    def download_url_login(self, url):
        
        cj = cookielib.CookieJar()
            
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

        opener.addheaders = [('User-agent', self.config['user_agent']), 
        ('HTTP_ACCEPT', 'text/html,application/xhtml+xml,application/xml; q=0.9,*/*; q=0.8'),
        ('Content-Type', 'application/x-www-form-urlencoded'),
        ('Host', 'www.zonalibros.com'),
        ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
        ('Accept-Language', 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3'),
        ('Connection', 'keep-alive'),
        ('Cache-Control', 'max-age=0'),
        ('Accept-Encoding', 'gzip,deflate')]

        self.logger.info("[download_url_login] opener")
        urllib2.install_opener(opener)
        
        url = quote(url.encode("utf-8"),":/?&=")
        for b in re.findall(".*?(%[0-9a-zA-Z]{2}).*?", url):
            url = url.replace(b, "")
        
        _url = self.config['url_login']
        _url = quote(_url.encode("utf-8"),":/&?")
        
        #~ req = urllib2.Request(_url, urllib.urlencode(post).replace("None", ""))
        req = urllib2.Request(_url, self.config['str_post'])
        #~ req = urllib2.Request(_url)
        
        ck = {}
        downloaded = False
        tries = 0
        while not downloaded:
            try:
                tries += 1
                self.logger.info("[download_url_login] url__ %s " % _url)
                self.logger.info("[download_url_login] open")
                resp = opener.open(req, timeout = 30)
                self.logger.info("[download_url_login] opened")
                #~ resp = urllib2.urlopen(req)
                
                ck = {c.name : c.value for c in cj}
                #~ print ck
                
                downloaded = 'ZONALIBROS.ASPXAUTH' in ck
                if not downloaded:
                    self.logger.warning("Respuesta correcta pero sin cookie de autorización")
                    if tries > 5:
                        raise Exception("No login")
            except urllib2.URLError as e:
                self.logger.warning("[download_url_login] Error descargando %s - %s" % (url, str(e)))
                if tries > 50:
                    raise
                else:
                    self.logger.warning("[download_url_login] Reintentando ...")
                time.sleep(tries * 2)
            
        #~ if 'content-encoding' in resp.headers and resp.headers['content-encoding'] == 'gzip':
            #~ try:
                #~ foo = gzip.GzipFile(fileobj = StringIO.StringIO(resp.read())).read()
            #~ except IOError:
                #~ return None
        #~ else:
            #~ foo = resp.read()
        
        
        #~ if 'content-encoding' in resp.headers and resp.headers['content-encoding'] == 'gzip':
            #~ try:
                #~ data = gzip.GzipFile(fileobj = StringIO.StringIO(resp.read())).read()
            #~ except IOError:
                #~ return None
        #~ else:
            #~ data = resp.read()
            #~ 
        #~ return data
        
        #####
        
        
        
        #~ ck['ZONALIBROS.ASPXAUTH'] = "01015218467FD833D108FEFFD772926D28CA2B0110450044004900300035003000340030007C00320039007C0035003000340030000743006C00690065006E0074006500012F00FF"
        #final url
        
        opener.addheaders = [('User-agent', self.config['user_agent']), 
        ('HTTP_ACCEPT', 'text/html,application/xhtml+xml,application/xml; q=0.9,*/*; q=0.8'),
        ('Content-Type', 'application/x-www-form-urlencoded'),
        ('Host', 'www.zonalibros.com'),
        ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
        ('Accept-Language', 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3'),
        ('referer', 'http://www.zonalibros.com/Clientes/Inicio.aspx'),
        ('Connection', 'keep-alive'),
        ('Cookie', 'ASP.NET_SessionId=%s; User=; CambioDist=N; ZONALIBROS.ASPXAUTH=%s; __utma=177133998.490927137.1399005954.1399005954.1399005954.1; __utmb=177133998.1.10.1399005954; __utmc=177133998; __utmz=177133998.1399005954.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)' % (ck['ASP.NET_SessionId'], ck['ZONALIBROS.ASPXAUTH'])),
        ('Cache-Control', 'max-age=0'),
        ('Accept-Encoding', 'gzip,deflate')]
        
        #~ url = "http://www.zonalibros.com/Clientes/FichaArticulo.aspx?libro=108.629861"
        url = quote(url.encode("utf-8"),":/&?=")
        
        self.logger.info("[download_url_login] request")
        #~ print "**" + url
        req = urllib2.Request(url)
        

        
        downloaded = False
        tries = 0
        while not downloaded:
            try:
                tries += 1
                self.logger.info("[download_url_login] open2")
                #~ print
                #~ print
                #~ print
                resp = opener.open(req, timeout = 30)
                self.logger.info("[download_url_login] opened2")
                #~ print resp.info()
                
                #~ resp = urllib2.urlopen(req)
                downloaded = True
            except urllib2.URLError as e:
                self.logger.info("[download_url_login] Error descargando %s - %s" % (url, str(e)))
                if tries > 50:
                    raise
                else:
                    self.logger.info("[download_url_login] Reintentando ...")
                time.sleep(tries * 2)
            
        if 'content-encoding' in resp.headers and resp.headers['content-encoding'] == 'gzip':
            try:
                data = gzip.GzipFile(fileobj = StringIO.StringIO(resp.read())).read()
            except IOError:
                return None
        else:
            data = resp.read()
            
        return data
        
    def add_discard(self, url = None):
        time.sleep(120)
        self.discards += 1
        if url:
            self.db.remove_url_type1(url)
        if self.discards > 10:
            self.logger.warning("[add_discard] Descartes máximos superados. Reiniciando.")
            time.sleep(600)
            self.db.reset_task(self.id_task)
            self.logger.warning("Descartes máximos superados. Reiniciando...")
            exit()
            
    def download_url(self, url, post = None):
        
        self.logger.info("[download_url] Descargando %s", url)
        
        try:
            url = url.replace("./", "/")
        except:
            pass
        
        cj = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

        opener.addheaders = [('User-agent', self.config['user_agent'])]

        urllib2.install_opener(opener)

        authentication_url = self.config['url_login']
        try:
            url = quote(url.encode("utf-8"),":/,")
        except:
            try:
                url = quote(url,":/,")
            except:
                pass
                
        for b in re.findall(".*?(%[0-9a-zA-Z]{2}).*?", url):
            url = url.replace(b, "")
        
        #~ url = url.replace(",", "%2C");
        
        
        post = {'URLx':quote(url.encode("utf-8"),":/").split(self.config['domain'])[1],
                'login':self.config['login'],
                'Password':self.config['password'],
                'Password':self.config['password'],
                'Ok': 'OK',
                'modo' : 'Cercador'}

        #~ req = urllib2.Request(self.config['url_login'], urllib.urlencode(post))
        #~ req = urllib2.Request(self.config['url_login'])
        
        downloaded = False
        tries = 0
        while not downloaded:
            try:
                tries += 1
                #~ resp = opener.open(req)
                self.logger.info("[download_url] Abriendo")
                resp = urllib2.urlopen(url)
                self.logger.info("[download_url] Abierto")
                #~ resp = urllib2.urlopen(req)
                downloaded = True
            except urllib2.HTTPError, e:
                self.logger.info("[download_url] Descartando C. Error descargando %s - %s" % (url, str(e)))
                
                if e.code in [404, 400]:
                    return None
                self.add_discard(url)
                return None
            except urllib2.URLError as e:
                self.logger.info("[download_url] Error descargando %s - %s" % (url, str(e)))
                
                if tries > 5:
                    return None
                else:
                    self.logger.info("[download_url] Reintentando ...")
                time.sleep(tries * 2)
            except Exception as e:
                self.logger.info("[download_url] Error descargando %s - %s" % (url, str(e)))
                
                if tries > 5:
                    return None
                else:
                    self.logger.info("[download_url] Reintentando ...")
                time.sleep(tries * 2)
        
        try:
            data = resp.read()
        except:
            return None
        
        self.logger.info("[download_url] devolviendo data")
        
        return data

    def load_external_stock(self):
        
        return True
        
        filename_xls = "temp.xls"
        f = open(filename_xls, "w")
        self.logger.info("[load_external_stock] descargando %s" % self.config['stock_external_xml'])
        f_web = urllib2.urlopen(self.config['stock_external_xml'])
        f.write(f_web.read())
        f.close()
        f_web.close()
            
        book = open_workbook(filename = filename_xls)
            
        sh = book.sheet_by_index(0)
        row_pos = 1
        try:
            while sh.cell_value(rowx=row_pos, colx=1):
                self.external_stock.append(sh.cell_value(rowx=row_pos, colx=1))
                row_pos += 1
        except IndexError:
            pass
            
        
    def is_in_external_stock(self, _id):
        if not self.external_stock:
            self.load_external_stock()
        return _id in self.external_stock
    
    def extract_product(self, url):
        """extract metadata from product page"""
        
        self.logger.info("[extract_product] %s" % url)
        
        html = self.download_url(url)
        if not html:
            return None
        
        
        self.tree = etree.fromstring(html, self.parser)
        
        self.metas = self.db.load_data(url)
        
        self.logger.info("[extract_product] obtenido algo? %s" % bool(self.metas))
        
        
        now = datetime.now()
        
        previous_metas = {}
        
        if self.metas:
            date_created = time.strptime(self.metas['extra_field_1'].strip(), "%d/%m/%Y")
        
            d_created = datetime(date_created.tm_year, date_created.tm_mon, date_created.tm_mday)
            
            if now > d_created and "PROXIMAMENTE" in self.metas['categories']:
                #not modified but publish date exceeded
                
                #to detect change
                previous_metas['stock'] = self.metas['stock'] + "0"
            else:
            
                #has been seen before
                content = "".join(self.extracts(self.xpaths['content'][0]))
                #~ self.logger.info("[]  %s" % self.metas['crc_content'])
                if crc32(content.strip().encode("utf-8")) == self.metas['crc_content']:
                    #no modifications
                    self.db.refresh_seen(url, self.id_task)
                    #ensure images
                    if self.config['check_images_without_changes']:
                        self.upload_images()
                    return True
                    
                previous_metas['stock'] = self.metas['stock']
                previous_metas['price'] = self.metas['price']
                previous_metas['thumbnail'] = self.metas['thumbnail']
                previous_metas['categories'] = self.metas['categories']
                
            self.logger.info("[extract_product] tiempos")
        
        self.init_metas(previous_metas)
        
        
        self.logger.info("[extract_product] categorias")
        
        #~ self.tree = etree.parse(url, self.parser)
        
        
        
        for meta, _xpath in self.xpaths.items():
            #~ with_label = len(_xpath) > 1
            with_label = False
            
            for xpath in _xpath:
                #~ xpath = _xpath[0].replace("$1",str(i+1))
                extract = self.extract(xpath) if meta not in ["content"]  else "".join(self.extracts(xpath))
                
                if meta == "images":
                    index_image = 2
                    for image in self.extracts(xpath):
                        self.metas['image' + str(index_image)] = image
                        index_image += 1
                
                if not extract:
                    if self.verbose:
                        print "\t", meta, _xpath
                    continue
                if self.verbose:
                    print meta, extract, _xpath
                try:
                    if not with_label:
                        self.metas[meta] = extract
                    else:
                        if "|" in _xpath[1]:
                            ok = False
                            for label in _xpath[1].split("|"):
                                if label in extract.upper():
                                    if meta == "label_stock" and "EAN" in extract.upper():
                                        continue
                                    ok = True
                                    break
                        else:
                            ok = _xpath[1] in extract.upper()
                        
                        if ok:
                            self.metas[meta] = extract.split(":")[1] if ":" in extract else extract
                            break
                        else:
                            continue
                            #~ self.metas[meta] = "*********" + extract + "|" + _xpath[1]
                        
                    
                except:
                    print "Ha fallado: ", meta, extract, _xpath
                    raise
        
            if meta in self.metas:
                self.metas[meta] = self.metas[meta].strip()
        
        
        category = None
        
        if not 'categories' in self.metas:
        
            if ('reference' in self.metas):
                category, subcategory = self.get_external(self.metas['reference'])
                
            if not category:
                if ('extra_field_7' in self.metas):
                    category, subcategory = self.get_external(self.metas['extra_field_7'])
                else:
                    if ('extra_field_11' in self.metas):
                        category, subcategory = self.get_external(self.metas['extra_field_11'])
            
            if not category:
                return None
                
            category = category.split("-")[0].strip()
            subcategory = subcategory.split("-")[0].strip()
            
            self.metas['category'] = category.upper()
            self.metas['subcategory'] = subcategory.upper()
            
            #remove tildes
            self.metas['category'] = self.normalize_category(self.metas['category'])
            self.metas['subcategory'] = self.normalize_category(self.metas['subcategory'])
            
            is_merchandising = "MERCHANDISING" in self.metas['category']
            
            
            #category validations
            if self.metas['category'] in self.category_alias:
                if isinstance(self.category_alias[self.metas['category']], basestring):
                    self.metas['category'] = self.category_alias[self.metas['category']]
                else:
                    #subcategory
                    if self.metas['subcategory'] in self.category_alias[self.metas['category']]:
                        self.metas['subcategory'] = self.category_alias[self.metas['category']][self.metas['subcategory']]
                        
            if self.metas['subcategory'] in self.subcategory_alias:
                self.metas['subcategory'] = self.subcategory_alias[self.metas['subcategory']]
            
            
            #category bans
            if self.metas['category'] in self.category_ban:
                if isinstance(self.category_ban[self.metas['category']], basestring):
                    return False
                else:
                    #subcategory
                    if self.metas['subcategory'] in self.category_ban[self.metas['category']]:
                        return False
        
        
        
        
        precio_neto = False
                
        if "lprice" in self.metas and "rprice" in self.metas:   
            self.metas['price2'] = self.metas['lprice'] if "PRECIO FINAL" in self.metas['rprice'] else self.metas['rprice']
            precio_neto = "PRECIO NETO" in self.metas['price2']
            
            
            self.metas['price2'] = self.metas['price2'].replace(u"€", "").replace(u"\xe2\x82\xac", "")
            #~ self.logger.info("[extract_product] price2 %s" % repr(self.metas['price2']))
            
            #~ self.metas['price2'] = self.metas['price2'].split(":")[1].strip()
            del self.metas['lprice']
            del self.metas['rprice']

        if not 'price2' in self.metas:
            self.metas['price2'] = "0"
        
        if precio_neto:
            self.metas['cost'] = self.metas['price2']
            self.metas['price2'] = float(self.metas['cost'].replace(".","").replace(",",".")) * 1.55
            self.metas['price'] = float(self.metas['cost'].replace(".","").replace(",",".")) * 1.50
        else:
            self.metas['cost'] = float(self.metas['price2'].replace(".","").replace(",",".")) * 0.7
            self.metas['price'] = float(self.metas['price2'].replace(".","").replace(",",".")) * 0.95
        
        
        #~ self.logger.info("[extract_product] precio")
        
        date_created = time.strptime(self.metas['date'].strip(), "%d/%m/%Y")
        self.metas['extra_field_1'] = time.strftime("%d/%m/%Y", date_created)
        self.metas['date_created'] = time.strftime("%m/%d/%Y", date_created)
        
        d_created = datetime(date_created.tm_year, date_created.tm_mon, date_created.tm_mday)
        
        if not 'manufacturer'in self.metas:
            self.metas['manufacturer'] = "VARIOS"
        
        if self.metas['manufacturer'] in self.manufacturer_alias:
            self.metas['manufacturer'] = self.manufacturer_alias[self.metas['manufacturer']]
            
        title_collection = get_title_collection(self.metas['title'], 
            self.metas['category'], self.metas['manufacturer'], 
            False, self.categories_like_merchandising)
        
        manufacturer = self.metas['manufacturer'] if self.metas['manufacturer'] else "VARIOS"
        
        l_stock = self.metas['label_stock'].lower()
        
        #~ self.logger.info("[extract_product] varios")
        
        if not 'categories' in self.metas:
            self.logger.info("[extract_product] no categories!")
            #~ if now > d_created: 
            if not u"próxima" in l_stock: 
                #CATEGORIA_PRINCIPAL@CATEGORIA_PRINCIPAL/SUBCATEGORIA@CATEGORIA_PRINCIPAL/SUBCATEGORIA/EDITORIAL@CATEGORIA_PRINCIPAL/SUBCATEGORIA/EDITORIAL/TITULO -(menos ó sin) NUMERO COLECCION
                
                if is_merchandising:
                    level_2 = title_collection.replace(manufacturer, "").strip()
                    self.metas['categories'] = "%s@%s/%s@%s/%s/%s@%s/%s/%s/%s" % \
                      (self.metas['category'], self.metas['category'], level_2, \
                      self.metas['category'], level_2, self.metas['subcategory'], \
                      self.metas['category'], level_2, self.metas['subcategory'], manufacturer)

                else:
                    self.metas['categories'] = "%s@%s/%s@%s/%s/%s@%s/%s/%s/%s" % \
                      (self.metas['category'], self.metas['category'], self.metas['subcategory'], \
                      self.metas['category'], self.metas['subcategory'], manufacturer, \
                      self.metas['category'], self.metas['subcategory'], manufacturer, \
                      title_collection)
            else:
                #comming
                if is_merchandising or self.metas['category'] in self.categories_like_merchandising:
                    self.metas['categories'] = "PROXIMAMENTE@PROXIMAMENTE/%s@PROXIMAMENTE/%s/%s@PROXIMAMENTE/%s/%s/%s" % \
                      (self.metas['category'], self.metas['category'], self.metas['subcategory'], \
                      self.metas['category'], self.metas['subcategory'], title_collection )
                else:
                    self.metas['categories'] = "PROXIMAMENTE@PROXIMAMENTE/%s@PROXIMAMENTE/%s/%s@PROXIMAMENTE/%s/%s/%s" % \
                      (self.metas['category'], self.metas['category'], self.metas['subcategory'], \
                      self.metas['category'], self.metas['subcategory'], manufacturer)
        
        self.metas['homespecial'] = 1 if abs((now - d_created).days) <10 else 0
        
        #~ self.logger.info("[extract_product] pre-images")
        
        for key_image, sufix in {'thumbnail':'_tb', 'image1':'', 'image2':'_2', 'image3':'_3', 'image4':'_4'}.items():
            if key_image in self.metas:
                if not "http" in self.metas[key_image]:
                    self.metas[key_image] = "http://%s%s" % (self.config['domain'], self.metas[key_image])
                filename = "%s%s.jpg" % (self.metas["id"], sufix)
                self.download_img(self.metas[key_image], filename , thumbnail = key_image == "thumbnail" )
                
                
                finalname = "%s%s/%s/%s/%s" % (self.config['url_images'], self.metas['category'], self.metas['subcategory'], \
                  self.metas['manufacturer'], filename)
                self.metas[key_image] = "%s.jpg" % self.normalize_path(finalname.replace(".jpg", ""))
                    
            
            #~ self.logger.info("[extract_product] images")
            
            if not 'category' in self.metas:
                self.metas['category'] = "UNK"
            self.metas['tax_code'] = 'IVL' if self.metas['category'] in ['LIBROS', 'COMICS', 'DVD-BLU RAY', 'REVISTAS'] else 'IVO'
        
        def smart_truncate(content, length=100, suffix=''):
            if len(content) <= length:
                return content
            else:
                return ' '.join(content[:length+1].split(' ')[0:-1]) + suffix
        
        def clean_spaces(s):
            while "  " in s:
                s = s.replace("  ", " ")
            return s
                
        if 'description' in self.metas:
            self.metas['description'] = smart_truncate(clean_spaces(self.metas['description']))
        if 'extended_description' in self.metas:
            self.metas['extended_description'] = clean_spaces(self.metas['extended_description'])
        
        
        keys_keywords = ["categories", "category", "subcategory", "manufacturer", "title", "extra_field_10", "extra_field_3"]
        self.metas['keywords'] = ", ".join(self.metas[i].strip() for i in keys_keywords if i in self.metas and len(self.metas[i])>1)
        
        def cut_last_comma(s):
            if s[-1] == ",":
                s = s[:-1]
            if s[-2] == ", ":
                s = s[:-2]
            return s
        
        self.metas['keywords'] = cut_last_comma(self.metas['keywords'])
        if 'extra_field_10' in self.metas:
            self.metas['extra_field_10'] = cut_last_comma(self.metas['extra_field_10'])
        
        self.metas['metatags'] = '<META NAME="KEYWORDS" CONTENT="%s">' % self.metas['keywords']
        
        
        
        self.metas['stock'] = 40 if u"próxima" in l_stock else 10 \
          if "saldado" in l_stock or "disponible" in l_stock else 0
          
        if is_merchandising and not self.is_in_external_stock(self.metas['id']):
            self.metas['stock'] = 0
            
        if d_created > now: 
            self.metas['stock'] = 40
            
        self.logger.info("[extract_product] keywords")
        
        if previous_metas:
            #has been seen already
            if previous_metas['stock'] == self.metas['stock'] and \
                previous_metas['price'] == self.metas['price'] and \
                previous_metas['thumbnail'] == self.metas['thumbnail']:
                #has modifications but not in price or stock. Dont update.
                return True
            
          
        self.metas['instock_message'] = "Pre-Reserva" if self.metas['stock'] == 40 \
          else "Añadir a Lista de Espera" if self.metas['stock'] == 0 \
          else "Envío 5 a 7 Días"
          
          
        #all products of this categories when stock > 0 have a custom message
        categories_order = ['ACCESORIOS', 'DVD-BLU RAY', 'MERCHANDISING', 'JUEGOS']
        if self.metas['stock'] > 0 and any(cat in self.metas['category'] for cat in categories_order):
            self.metas['instock_message'] = "Disponible Bajo Pedido"
        
          
        self.metas['reward_points'] = int(self.metas['price'] * 20 if d_created > now else self.metas['price'] * 10)
        
        self.metas['extra_field_4'] = self.metas['extra_field_4a'] if 'extra_field_4a' in self.metas \
          and self.metas['extra_field_4a'] else self.metas['extra_field_4b'] \
          if 'extra_field_4b' in self.metas else ""
          
        if 'extra_field_11' in self.metas and self.metas['extra_field_11']:
            self.metas['extra_field_11'] = "<div>%s</div>" % self.metas['extra_field_11']
            
        #~ encode_keys = ["id", "mfgid", "title", "name", "categories", "extra_field_10", "thumbnail", \
          #~ "image1", "image2", "image3", "image4", "content", "extra_field_3", "extra_field_2", "extra_field_5", "manufacturer"] 
        #~ for encode_key in encode_keys:
            #~ if encode_key in self.metas:
                #~ try:
                    #~ self.metas[encode_key] = self.metas[encode_key].encode("utf-8")
                #~ except:
                    #~ print encode_key, self.metas[encode_key], repr(self.metas[encode_key])
                    #~ 
                    #~ raise
        if isinstance(self.metas['price2'], basestring):
            self.metas['price2'] = self.metas['price2'].replace(",", ".")
        if isinstance(self.metas['cost'], basestring):
            self.metas['cost'] = self.metas['cost'].replace(",", ".")
        for meta in self.metas:
            if isinstance(self.metas[meta],float):
                self.metas[meta] = str(round(self.metas[meta],2))
            #~ print meta, self.metas[meta]
            else:
                if isinstance(self.metas[meta],basestring):
                    try:
                        self.metas[meta] = self.metas[meta].encode("utf-8")
                    except UnicodeDecodeError:
                        pass
                        
        self.logger.info("[extract_product] to save")
                        
        
        self.db.save_data(url, self.metas, self.id_task)
        #~ self.print_line(self.get_metas_orderer())
        
        self.logger.info("[extract_product] to upload")
        self.upload_images()
        
        self.logger.info("[extract_product] Fin")
        
    def upload_images(self):
        
        
        connected = False
        tries = 0
        while not connected:
            try:
                ftps = mFTP_TLS()
                ftps.connect(self.config['ftp_host'], port=990, timeout = 60)
                ftps.login(self.config['ftp_user'], self.config['ftp_pass'])
                ftps.prot_p()
                connected = True
            except:
                
                tries +=1
                if tries > 2:
                    return False
                time.sleep(tries * 2)
            
        
        
        
        #~ print ftps.retrlines('LIST')
        
        for key_image in ['thumbnail', 'image1', 'image2', 'image3', 'image4']:
            ftps.cwd(self.config['path_images'])
            if key_image in self.metas and self.metas[key_image]:
                
                self.logger.info("[upload_images] subiendo %s" % self.metas[key_image].replace(self.config['url_images'],""))
                paths = [self.config["root_img"]] + self.metas[key_image].replace(self.config['url_images'],"").split("/")[:-1]
                filename = self.metas[key_image].replace(self.config['url_images'],"").split("/")[-1]
                local_filename = os.path.join(os.path.dirname(__file__),"imgs/%s" % filename)
                for path in paths:
                    try:
                        ftps.cwd(path)
                    except:
                        created = False
                        tries = 0
                        while not created:
                            try:
                                ftps.mkd(path)
                                created = True
                            except:
                                tries +=1
                                if tries > 50:
                                    raise
                                time.sleep(tries * 2)
                        try:
                            ftps.cwd(path)
                        except error_perm as e:
                            if not "550" in str(e):
                                raise
                            else:
                                pass
                
                #check if exists
                try:
                    if ftps.size(filename) == os.path.getsize(local_filename):
                        #exists
                        self.logger.info("[upload_images] ya habia copia en el ftp de %s" % self.metas[key_image].replace(self.config['url_images'],""))
                        continue
                except error_perm as e:
                    if not "550" in str(e):
                        raise
                    else:
                        #file not exists
                        pass
                
                f = open(local_filename, 'rb')
                uploaded = False
                tries = 0
                while not uploaded:
                    try:
                        ftps.storbinary('STOR ' + filename, f, 1024)
                        uploaded = True
                    except:
                        self.logger.warning("[upload_images] reintando subida %s" % local_filename)
                        tries +=1
                        if tries > 50:
                            raise
                        time.sleep(tries * 2)
                
                    
        ftps.quit()
    
    def get_external(self, extra_field_7):
        #~ f = open("a.html", "w")
        #~ f.write(self.download_url_login(self.config['url_external'] % extra_field_7))
        #~ f.close()
        html = None
        try:
            url = self.config['url_external'] % extra_field_7.replace("-", "") 
            self.logger.info("[get_external] descargando %s" % url)
            html = self.download_url_login(url)
        except Exception as e:
            self.logger.warning("No se ha podido descargar %s" % str(e))
        
        if not html:
            self.logger.info("[get_external] No se encuentra ")
            return None, None
        
        self.logger.info("[get_external] Analizando ")
        tree = etree.fromstring(html , self.parser)
        self.logger.info("[get_external] Analizado ")
        
        find = etree.XPath('//*[@id="ctl00_MainContent_txtCI"]//text()')
        
        try:
            #~ ref = find(tree)[0]
            #~ find = etree.XPath('//*[@id="ctl00_MainContent_txtPublicacion"]//text()')
            #~ date = find(tree)[0]
            #~ find = etree.XPath('//*[@id="ctl00_MainContent_lblDisponible"]//text()')
            #~ stock_label = find(tree)[0]
            find = etree.XPath('//*[@id="ctl00_MainContent_lblTipoArt"]//text()')
            category = find(tree)[0]
            find = etree.XPath('//*[@id="ctl00_MainContent_txtCategoria"]//text()')
            subcategory = find(tree)[0]
            #~ stock = 0 if "agotado" in stock_label.lower() else 10
            return category, subcategory
        except IndexError:
            self.logger.info("[get_external] No se encuentra ")
            return None, None
        #ctl00_MainContent_txtCI
    
        
    def get_metas_orderer(self):
        """select metas required"""
        
        #~ self.logger.info("[get_metas_orderer] ordenando %s " % self.metas)

        return [self.metas[meta] if meta in self.metas and self.metas[meta] \
          else "N/A" for meta in self.config['csv_header']]
        #~ return [self.metas[meta] if meta in self.metas and self.metas[meta] \
          #~ or (not "extra_field" in meta) else "N/A" for meta in self.config['csv_header']]

        
    def print_line(self, line, header = False):
        """print line in csv"""
        
        #~ pprint([str(i).replace(",", ".") if is_number(i) else i for i in line])
        #~ pprint([is_number(i) for i in line])
        with open(self.filename_csv, 'wb' if header else 'ab') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter='\t',quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
            csvwriter.writerow(line)
            
    def run(self):
        """start complete crawler"""
        
        self.logger.info("[run] iniciando(Completo=%s)" % self.mode_complete)
        
        try:
            self.db.init_task(self.id_task)
            
            #~ self.generate_csv()
            #~ 
            #~ self.db.finish_task(self.id_task)
            #~ exit();
            
            self.logger.info("[run] comprobando get_title_collection")
            if not test_get_title_collection():
                self.logger.info("[run] hay algún problema con get_title_collection. Revisar...")
                self.db.finish_task(self.id_task, True)
                return False
                
            links = []
            
            
            def extract_links(html, url_discover):
                self.logger.info("[extract_links] sacando de %s" % url_discover )
                
                self.tree = etree.fromstring(html, self.parser)
                post = {}
                for _input in self.extracts("//*[@id='form1']//input"):
                    if "value" in _input.attrib:
                        #~ print _input.attrib['name'], "-->", _input.attrib['value']
                        post[_input.attrib['name']] = _input.attrib['value'].encode('ascii', 'ignore')
                        #~ post[_input.attrib['name']] = _input.attrib['value']

                
                #~ print post.keys()
                
                
                html = self.download_products(url_discover, post)
                #~ f.write(html)
                #~ f.close
                
                self.db.save_url_type1(url_discover, self.id_task, html)
                
                for link in self.extracts("//a"):
                    if "href" in link.attrib and "isbn" in link.attrib["href"].lower() and not "javascript" in link.attrib["href"].lower():
                            
                        url = "http://%s/%s" %(self.config['domain'], link.attrib["href"].replace("./", ""),)
                        
                        if not url in links:
                            self.db.save_url_type1(url, self.id_task)
                            links.append(url)
            
            self.urls_seed = self.db.get_data_urls_t1()
            
            self.logger.info("[run] urls seed %s" % len(self.urls_seed) )
            
            urls_seen = []
            
            if not self.urls_seed:
                discover_urls = self.config['discover_url']
                
                num = 0
                for editorial in self.config['editorials']:
                    discover_urls.append(self.config['url_editorial'] % editorial)
                    num += 1
                    #~ if num > 50:
                        #~ break
                    
                
                
                first = True
                
                for url_discover in self.config['discover_url']:
                    #~ f = open("a.html", "w")
                    #~ 
                    html = self.download_products(url_discover)
                    #~ f.write(html)
                    #~ f.close()
                    
                    
                    html_md5 = None
                    i = 0
                    no_changes = 0
                    last_len = 0
                    while html and html_md5 != md5(html) and no_changes < 10:
                        html_md5 = md5(html)
                        i += 1
                        self.logger.info("[run] page %s" % i )
                        #~ f = open("a%s.html" % i, "w")
                        
                        extract_links(html, url_discover)
                        
                        self.logger.info("[run] Almacenados %s enlaces" % len(links) )
                        
                        #~ pprint(links)
                        #~ print len(links)
                        if last_len == len(links):
                            no_changes += 1
                            if not first:
                                break
                        else:
                            no_changes = 0
                        
                        last_len = len(links)
                        
                    first = False
            else:
                links = self.urls_seed
                urls_seen = self.db.get_data_urls_t1(self.id_task)
                
                
                
            

            any_new = True
            news = 200;
            while any_new:

                any_new = False

                rediscover = list(links)
                rediscover_count = len(rediscover)
                
                loop = 0
                for url_discover in rediscover:
                    
                    if "Isbn--Codigo" in url_discover:
                        continue
                    
                    loop += 1
                    if not url_discover in urls_seen:
                        if (news < 0):
                            any_new = True
                        else:
                            news -= 1
                        
                        html = self.download_products(url_discover)
                        urls_seen.append(url_discover)
                        
                        if not html:
                            continue
                        
                        extract_links(html, url_discover)
                        
                        
                        
                        self.logger.info("[run] (B) Almacenados %s enlaces" % len(links) )
                        self.logger.info("[run] rediscover [%s/%s]" % ( rediscover_count, loop) )
                        
            
            urls_seen = []
            
            
            link_count = len(links)
            loop = 0
            for url in links:
                if "Isbn--Codigo" in url:
                    continue
                loop += 1
                
                self.logger.info("[run] extrayendo [%s/%s]" % ( link_count, loop) )
                if not url in urls_seen:
                    self.extract_product(url)
                    urls_seen.append(url)
                    
                    
                
    
            #~ self.tree = etree.fromstring(self.download_url(self.config['start_url']), self.parser)
            #~ start_week = self.extract("/html/body/table[2]/tr[1]/td[3]/table[3]/tr[6]/td/a[1]/@href").split("/")[-2]
            #~ 
            #~ week = int(start_week[-2:])
            #~ year = int(start_week[:4])
            #~ start_year = year
            #~ 
            #~ #forward
            #~ n_products = 1
            #~ while n_products > 0:
                #~ print year, week
                #~ n_products = self.extract_products(year, week)
                #~ print year, week, n_products
                #~ self.logger.info("[run] extraidos %s productos en %s/%s" % ( n_products, year, week))
                #~ week += 1
                #~ if week > 52:
                    #~ week = 1
                    #~ year += 1
                #~ #to end of year
                #~ if year == start_year:
                    #~ n_products = 1
            #~ #back
            #~ week = int(start_week[-2:])
            #~ year = int(start_week[:4])
            #~ n_products = 1
            #~ current_week = True
            #~ while n_products > 0:
                #~ #skip the current
                #~ if not current_week:
                    #~ print year, week
                    #~ n_products = self.extract_products(year, week)
                    #~ print year, week, n_products
                #~ current_week = False
                #~ week -= 1
                #~ if week < 1:
                    #~ week = 52
                    #~ year -= 1
                #~ if year > 2002:
                    #~ n_products = 1


                    
            #metas utf8 to iso 
            
                    
            self.generate_csv()
            
            self.db.finish_task(self.id_task)
        except Exception as e:
            self.db.finish_task(self.id_task, True)
            
            exc_type, exc_obj, exc_tb = sys.exc_info()
            #~ fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            #~ print(exc_type, fname, exc_tb.tb_lineno)
            #~ 
            self.logger.error("%s\n %d: %s" %(traceback.format_exc(), exc_tb.tb_lineno, str(e)))
            raise
        
    
    def generate_csv(self):
        """generate csv from db"""
        
        self.logger.info("[generate_csv] task: %s modo:%s" % (self.id_task, self.mode_complete))
        datas = self.db.get_data_task(self.id_task, self.mode_complete)
        
        self.logger.info("[generate_csv] %d urls" % len(datas))
        
        for url_data in datas:
            self.metas = url_data
            self.metas['category'] = self.metas['categories'].split("@")[0]
            #~ self.metas['manufacturer'] = self.metas['categories'].split("/")[-2]
            
            try:
                title_collection = get_title_collection(self.metas['title'], 
                    self.metas['category'], self.metas['manufacturer'], 
                    False, self.categories_like_merchandising)
            except AttributeError:
                #raise when categories_like_merchandising is not defined
                #without categories_like_merchandising use old title
                title_collection = get_title_collection(self.metas['title'], 
                    self.metas['category'], self.metas['manufacturer'])
            
            if type(title_collection) == type(u""):
                title_collection = title_collection.encode("utf-8")
            
            if title_collection != self.metas['title']:
                number_collection = get_number_collection(self.metas['title'], self.metas['id'], self.metas['category'])
                
                related = self.db.get_related(title_collection, number_collection, self.id_task)
                accesories =  self.db.get_accesories(title_collection, number_collection, self.id_task)
                
                #related
                if related:
                    self.metas['related'] = ",".join([r for r in related if r != url_data['id']])
                
                #accesories
                if accesories:
                    self.metas['accessories'] = ",".join([a for a in accesories if a != url_data['id']])
                    
            
            self.print_line(self.get_metas_orderer())
        
        datas = self.db.get_data_task_removed_lite(self.id_task)
        
        self.logger.info("[generate_csv] %d urls removed" % len(datas))
        
        for url_data in datas:
            self.metas = self.db.load_data(url_data['url'])
            #~ self.metas = url_data
            self.metas['category'] = self.metas['categories'].split("@")[0]
            self.metas['manufacturer'] = self.metas['categories'].split("/")[-2]
            
            try:
                title_collection = get_title_collection(self.metas['title'], 
                    self.metas['category'], self.metas['manufacturer'], 
                    False, self.categories_like_merchandising)
            except AttributeError:
                title_collection = get_title_collection(self.metas['title'], 
                    self.metas['category'], self.metas['manufacturer'])
            
            
            if type(title_collection) == type(u""):
                title_collection = title_collection.encode("utf-8")
                
            
            if title_collection != self.metas['title']:
                number_collection = get_number_collection(self.metas['title'], self.metas['id'], self.metas['category'], )
                
                related = self.db.get_related(title_collection, number_collection, self.id_task)
                accesories =  self.db.get_accesories(title_collection, number_collection, self.id_task)
                
                #related
                if related:
                    self.metas['related'] = ",".join(related)
                
                #accesories
                if accesories:
                    self.metas['accessories'] = ",".join(accesories)
                    
            #removed
            self.metas['extra_field_13'] = "Borrado"
            self.metas['stock'] =  0
            self.metas['instock_message'] = "Añadir a Lista de Espera"
            
            self.print_line(self.get_metas_orderer())
    
    def extract_products(self, year, week):
        """extract all products of the page"""
        
        url = self.config['discover_url'] % (int(year), int(week))
        
        self.logger.info("[extract_products] recorriendo %s" % url)
        self.tree = etree.fromstring(self.download_url(url), self.parser)
        
        
        n_products = 0
        products = self.extracts('//div[@class="reg1"]')
        for product in products:
            try:
                subcategory, category = product.xpath("./a//node()")
            except ValueError:
                subcategory = "VARIOS"
                category = product.xpath("./a//node()")[0]
            
            self.extract_product("http://%s%s" % (self.config['domain'] , \
                    product.xpath("./a/@href")[0]), category, subcategory)  
            
            n_products += 1
            
            
        return n_products
        
        
        
if __name__ == '__main__':
    
    
    if len(sys.argv) == 1:
        crawl = CrawlerComics(verbose = False)
        crawl.run()
    else:
        if "http" in sys.argv[1]:
            for url in sys.argv[1:]:
                crawl = CrawlerComics()
                #~ crawl.extract_product(url, "a", "b")
                

                #~ crawl.extract_product(url, u"COMICS", u"COMIC ESPAÑOL")
                crawl.extract_product(url)
                crawl.generate_csv()
            
                crawl.db.finish_task(crawl.id_task)
        else:
            crawl = CrawlerComics(id_task = sys.argv[1], mode = sys.argv[2])
            crawl.run()
            
    
        
        