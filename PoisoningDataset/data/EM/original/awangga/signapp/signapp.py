#!/usr/bin/env python
"""
signapp.py 
created by Rolly Maulana Awangga

"""
import config
import urllib.request
import random
import time
from Crypto.Cipher import AES
import gspread
from oauth2client.service_account import ServiceAccountCredentials


class Signapp(object):
    def __init__(self):
        self.key = config.key
        self.iv = config.iv

    def opendb(self):
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
        client = gspread.authorize(creds)
        self.sheet = client.open(config.sheet)

    def getPertemuan(self):
        return config.pertemuanke
    
    def tokenUri(self):
        return config.tokenuri

    def random(self, ln):
        ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        chars = []
        for i in range(ln):
            chars.append(random.choice(ALPHABET))
        return "".join(chars)

    def urlEncode16(self, uri):
        ln = len(uri)
        sp = 16 - ln - len(str(ln))
        if ln > 9:
            dt = str(ln) + uri + self.random(sp)
        else:
            dt = "0" + str(ln) + uri + self.random(sp - 1)
        return self.encodeData16(dt)

    def urlDecode16(self, uri):
        if len(uri) % 16 == 0:
            dt = self.decodeData16(uri)
            try:
                int(dt[:2])
                ln = int(dt[:2])
                ret = dt[2:2 + ln]
            except ValueError:
                ret = dt
        else:
            ret = uri
        return ret

    def setTTL(self, token):
        return self.db.set(token, "valid")

    def getTTL(self, token):
        return self.db.get(token)

    def getAllSign(self, npm):
        ambil = self.sheet.get_worksheet(config.nilai).cell(self.sheet.get_worksheet(config.nilai).find(npm).row,self.sheet.get_worksheet(config.nilai).find('rata_rata').col).value
        return ambil

    def getSign(self, npm, num):
        colnum = config.namakolom + str(num)
        try:
            ambil = self.sheet.get_worksheet(config.nilai).cell(self.sheet.get_worksheet(config.nilai).find(npm).row,
                                                                self.sheet.get_worksheet(config.nilai).find(
                                                                    colnum).col).value
        except:
            ambil = 'kosong'
        return ambil

    def getPhoto(self, data):
        if data[:3] == "117":
            cdn = config.cdn17
        else:
            cdn = config.cdn18
        result = '<h2>' + data + '</h2><img src="' + cdn + data + '.jpg"><ul>'
        return result

    def getPertemuan(self):
        return config.pertemuanke

    def setSign(self, npm, num, Nilai, Pembimbing, Topik):
        colnum = config.namakolom + str(num)
        try:
            ambil = self.sheet.get_worksheet(config.nilai).update_cell(
                self.sheet.get_worksheet(config.nilai).find(npm).row,
                self.sheet.get_worksheet(config.nilai).find(colnum).col, Nilai)
            ambil = self.sheet.get_worksheet(config.komentar).update_cell(
                self.sheet.get_worksheet(config.komentar).find(npm).row,
                self.sheet.get_worksheet(config.komentar).find(colnum).col, Topik)
            ambil = self.sheet.get_worksheet(config.tanggal).update_cell(
                self.sheet.get_worksheet(config.tanggal).find(npm).row,
                self.sheet.get_worksheet(config.tanggal).find(colnum).col, time.strftime("%d/%m/%Y"))
            ambil = self.sheet.get_worksheet(config.pembimbing).update_cell(
                self.sheet.get_worksheet(config.pembimbing).find(npm).row,
                self.sheet.get_worksheet(config.pembimbing).find(colnum).col, Pembimbing)
        except:
            ambil = 'kosong'
        return ambil

    def insertTodayOnly(self, NPM, Nilai, Pembimbing, Topik):
        self.setSign(NPM, config.pertemuanke, Nilai, Pembimbing, Topik)
        try:
            cekNilai = self.sheet.get_worksheet(config.nilai).cell(self.sheet.get_worksheet(config.nilai).find(NPM).row,self.sheet.get_worksheet(config.nilai).find(config.namakolom+str(config.pertemuanke)).col).value
            if cekNilai != '':
                return "done"
            else:
                return "failed"
        except:
            return "failed"

    def encodeData16(self, msg):
        obj = AES.new(self.key, AES.MODE_CBC, self.iv)
        cp = obj.encrypt(msg)
        return cp.hex()

    def decodeData16(self, msg):
        obj = AES.new(self.key, AES.MODE_CBC, self.iv)
        dec = bytes.fromhex(msg)
        return obj.decrypt(dec).decode('utf-8')

    def getHtmlBegin(self):
        return config.html_begin

    def getHtmlEnd(self):
        return config.html_end

    def getHtmlForm(self):
        return config.html_form

    def getMenu(self, uri):
        if uri == config.keyuri:
            opsi = "key"
        elif uri == config.tokenuri:
            opsi = "token"
        else:
            opsi = "other"
        return opsi

    def getTokenData(self, token):
        url = config.tokenurl + token
        response = urllib.request.urlopen(url)
        html = response.read()
        return html.decode('utf-8')

    def emailAcl(self, email):
        if email.split('@')[1] == config.domainacl:
            return True
        else:
            return False

    def tokenValidation(self, token):
        html = self.getTokenData(token)
        if (html.find(config.aud) > 0) and (html.find(config.iss) > 0):
            ret = "valid"
        else:
            ret = "invalid"
        return ret

    def getJsonData(self, name, json):
        lookup = '"%s": "' % name
        b = json.find(lookup)
        c = json[b:].find(':')
        c += 1
        b = b + c
        c = json[b:].find(',')
        c = b + c
        data = json[b:c].strip().strip('"')
        return data
