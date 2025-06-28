#!/usr/bin/env python
# -.- coding: utf-8 -.-y
import base64
import datetime
import getpass
import os
import Queue
import socket
import sqlite3
import subprocess
import sys
import time
import threading
from cmd import Cmd
from Crypto.Cipher import AES
from Crypto import Random
#Created by Camerin Figueroa
cv = "2.0"
q = Queue.Queue()
q.put([[]])
errors = Queue.Queue()
errors.put([])
motd = Queue.Queue()
quit = Queue.Queue()
quit.put("")
mesg = Queue.Queue()
mesg.put("")
online = Queue.Queue()
online.put([])
print """\33[91m
═════════════════════════════════════════════════════════
                ███████    ██████         ███████
               █           █     █       █ ║
              █            █════╗ █   ╔═█  ║
             █═════════════█    ╚█    ║█═══╝
             █             ██████     ║█
              █            █   █      ╚╗█  ╔═══════Server
               █════════╗  █    █      ╚═█ ║
                ███████ ║  █     █        ███████
Chat Room Client════════╝
═════════════════════════════════════════════════════════
\33[92m"""
port = 99999
configcont = "#Replace Everything behind = sign\n#Ex before: config = edit\n#Ex after: config = configinput\n\nmotd = Hello world This is a new Chat Room Server made by Camerin Figueroa\nport = 22550\ndatabase = ./crdb.db"
if os.path.isfile('./crsconfig.txt') == True:
    f = open('./crsconfig.txt', 'r')
    configuration = f.read()
    f.close()
    configuration = configuration.split("\n")
    for line in configuration:
        if "motd =" in line:
            motd.put(line[6:])
        else:
            pass
        if "database =" in line:
            dbdir = line[11:]
        else:
            pass
        if "port = " in line:
            port = int(line[7:])

        else:
            pass

else:
    f = open('./crsconfig.txt', 'w')
    f.write(configcont)
    f.close()
    print "Please edit crsconfig.txt"
    sys.exit()
if port != 99999:
    pass
else:
    f = open('./crsconfig.txt', 'w')
    f.write(configcont)
    f.close()
    print "Please edit crsconfig.txt"
    sys.exit()
def console(q, errors, motd):
    if __name__ == '__main__':
        prompt = consoleprompt()
        prompt.prompt = '> '
        prompt.cmdloop('Starting prompt...')
class consoleprompt(Cmd):
    def do_say(self, args):
        if args == "" or args == " ":
            print "say messagetosay\nor\nsay Message to say"
        else:
            curtime = str(int(time.time()))
            curmes = mesg.get()
            if curmes.split(":")[0] == curtime:
                mesg.put(curmes)
            else:
                db = q.get()
                db[1].append("OP" + ":" + args)
                q.put(db)
                mesg.put(curtime + ":" + "OP" + ":" + args)
    def do_printdb(self, args):
        global q
        self.quit = quit
        db = q.get()
        q.put(db)
        tick = 0
        for line in db:
            for lin in line:
                if tick == 0:
                    for li in lin:
                        print li
                    tick = 1
                else:
                    print lin
    def do_online(self, args):
        global online
        on = online.get()
        online.put(on)
        print "Online:"
        for username in on:
            print username
    def do_printerrors(self, args):
        global errors
        erlist = errors.get()
        errors.put(erlist)
        print "Errors:"
        for error in erlist:
            print error
    def do_motd(self, args):
        if "-c" in args:
            global motd
            oldmotd = motd.get()
            motd.put(args[3:])
            print "motd changed from " + oldmotd + " to " + args[3:]
        else:
            print "add -c newcmd"
    def do_quit(self, args):
        global quit
        print "Quitting.\33[97m"
        quit.get()
        quit.put("quitting:")
        time.sleep(2)
        os._exit(0)
    def do_printdatabase(self, args):
        conn = sqlite3.connect(dbdir)
        c = conn.cursor()
        print "Under Development"
    def do_adduser(self, args):
        if args == "":
            print "adduser username"
            print "password prompt will pop up once you run the command."
        else:
            global dbdir
            conn = sqlite3.connect(dbdir)
            c = conn.cursor()
            c.execute("SELECT EXISTS(SELECT 1 FROM userbase WHERE username='" + args + "' LIMIT 1)")
            if int(c.fetchall()[0][0]) == 1:
                print "Username already used"
            else:
                c.execute("SELECT MAX(id) FROM userbase")
                maxid = int(c.fetchall()[0][0])
                c.execute("insert into userbase values('" + args + "', '" + getpass.getpass() + "', '" + str(maxid + 1) + "');")
                conn.commit()


class Server(object):
    def __init__(self, host, port, q, motd, errors, mesg, quit, online, conn, c):
        self.c = c
        self.conn = conn
        self.motd = motd
        self.quit = quit
        self.errors = errors
        self.host = host
        self.port = port
        self.q = q
        self.mesg = mesg
        self.online = online
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
    def listen(self):
        self.sock.listen(5)
        while True:
            try:
                client, address = self.sock.accept()
                client.settimeout(60)
                threading.Thread(target = self.listenToClient,args = (client,address)).start()
            except:
                pass
    def listenToClient(self, client, address):
        global cv, now, dbdir
        conn = sqlite3.connect(dbdir)
        c = conn.cursor()
        rcv = client.recv(128)
        if str(cv) != str(rcv[3:]) and "cv:" in rcv and rcv != "screen:":
            client.send("comp:0:" + str(cv))
            error = self.errors.get()
            error.append("Error client is wrong version")
            self.errors.put(error)
            kill1 = 1
        else:
            client.send("comp:1")
            client.recv(1024)
            client.send("ping")
            time2 = int(round(time.time()*1000))
            client.recv(1024)
            time3 = int(round(time.time()*1000))
            keytime = str(time.time())
            hm = now.strftime("%H%M")
            if time2 - time3 > 250:
                error = self.errors.get()
                error.append("Error ping is longer than 250 ms.")
                self.errors.put(error)
                client.send("ptl:250")
                kill1 = 1
            else:
                pass
            if len(keytime) < 32:
                add = 32 - len(keytime)
                key = str(keytime)
                for num in range(add):
                    key = key + "#"
            else:
                pass
            encrypt = AESCipher(key)
            usern = encrypt.decrypt(client.recv(1024))
            uget = "SELECT username FROM userbase WHERE username = '" + usern + "';"
            c.execute(uget)
            users = c.fetchall()
            ucheck = 0
            for user in users:
                if str(user[0]) == usern:
                    c.execute("SELECT username,yash,id FROM userbase WHERE username = '" + usern + "';")
                    userbase = c.fetchone()
                else:
                    pass
            #userbase =
            kill = 0
            try:
                if userbase:
                    client.send(encrypt.encrypt("succ:sendek"))
                else:
                    kill = 1
            except:
                client.send(encrypt.encrypt("err:nousername"))
                client.close()
                kill = 1
            kill1 = 0
            if kill == 0:
                encrypt = AESCipher(yash(str(userbase[1])) + hm)
                syncmessage = encrypt.decrypt(client.recv(1024))
                if len(syncmessage) == 10:
                    try:
                        int(syncmessage)
                    except:
                        client.send("kill:wpass")
                        #kill Connection
                        kill1 = 1
                else:
                    client.send("kill:wpass")
                    #kill Connection
                    client.close()
                    kill1 = 1
                if kill1 == 0:
                    client.send(encrypt.encrypt("pass:excepted"))
                    c.execute("insert into logs values('" + str(int(userbase[2])) + "', '" + str(userbase[0]) + " has logged in..." + "', '" + str(now.strftime("%Y:%M:%D:%H:%M:%S")) + "');")
                else:
                    c.execute("insert into logs values('" + str(int(userbase[2])) + "', '" + str(userbase[0]) + " failed to login with on IP:" + str(address[0]) + "', '" + str(now.strftime("%Y:%M:%D:%H:%M:%S")) + "');")
                conn.commit()
            else:
                rcv = "cv:n/a"
        if kill1 == 1:
            pass
        elif str(cv) != rcv[3:] and "cv:" in rcv:
            pass
        elif rcv == "screen:":
            online = self.online.get()
            self.online.put(online)
            client.send(encrypt.encrypt(str(online)))
            cmessage = self.mesg.get()
            self.mesg.put(cmessage)
            lm = cmessage
            tick = 0
            qi = False
            try:
                while qi == False:
                    cmessage = self.mesg.get()
                    self.mesg.put(cmessage)
                    online = self.online.get()
                    self.online.put(online)
                    if cmessage != lm:
                        csend = cmessage.split(":")
                        client.send(encrypt.encrypt(csend[1] + ":" + csend[2]))
                        lm = cmessage
                    else:
                        pass
                    quit = self.quit.get()
                    self.quit.put(quit)
                    if tick == 1000:
                        client.send(encrypt.encrypt("online:" + str(online)))
                        onlinecheck = encrypt.decrypt(client.recv(1024))
                        if onlinecheck == "quitting:":
                            quit = "quitting:"
                            qi = True
                        else:
                            pass
                        tick = 0
                    else:
                        pass
                    tick = tick + 1
                    if quit == "quitting:":
                        client.send(encrypt.encrypt("quitting:"))
                        client.close()
                        qi = True
                    else:
                        pass
                    time.sleep(.001)
            except:
                error = self.errors.get()
                error.append("A screen raised an error")
                self.errors.put(error)
                pass
        else:
            client.send(encrypt.encrypt("comp:1"))
            name = encrypt.decrypt(client.recv(1024))
            if "user:" not in name:
                client.send(encrypt.encrypt("error:wrong type of packet received. 'user:' was not within the packet"))
                erlist = errors.get()
                erlist.append(str(client.getpeername() + ":wrong type of packet received. 'user:' was not within the packet"))
                errors.put(erlist)
            else:
                name = name[5:]
                used = False
                online = self.online.get()
                self.online.put(online)
                for user in online:
                    if user == name:
                        used = True
                    else:
                        pass
                if used == True:
                    client.send(encrypt.encrypt("error:Username has already been used before."))
                    client.close()
                    erlist = errors.get()
                    erlist.append(str(name + ":" + name + ":Username has already been used before."))
                    errors.put(erlist)
                    check = False
                else:
                    client.send(encrypt.encrypt("user:" + name))
                    check = True
            if check == True:
                db = q.get()
                q.put(db)
                leng = 1
                for nam in db[0]:
                    if name in nam:
                        nl = leng
                    else:
                        leng = leng
                if 'nl' in locals():
                    db[0][nl - 1].append(address)
                else:
                    nl = leng
                    db.append([name,])
                    db[0].append([name, address])
                    q.get()
                    q.put(db)
                try:
                    online = self.online.get()
                    online.append(name)
                    self.online.put(online)
                    warntim = 0
                    while True:
                            rmesg = encrypt.decrypt(client.recv(1024))
                            if "" == rmesg:
                                pass
                            elif "/help" == rmesg:
                                pass
                            elif "quitting:" == rmesg:
                                on = online.get()
                                on.remove(name)
                                online.put(on)
                            elif "ping:" == rmesg:
                                pass
                            elif "m3ssg::" in rmesg:
                                curtime = str(int(time.time()))
                                curmes = self.mesg.get()
                                if curmes.split(":")[0] == curtime:
                                    self.mesg.put(curmes)
                                    warntim = warntim + 1
                                    if warntim == 100:
                                        client.close()
                                    else:
                                        pass
                                else:
                                    db = q.get()
                                    db[leng].append(name + ":" + rmesg[7:])
                                    q.put(db)
                                    self.mesg.put(curtime + ":" + name + ":" + rmesg[7:])
                            else:
                                print "add this to log errors. unknown packet"
                                print rmesg
                except:
                    online = self.online.get()
                    if name in online:
                        online.remove(name)
                    else:
                        pass
                    self.online.put(online)
            else:
                pass
def writeoutput(q, errors):
    if os.path.isdir("./logs") == False:
        subprocess.Popen(['mkdir', './logs'], stdout=subprocess.PIPE,).communicate()[0]
    else:
        pass
    tim = str(datetime.datetime.now())
    tim = tim.replace(" ", "")
    log = "./logs/log" + tim + ".txt"
    while True:
        try:
            time.sleep(10)
            tta = q.get()
            q.put(tta)
            error = errors.get()
            errors.put(error)
            fw = "Users:\n"
            errs = ""
            for err in error:
                errs = errs + err + "\n"
            for line in tta:
                for lin in line:
                    fw = fw + str(lin) + "\n"
            fw = fw + "═════════════════════════════════════════════════════════\nErrors:\n" + errs
            f = open(log, 'w')
            f.write(fw)
            f.close()
        except:
            error = errors.get()
            error.append("Error while writing output\n")
            errors.put(error)
#Added in Chat Room 2.0
if os.path.isfile(dbdir) == True:
    dbexist = 1
else:
    dbexist = 0

now = datetime.datetime.now()
conn = sqlite3.connect(dbdir)
c = conn.cursor()
if dbexist == 1:
    pass
else:
    print "Initializing database..."
    time.sleep(1)
    print "Please put a new username and password into the database..."
    good = False
    while good == False:
        usern = raw_input("username:")
        passw = getpass.getpass()
        tmp = raw_input("Are you sure thats correct?(Y/N)")
        if tmp == "y" or tmp == "Y" or tmp == "ye" or tmp == "YE" or tmp == "YES" or tmp == "Yes" or tmp == "YEs" or tmp == "yes" or tmp == "" or tmp == " ":
            good = True
        else:
            pass
    c.execute("CREATE TABLE userbase (username real, yash real, id real);")
    c.execute("CREATE TABLE logs (id real, message real, timestamp real);")
    c.execute("insert into userbase values('" + usern + "', '" + passw + "', '1');")
    conn.commit()
def yash(inp):
    try:
        partial = inp + 1
        print "Error this is not a string"
        sys.exit()
    except:
        pass
    tick = 0
    hexlists = [
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '26', '27', '28', '29', '20', '2a', '2b', '2c', '2d', '2e', '2f', '31', '32', '33', '34', '35', '36', '37', '38', '39', '30', '3a', '3b', '3c', '3d', '3e', '3f', '41', '42', '49', '21', '22', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '52', '53', '72', '73', '74', '75', '76', '77', '54', '55', '56', '57', '58', '59', '50', '5a', '5b', '5c', '5d', '5e', '5f', '61', '62', '63', '64', '43', '44', '45', '46', '47', '48', '65', '66', '67', '68', '69', '60', '6a', '6b', '6c', '6d', '6e', '6f', '71', '78', '79', '70', '7a', '7b', '7c', '7d', '7e', '7f'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '37', '38', '39', '30', '3a', '6e', '6f', '71', '78', '79', '26', '27', '28', '29', '70', '7a', '7b', '7c', '7d', '7e', '7f', '20', '2a', '2b', '2c', '2d', '2e', '2f', '31', '32', '3b', '3c', '3d', '3e', '3f', '41', '42', '49', '21', '22', '5c', '5d', '5e', '5f', '61', '62', '63', '64', '43', '44', '45', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '52', '53', '72', '73', '74', '75', '76', '77', '54', '55', '56', '57', '58', '59', '50', '5a', '5b', '46', '47', '48', '65', '66', '67', '68', '69', '60', '6a', '6b', '6c', '6d', '33', '34', '35', '36'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '50', '5a', '5b', '46', '47', '48', '65', '66', '67', '68', '69', '60', '6a', '6b', '6c', '6d', '33', '34', '35', '36', '37', '38', '26', '27', '28', '29', '70', '7a', '7b', '7c', '7d', '7e', '7f', '20', '2a', '2b', '2c', '2d', '2e', '2f', '31', '32', '3b', '3c', '3d', '61', '62', '63', '64', '43', '44', '45', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '52', '53', '72', '73', '74', '75', '76', '77', '54', '55', '56', '57', '58', '59', '39', '30', '3a', '6e', '6f', '71', '78', '79', '3e', '3f', '41', '42', '49', '21', '22', '5c', '5d', '5e', '5f'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '7f', '20', '2a', '2b', '2c', '2d', '2e', '2f', '31', '32', '3b', '3c', '3d', '61', '62', '63', '64', '43', '44', '45', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '52', '53', '72', '73', '74', '75', '76', '77', '54', '55', '5d', '5e', '5f', '56', '57', '58', '59', '39', '30', '3a', '6e', '6f', '71', '78', '79', '3e', '3f', '41', '42', '49', '21', '22', '5c', '48', '65', '66', '67', '68', '69', '60', '6a', '6b', '6c', '6d', '33', '34', '35', '36', '37', '38', '26', '50', '5a', '5b', '46', '47', '27', '28', '29', '70', '7a', '7b', '7c', '7d', '7e'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '79', '3e', '3f', '41', '42', '49', '21', '22', '5c', '48', '65', '66', '67', '68', '69', '60', '6a', '6b', '6c', '6d', '74', '75', '76', '77', '54', '55', '5d', '33', '34', '35', '36', '50', '5a', '5b', '46', '47', '27', '28', '29', '70', '7a', '7b', '7c', '7d', '7e', '7f', '20', '2a', '2b', '2c', '2d', '2e', '2f', '31', '32', '3b', '3c', '3d', '61', '62', '63', '64', '43', '44', '45', '3a', '6e', '6f', '71', '78', '37', '38', '26', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '52', '53', '72', '73', '5e', '5f', '56', '57', '58', '59', '39', '30'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '48', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '52', '53', '72', '73', '5e', '5f', '65', '66', '67', '68', '69', '60', '6a', '6b', '6c', '6d', '74', '75', '76', '77', '54', '55', '5d', '33', '34', '35', '36', '50', '5a', '5b', '46', '47', '27', '28', '29', '70', '7a', '7b', '7c', '7d', '7e', '7f', '20', '2a', '2b', '2c', '2d', '2e', '2f', '31', '32', '3b', '3c', '3d', '61', '62', '63', '64', '43', '44', '45', '56', '57', '58', '59', '39', '30', '3a', '6e', '6f', '71', '78', '37', '38', '26', '79', '3e', '3f', '41', '42', '49', '21', '22', '5c'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '79', '3e', '3f', '41', '42', '49', '21', '22', '5c', '48', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '52', '53', '72', '73', '5e', '5f', '65', '66', '67', '32', '3b', '3c', '3d', '61', '62', '63', '64', '43', '44', '45', '56', '57', '68', '69', '60', '6a', '6b', '6c', '6d', '74', '75', '76', '77', '54', '55', '5d', '33', '34', '35', '36', '50', '5a', '31', '58', '59', '39', '30', '3a', '6e', '6f', '71', '78', '37', '38', '26', '5b', '46', '47', '27', '28', '29', '70', '7a', '7b', '7c', '7d', '7e', '7f', '20', '2a', '2b', '2c', '2d', '2e', '2f'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '79', '3e', '3f', '41', '42', '49', '21', '22', '5c', '48', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '52', '53', '72', '73', '5e', '5f', '65', '66', '67', '32', '3b', '3c', '3d', '61', '62', '63', '7b', '7c', '7d', '7e', '7f', '20', '2a', '2b', '2c', '2d', '2e', '2f', '31', '58', '59', '39', '30', '3a', '6e', '6f', '71', '64', '43', '44', '45', '56', '57', '68', '69', '60', '6a', '6b', '6c', '6d', '74', '75', '76', '77', '54', '55', '5d', '33', '34', '35', '36', '50', '5a', '5b', '46', '47', '27', '28', '29', '70', '7a', '78', '37', '38', '26'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '79', '3e', '3f', '41', '5d', '33', '34', '35', '36', '50', '5a', '5b', '46', '47', '27', '28', '29', '70', '7a', '78', '37', '38', '26', '42', '49', '21', '22', '5c', '48', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '62', '63', '7b', '7c', '7d', '7e', '7f', '20', '2a', '2b', '2c', '2d', '2e', '2f', '31', '58', '59', '39', '30', '3a', '6e', '6f', '71', '64', '43', '44', '45', '56', '57', '68', '69', '60', '6a', '6b', '6c', '6d', '74', '75', '76', '77', '54', '55', '52', '53', '72', '73', '5e', '5f', '65', '66', '67', '32', '3b', '3c', '3d', '61'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '29', '70', '7a', '78', '37', '38', '26', '42', '7e', '7f', '20', '2a', '2b', '2c', '2d', '2e', '57', '68', '69', '60', '79', '3e', '3f', '41', '5d', '33', '34', '35', '36', '50', '5a', '5b', '46', '47', '27', '28', '6a', '6b', '6c', '6d', '74', '75', '76', '77', '54', '55', '52', '53', '72', '73', '5e', '5f', '65', '66', '67', '32', '3b', '3c', '3d', '61', '2f', '31', '58', '59', '39', '30', '3a', '6e', '6f', '71', '64', '43', '44', '45', '56', '49', '21', '22', '5c', '48', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '62', '63', '7b', '7c', '7d'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '56', '49', '21', '22', '5c', '48', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '62', '63', '7b', '7c', '7d', '34', '35', '36', '50', '5a', '5b', '46', '47', '27', '28', '6a', '29', '70', '7a', '78', '37', '38', '26', '42', '7e', '7f', '20', '2a', '2b', '2c', '2d', '2e', '57', '68', '69', '60', '79', '3e', '3f', '41', '5d', '33', '3c', '3d', '61', '2f', '31', '58', '59', '39', '30', '3a', '6e', '6f', '71', '64', '43', '44', '45', '6b', '6c', '6d', '74', '75', '76', '77', '54', '55', '52', '53', '72', '73', '5e', '5f', '65', '66', '67', '32', '3b'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '46', '47', '27', '28', '6a', '29', '70', '7a', '78', '37', '38', '26', '42', '7e', '7f', '20', '2a', '3a', '6e', '6f', '71', '64', '43', '44', '45', '6b', '6c', '6d', '74', '75', '76', '56', '49', '21', '22', '5c', '48', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '62', '63', '7b', '7c', '7d', '34', '35', '36', '50', '5a', '5b', '77', '54', '55', '52', '53', '72', '73', '5e', '5f', '65', '66', '67', '32', '3b', '2b', '2c', '2d', '2e', '57', '68', '69', '60', '79', '3e', '3f', '41', '5d', '33', '3c', '3d', '61', '2f', '31', '58', '59', '39', '30'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '7f', '20', '2a', '3a', '6e', '6f', '71', '64', '43', '44', '45', '6b', '6c', '6d', '74', '75', '76', '56', '49', '79', '3e', '3f', '41', '5d', '33', '3c', '3d', '61', '2f', '31', '58', '59', '39', '30', '21', '22', '5c', '48', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '62', '63', '7b', '7c', '7d', '34', '35', '36', '50', '5a', '5b', '77', '54', '55', '52', '53', '72', '73', '5e', '5f', '65', '66', '67', '32', '3b', '2b', '2c', '2d', '2e', '57', '68', '69', '60', '46', '47', '27', '28', '6a', '29', '70', '7a', '78', '37', '38', '26', '42', '7e'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '49', '79', '3e', '3f', '41', '5d', '33', '3c', '3d', '61', '2f', '31', '58', '59', '39', '30', '21', '22', '5c', '67', '32', '3b', '2b', '2c', '2d', '2e', '57', '68', '69', '60', '48', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '62', '63', '7b', '7c', '7d', '34', '35', '36', '50', '5a', '5b', '77', '54', '55', '52', '53', '72', '73', '5e', '5f', '65', '66', '46', '47', '27', '28', '6a', '29', '70', '7a', '78', '37', '38', '26', '42', '7e', '7f', '20', '2a', '3a', '6e', '6f', '71', '64', '43', '44', '45', '6b', '6c', '6d', '74', '75', '76', '56'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '39', '30', '21', '22', '5c', '67', '32', '3b', '2b', '2c', '2d', '2e', '57', '68', '69', '60', '48', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '62', '63', '7b', '7c', '7d', '34', '35', '36', '50', '5a', '5b', '77', '54', '55', '6d', '74', '75', '76', '49', '79', '3e', '3f', '41', '5d', '33', '3c', '3d', '61', '2f', '31', '58', '59', '56', '52', '53', '72', '73', '5e', '5f', '65', '66', '46', '47', '27', '28', '6a', '29', '70', '7a', '78', '37', '38', '26', '42', '7e', '7f', '20', '2a', '3a', '6e', '6f', '71', '64', '43', '44', '45', '6b', '6c'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '4c', '4d', '4e', '4f', '51', '62', '63', '7b', '7c', '7d', '34', '35', '36', '50', '5a', '5b', '77', '54', '55', '6d', '74', '75', '76', '49', '79', '3e', '3f', '41', '5d', '7e', '7f', '20', '2a', '3a', '6e', '6f', '71', '64', '43', '44', '45', '6b', '6c', '33', '3c', '39', '30', '21', '22', '5c', '67', '32', '3b', '2b', '2c', '2d', '2e', '57', '68', '69', '60', '48', '23', '24', '25', '40', '4a', '4b', '3d', '61', '2f', '31', '58', '59', '56', '52', '53', '72', '73', '5e', '5f', '65', '66', '46', '47', '27', '28', '6a', '29', '70', '7a', '78', '37', '38', '26', '42'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '28', '6a', '29', '70', '7a', '78', '37', '38', '26', '42', '46', '4c', '55', '6d', '74', '75', '76', '49', '79', '3e', '3f', '41', '5d', '7e', '7f', '20', '2a', '3a', '6e', '6f', '71', '64', '43', '44', '45', '6b', '6c', '33', '3c', '39', '30', '21', '4d', '4e', '4f', '51', '62', '63', '7b', '7c', '7d', '34', '35', '36', '50', '5a', '5b', '77', '54', '22', '5c', '67', '32', '3b', '2b', '2c', '2d', '2e', '57', '68', '69', '60', '48', '23', '24', '25', '40', '4a', '4b', '3d', '61', '2f', '31', '58', '59', '56', '52', '53', '72', '73', '5e', '5f', '65', '66', '47', '27'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '25', '40', '4a', '3f', '41', '5d', '7e', '7f', '20', '2a', '3a', '6e', '6f', '71', '64', '43', '44', '45', '6b', '6c', '33', '3c', '39', '30', '21', '4d', '4c', '55', '6d', '74', '75', '76', '49', '79', '3e', '4e', '4f', '51', '62', '63', '7b', '7c', '7d', '34', '35', '36', '50', '5a', '5b', '77', '54', '22', '5c', '67', '32', '3b', '2b', '2c', '2d', '69', '60', '48', '23', '24', '4b', '3d', '61', '2f', '31', '58', '59', '56', '52', '53', '72', '38', '26', '42', '73', '5e', '66', '47', '27', '28', '6a', '29', '70', '7a', '78', '37', '46', '5f', '65', '2e', '57', '68'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '64', '43', '44', '45', '6b', '6c', '33', '3c', '39', '30', '21', '4d', '4c', '70', '7a', '78', '37', '46', '5f', '65', '2e', '57', '68', '55', '6d', '74', '75', '76', '49', '25', '40', '4a', '3f', '41', '5d', '7e', '7f', '20', '2a', '3a', '6e', '6f', '71', '79', '3e', '4e', '4f', '51', '62', '63', '7b', '7c', '7d', '34', '35', '36', '50', '5a', '5b', '77', '54', '22', '5c', '67', '32', '3b', '2b', '2c', '2d', '69', '60', '48', '23', '24', '4b', '3d', '61', '2f', '31', '58', '59', '56', '52', '53', '72', '38', '26', '42', '73', '5e', '66', '47', '27', '28', '6a', '29'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '3c', '39', '30', '21', '4d', '4c', '70', '7a', '78', '37', '46', '5f', '65', '2e', '57', '68', '55', '6d', '74', '75', '76', '49', '25', '40', '4a', '3f', '41', '5d', '7e', '7f', '20', '2a', '3a', '6e', '6f', '71', '79', '3e', '4e', '4f', '51', '62', '63', '7b', '7c', '52', '53', '72', '38', '26', '42', '73', '5e', '64', '43', '44', '45', '6b', '6c', '33', '66', '47', '27', '28', '6a', '29', '7d', '34', '35', '36', '50', '5a', '5b', '77', '54', '22', '5c', '67', '32', '3b', '2b', '2c', '2d', '69', '60', '48', '23', '24', '4b', '3d', '61', '2f', '31', '58', '59', '56'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '60', '48', '23', '24', '4b', '3d', '61', '2f', '31', '58', '59', '56', '7f', '20', '2a', '3a', '6e', '6f', '71', '79', '3e', '57', '68', '55', '6d', '74', '75', '76', '49', '25', '40', '4a', '3f', '41', '5d', '7e', '2d', '69', '4e', '4f', '51', '62', '63', '7b', '7c', '52', '53', '72', '38', '26', '42', '73', '5e', '3c', '39', '30', '21', '4d', '4c', '70', '7a', '78', '37', '46', '5f', '65', '2e', '64', '43', '44', '45', '6b', '6c', '33', '66', '47', '27', '28', '6a', '29', '7d', '34', '35', '36', '50', '5a', '5b', '77', '54', '22', '5c', '67', '32', '3b', '2b', '2c'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '20', '28', '6f', '71', '78', '38', '79', '6c', '29', '70', '7b', '26', '7a', '27', '7c', '7d', '7e', '7f', '2a', '2b', '2c', '2d', '2e', '2f', '31', '32', '3b', '3c', '3d', '3e', '3f', '41', '42', '49', '21', '63', '64', '43', '44', '45', '23', '24', '25', '40', '4a', '66', '67', '22', '5c', '5d', '5e', '5f', '61', '62', '68', '69', '60', '4b', '4c', '6a', '6b', '4d', '4e', '4f', '51', '52', '53', '72', '73', '74', '75', '76', '77', '54', '55', '56', '57', '58', '59', '50', '5a', '5b', '46', '47', '48', '65', '6d', '33', '34', '35', '36', '37', '39', '30', '3a', '6e'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '27', '7c', '7d', '7e', '7f', '2a', '59', '50', '5a', '5b', '46', '47', '48', '65', '6d', '33', '34', '35', '36', '37', '39', '30', '3a', '6e', '2b', '2c', '2d', '2e', '2f', '31', '32', '3b', '3c', '3d', '3e', '3f', '41', '42', '49', '21', '63', '64', '43', '44', '45', '23', '24', '25', '40', '4a', '66', '67', '22', '5c', '5d', '5e', '5f', '61', '62', '68', '69', '60', '4b', '4c', '6a', '6b', '4d', '4e', '4f', '51', '20', '28', '6f', '71', '78', '38', '79', '6c', '29', '70', '7b', '26', '7a', '52', '53', '72', '73', '74', '75', '76', '77', '54', '55', '56', '57', '58'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '48', '34', '7c', '27', '7d', '65', '6d', '33', '7e', '47', '35', '7f', '37', '39', '6e', '2b', '2c', '2d', '2e', '2f', '31', '3b', '3f', '41', '3c', '3d', '3e', '42', '49', '21', '63', '64', '43', '44', '45', '23', '24', '25', '40', '4a', '66', '67', '22', '5c', '5f', '61', '5d', '5e', '69', '60', '4b', '4c', '6a', '6b', '4d', '4e', '4f', '51', '62', '68', '20', '28', '6f', '71', '74', '75', '38', '79', '6c', '29', '70', '7b', '26', '7a', '52', '76', '78', '77', '54', '55', '56', '57', '58', '53', '72', '73', '2a', '59', '50', '5a', '5b', '46', '32', '30', '3a', '36'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '2f', '31', '3b', '3f', '41', '3c', '3d', '3e', '42', '5b', '46', '32', '30', '3a', '36', '35', '7f', '37', '39', '6e', '2b', '2c', '2d', '2e', '49', '21', '63', '64', '43', '44', '45', '23', '24', '25', '40', '4a', '66', '67', '22', '5c', '5f', '61', '5d', '5e', '69', '60', '4b', '4c', '6a', '6b', '4d', '4e', '4f', '51', '62', '68', '20', '28', '6f', '71', '74', '75', '38', '79', '6c', '29', '70', '7b', '26', '73', '2a', '59', '50', '5a', '7a', '52', '76', '78', '77', '54', '55', '56', '57', '27', '7d', '65', '6d', '33', '7e', '47', '58', '53', '72', '48', '34', '7c'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '5b', '46', '32', '30', '3a', '36', '35', '7f', '37', '39', '6e', '2b', '2c', '2d', '2e', '2f', '31', '3b', '3f', '41', '3c', '3d', '3e', '42', '49', '21', '63', '64', '43', '44', '45', '23', '24', '25', '40', '4a', '66', '67', '22', '5c', '5f', '61', '5d', '5e', '69', '60', '4b', '4c', '6a', '6b', '4d', '4e', '4f', '51', '62', '68', '20', '28', '6f', '71', '74', '77', '54', '78', '56', '48', '34', '7c', '55', '75', '38', '79', '6c', '29', '70', '7b', '26', '73', '2a', '59', '50', '5a', '7a', '52', '76', '27', '7d', '65', '6d', '33', '7e', '47', '57', '58', '53', '72'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '39', '6e', '2b', '5b', '46', '32', '30', '3a', '36', '35', '7f', '37', '64', '43', '2d', '2e', '2f', '2c', '42', '49', '21', '63', '31', '3b', '3f', '41', '3c', '3d', '3e', '44', '5a', '7a', '52', '76', '27', '7d', '65', '6d', '33', '7e', '47', '57', '45', '23', '4c', '6a', '24', '25', '40', '4a', '66', '67', '22', '5c', '5f', '61', '5d', '5e', '69', '60', '4b', '6b', '7c', '55', '75', '38', '79', '6c', '29', '70', '7b', '26', '73', '2a', '59', '50', '4d', '68', '20', '28', '6f', '71', '74', '4e', '4f', '51', '62', '77', '54', '78', '56', '48', '58', '53', '72', '34'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '35', '7f', '37', '64', '43', '2d', '39', '6e', '2b', '5b', '46', '32', '30', '3a', '36', '2e', '31', '3b', '27', '7d', '65', '6d', '2f', '2c', '42', '49', '21', '63', '33', '7e', '47', '57', '45', '3f', '41', '3c', '3d', '3e', '44', '5a', '7a', '52', '76', '23', '4c', '6a', '24', '67', '22', '5c', '5f', '61', '5d', '25', '40', '4a', '66', '5e', '69', '60', '4b', '6b', '7c', '4f', '51', '62', '77', '54', '78', '56', '48', '58', '53', '72', '34', '55', '75', '38', '79', '6c', '29', '70', '7b', '26', '73', '2a', '59', '50', '4d', '68', '20', '28', '6f', '71', '74', '4e']
                ]
    hexlist = []
    for char in inp:
        hexlist.append(str(char.encode("hex")))
    addlist = []
    maxi = len(inp)
    if len(inp) < 28:
        for num in range(28 - maxi):
            if tick == maxi:
                tick = 0
                addlist.append(hexlists[num + maxi - 1][int(hexlist[tick], 16)])
            else:
                addlist.append(hexlists[num + maxi - 1][int(hexlist[tick], 16)])
            tick = tick + 1
    for hexi in addlist:
        hexlist.append(hexi)
    hexlist1 = []
    for hexdig in hexlist:
        tmp = ""
        if hexdig[1] == 0 or hexdig[1] == 1 or hexdig[1] == 8 or hexdig[1] == 9 or hexdig[1] == "a" or hexdig[1] == "b" or hexdig[1] == "c" or hexdig[1] == "d" or hexdig[1] == "e" or hexdig[1] == "f":
            tmp = hexdig[1]
            tmp = tmp + hexdig[0]
        else:
            tmp = hexdig
        hexlist1.append(tmp)
    evens = []
    odds = []
    for hexdig in hexlist1:
        evens.append(hexdig[0])
        odds.append(hexdig[1])
    odds[len(odds) - 1]
    odds1 = [odds[len(odds) - 1]]
    tick = 0
    for odd in odds:
        if tick == len(odds) - 1:
            pass
        else:
            tick = tick + 1
            odds1.append(odd)
    hexlist = []
    for tick in range(len(evens)):
        hexlist.append(evens[tick] + odds1[tick])
    outp = ""
    for hexdig in hexlist:
        outp = outp + hexdig.decode("hex")
    return outp
BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s : s[:-ord(s[len(s)-1:])]
def ping(sock):
    while True:
        sock.send("ping")
        time.sleep(1)
class AESCipher:
    def __init__( self, key ):
        self.key = key

    def encrypt( self, raw ):
        raw = pad(raw)
        iv = Random.new().read( AES.block_size )
        cipher = AES.new( self.key, AES.MODE_CBC, iv )
        return base64.b64encode( iv + cipher.encrypt( raw ) )

    def decrypt( self, enc ):
        enc = base64.b64decode(enc)
        iv = enc[:16]
        cipher = AES.new(self.key, AES.MODE_CBC, iv )
        return unpad(cipher.decrypt( enc[16:] ))
if __name__ == "__main__":
    threading.Thread(target = writeoutput,args = (q,errors)).start()
    threading.Thread(target = console,args = (q, errors, motd)).start()
    Server('', port ,q, motd, errors, mesg, quit, online, conn, c).listen()
