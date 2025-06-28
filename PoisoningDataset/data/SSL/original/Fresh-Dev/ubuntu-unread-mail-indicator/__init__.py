#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 1 2015
@author: Kevin Kleinjung
"""

import glib
import imaplib
import socket
import ssl
import gtk
import appindicator
import os
import pynotify
import setup
import ConfigParser

class IMAP4_TLS(imaplib.IMAP4_SSL): 
    def open(self, host="", port=imaplib.IMAP4_SSL_PORT): 
        self.host = host 
        self.port = port 
        self.sock = socket.create_connection((host, port)) 
        self.sslobj = ssl.wrap_socket( 
                self.sock, 
                self.keyfile, 
                self.certfile, 
                ssl_version=ssl.PROTOCOL_TLSv1, 
                ) 
        self.file = self.sslobj.makefile('rb')
    
class UnreadMailIndicator:      
    def __init__(self):
        home = os.curdir                       
        if 'HOME' in os.environ:
            home = os.environ['HOME']
        elif os.name == 'posix':
            home = os.path.expanduser("~/")
        elif os.name == 'nt':
            if 'HOMEPATH' in os.environ and 'HOMEDRIVE' in os.environ:
                home = os.environ['HOMEDRIVE'] + os.environ['HOMEPATH']
        else:
            home = os.environ['HOMEPATH']

        if os.path.isfile(home+"/.config/unread-mail-indicator/config.ini")==False:
            setup.main()
            
        self.Config = ConfigParser.ConfigParser()
        self.Config.read(home+"/.config/unread-mail-indicator/config.ini")
        print self.Config.sections()

        self.ind = appindicator.Indicator("Unread-Mail-Notify", "indicator-messages", appindicator.CATEGORY_APPLICATION_STATUS)
        self.callback_minutes = int(self.Config.get('Basics', 'CheckIntervalMinutes'))
        self.strNoUnreadMails = self.Config.get('Strings', 'strNoUnreadMails')
        self.strUnreadMails = self.Config.get('Strings', 'strUnreadMails')
        self.notificationEnabled = self.Config.get('Basics', 'ShowNotifications')
        self.notificationTitle = self.Config.get('Strings', 'notificationTitle')
        self.notificationIcon = 'indicator-messages-new'
        self.actionOnClick = "thunderbird"
        self.set_menu()   
        glib.timeout_add_seconds(int(60)*self.callback_minutes, self.work)
        
    def main(self):
            gtk.main()

    def work(self):
        self.set_menu()
        return True

    def set_menu(self):
        if(len(self.Config.get('EmailAccounts', 'EmailAccount[1][Server]'))>0):        
            self.mail_one = IMAP4_TLS(self.Config.get('EmailAccounts', 'EmailAccount[1][Server]'))
            self.mail_one.login(self.Config.get('EmailAccounts', 'EmailAccount[1][Username]'), self.Config.get('EmailAccounts', 'EmailAccount[1][Password]'))
            self.mail_one.select()
            self.mail_one_unreadcount=int(len(self.mail_one.search(None,'Unseen')[1][0].split()))
            self.mail_one.close()
            self.mail_one.logout()
        else:
            self.mail_one_unreadcount=0
        
        if(len(self.Config.get('EmailAccounts', 'EmailAccount[2][Server]'))>0):        
            self.mail_two = IMAP4_TLS(self.Config.get('EmailAccounts', 'EmailAccount[2][Server]'))
            self.mail_two.login(self.Config.get('EmailAccounts', 'EmailAccount[2][Username]'), self.Config.get('EmailAccounts', 'EmailAccount[2][Password]'))
            self.mail_two.select()
            self.mail_two_unreadcount=int(len(self.mail_two.search(None,'UnSeen')[1][0].split()))
            self.mail_two.close()
            self.mail_two.logout()
        else:
            self.mail_two_unreadcount=0
       
        if(len(self.Config.get('EmailAccounts', 'EmailAccount[3][Server]'))>0):        
            self.mail_three = IMAP4_TLS(self.Config.get('EmailAccounts', 'EmailAccount[3][Server]'))
            self.mail_three.login(self.Config.get('EmailAccounts', 'EmailAccount[3][Username]'), self.Config.get('EmailAccounts', 'EmailAccount[3][Password]'))
            self.mail_three.select()
            self.mail_three_unreadcount=int(len(self.mail_three.search(None,'UnSeen')[1][0].split()))
            self.mail_three.close()
            self.mail_three.logout()
        else:
            self.mail_three_unreadcount=0
       
        if(len(self.Config.get('EmailAccounts', 'EmailAccount[4][Server]'))>0):        
            self.mail_four = IMAP4_TLS(self.Config.get('EmailAccounts', 'EmailAccount[4][Server]'))
            self.mail_four.login(self.Config.get('EmailAccounts', 'EmailAccount[4][Username]'), self.Config.get('EmailAccounts', 'EmailAccount[4][Password]'))
            self.mail_four.select()
            self.mail_four_unreadcount=int(len(self.mail_four.search(None,'UnSeen')[1][0].split()))
            self.mail_four.close()
            self.mail_four.logout()
        else:
            self.mail_four_unreadcount=0
            
        if(len(self.Config.get('EmailAccounts', 'EmailAccount[5][Server]'))>0):        
            self.mail_five = IMAP4_TLS(self.Config.get('EmailAccounts', 'EmailAccount[5][Server]'))
            self.mail_five.login(self.Config.get('EmailAccounts', 'EmailAccount[5][Username]'), self.Config.get('EmailAccounts', 'EmailAccount[5][Password]'))
            self.mail_five.select()
            self.mail_five_unreadcount=int(len(self.mail_five.search(None,'UnSeen')[1][0].split()))
            self.mail_five.close()
            self.mail_five.logout()
        else:
            self.mail_five_unreadcount=0
        
            
      
        """
        Count all unread mails together...
        """
        self.totalUnr = int(self.mail_one_unreadcount + self.mail_two_unreadcount + self.mail_three_unreadcount + self.mail_four_unreadcount)
        
        self.ind.set_status (appindicator.STATUS_ACTIVE)
        self.ind.set_attention_icon ("indicator-messages-new")
        if(len(self.Config.get('EmailAccounts', 'EmailAccount[1][Username]'))>0):
            self.notificationText = "["+str(self.mail_one_unreadcount)+"] "+self.Config.get('EmailAccounts', 'EmailAccount[1][Label]')
        
        if(len(self.Config.get('EmailAccounts', 'EmailAccount[2][Username]'))>0):
            self.notificationText = self.notificationText+"["+str(self.mail_two_unreadcount)+"] "+self.Config.get('EmailAccounts', 'EmailAccount[2][Label]')
        
        if(len(self.Config.get('EmailAccounts', 'EmailAccount[3][Username]'))>0):
            self.notificationText = self.notificationText+"["+str(self.mail_three_unreadcount)+"] "+self.Config.get('EmailAccounts', 'EmailAccount[3][Label]')
            
        if(len(self.Config.get('EmailAccounts', 'EmailAccount[4][Username]'))>0):
            self.notificationText = self.notificationText+"["+str(self.mail_four_unreadcount)+"] "+self.Config.get('EmailAccounts', 'EmailAccount[4][Label]')
        
        if(len(self.Config.get('EmailAccounts', 'EmailAccount[5][Username]'))>0):
            self.notificationText = self.notificationText+"["+str(self.mail_five_unreadcount)+"] "+self.Config.get('EmailAccounts', 'EmailAccount[5][Label]')
            
        if self.totalUnr == 0:
            self.ind.set_icon("indicator-messages")
            self.strNoUnreadMails = self.strNoUnreadMails
            self.ind.set_label (self.strNoUnreadMails)
        else:
            self.ind.set_icon("indicator-messages-new")
            self.ind.set_label (self.strUnreadMails.replace("##unreadCount##", str(self.totalUnr)))
            if self.notificationEnabled == 1:            
                pynotify.init('Unread-Mail-Notify')
                self.notification = pynotify.Notification(self.notificationTitle,self.notificationText, self.notificationIcon)
                self.notification.show()
        
        """
        Create Menu-Element
        """        
        self.menu = gtk.Menu()
        
        """
        Create Dropdown-Elements
        """        
        if(len(self.Config.get('EmailAccounts', 'EmailAccount[1][Username]'))>0):
            self.item_a = gtk.ImageMenuItem("["+str(self.mail_one_unreadcount)+"] "+self.Config.get('EmailAccounts', 'EmailAccount[1][Label]'))
            self.item_a.connect('activate',self.on_entry_clicked)
            self.item_a.show()
            self.menu.append(self.item_a)            
        
        if(len(self.Config.get('EmailAccounts', 'EmailAccount[2][Username]'))>0):
            self.item_b = gtk.ImageMenuItem("["+str(self.mail_two_unreadcount)+"] "+self.Config.get('EmailAccounts', 'EmailAccount[2][Label]'))
            self.item_b.connect('activate',self.on_entry_clicked)
            self.item_b.show()
            self.menu.append(self.item_b)

        if(len(self.Config.get('EmailAccounts', 'EmailAccount[3][Username]'))>0):
            self.item_c = gtk.ImageMenuItem("["+str(self.mail_three_unreadcount)+"] "+self.Config.get('EmailAccounts', 'EmailAccount[3][Label]'))
            self.item_c.connect('activate',self.on_entry_clicked)
            self.item_c.show()
            self.menu.append(self.item_c)
            
        if(len(self.Config.get('EmailAccounts', 'EmailAccount[4][Username]'))>0):
            self.item_d = gtk.ImageMenuItem("["+str(self.mail_four_unreadcount)+"] "+self.Config.get('EmailAccounts', 'EmailAccount[4][Label]'))
            self.item_d.connect('activate',self.on_entry_clicked)
            self.item_d.show()
            self.menu.append(self.item_d)
        
        if(len(self.Config.get('EmailAccounts', 'EmailAccount[5][Username]'))>0):
            self.item_e = gtk.ImageMenuItem("["+str(self.mail_five_unreadcount)+"] "+self.Config.get('EmailAccounts', 'EmailAccount[5][Label]'))
            self.item_e.connect('activate',self.on_entry_clicked)
            self.item_e.show()
            self.menu.append(self.item_e)
        """
        Exit Dropdown-Entry
        """
        image = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        image.set_always_show_image(True) 
        image.connect("activate", self.quit)
        image.show()
        self.menu.append(image)                    
        self.menu.show()
        self.ind.set_menu(self.menu)

    def quit(self, widget, data=None):
        gtk.main_quit()


    def on_entry_clicked(self,widget):
        os.system(self.actionOnClick)

def main():    
    gtk.main()
    return 0

if __name__ == "__main__":
    indicator = UnreadMailIndicator()
    main()
