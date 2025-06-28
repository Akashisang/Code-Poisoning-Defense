# -*- coding: utf-8 -*-

##Copyright (C) [2003]  [Jürgen Hamel, D-32584 Löhne]

##This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as
##published by the Free Software Foundation; either version 3 of the License, or (at your option) any later version.

##This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
##warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
##for more details.

##You should have received a copy of the GNU General Public License along with this program; if not, write to the
##Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA. 

import sys,  time
from types import *
import pygtk
pygtk.require('2.0')
import gtk
import gtk.glade
import gobject
#from gtk import TRUE, FALSE
import string
import hashlib
import logging
from cuon.Windows.windows  import windows
try:
    from Crypto.Cipher import AES
except:
    print 'No Crypto-Module found -- !'
    
import cuon.User.user

class loginwindow(windows):

    
    def __init__(self, eFields, gladePath=None, Username='EMPTY', PASSWORD='Test',  ClientID = 0):

        windows.__init__(self)
        self.eUserName = eFields[0]
        self.oUser = cuon.User.user.User()
       
        self.loadGlade('login.xml', None, gladePath)
   
        self.win1 = self.getWidget('UserID_Dialog')
        
        if Username != "EMPTY":
            self.getWidget('TUserID').set_text(Username)
            self.getWidget('TPassword').set_text(PASSWORD)
            self.activateClick("okbutton1")
       
            #while response == gtk.RESPONSE_DELETE_EVENT or response == gtk.RESPONSE_CANCEL:
            #    response = win1.run()
        response = self.win1.run()
        
        while response != gtk.RESPONSE_OK:
            if response == gtk.RESPONSE_HELP:
                print "Hilfe"
            elif response == gtk.RESPONSE_CANCEL:
                print 'Cancel'
                self.oUser.setUserName('EMPTY')
                self.openDB()
                self.saveObject('User', self.oUser)
                self.closeDB()
                self.quitLogin()
                break ;
            
            
            
                
            if response == gtk.RESPONSE_OK:
                print 'ok pressed 0'
                self.okButtonPressed()
                
            
            response = win1.run()
               
            ##elif response == gtk.RESPONSE_HELP:
            ##    print "Hilfe"
                
            ##elif response == gtk.RESPONSE_DELETE_EVENT:
            ##else:
            ##print "else"
                
        #set this Functions to None
    ##    def start(self):
    ##        self.loadGlade('login.xml')
    ##   
    ##        self.win1 = self.getWidget('UserID_Dialog')
    ##        
    def loadUserInfo(self):
        pass
        
    def checkClient(self):
        pass 
             
    def on_TPassword_key_press_event(self, entry,event):
        if self.checkKey(event,'NONE','Return'):
            self.activateClick('okbutton1', event, 'clicked')
            
    def on_TUserID_key_press_event(self, entry,event):
        if self.checkKey(event,'NONE','Return'):
            self.getWidget('TPassword').grab_focus()
              
    def on_okbutton1_clicked(self, event):
        self.okButtonPressed()
        
        
    def okButtonPressed(self):
        self.quitLogin()
        print 'ok pressed 1'
        #obj = AES.new('Th77777777key456', AES.MODE_ECB)
        username = self.getWidget('TUserID').get_text()
        #self.openDB()
        #userObj = self.loadObject(username)
        #self.closeDB()
        
        #if userObj :
        #    
        #    print 'User found'
        #    self.oUser = userObj
        #else:
        #    
        self.oUser = cuon.User.user.User()
        self.oUser.setUserName(username )
        sPw = self.getWidget('TPassword').get_text()

        print 'New Auth data ( Session_id )'
        m = hashlib.sha512(sPw)
        print m.hexdigest()
        
        #print self.oUser.getUserName(), sPw
        sid = self.rpc.callRP('Database.createSessionID', self.oUser.getUserName(), m.hexdigest())
        print "Session-ID0 = ", `sid`
        if not sid:
            sid = self.rpc.callRP('Database.createSessionID', self.oUser.getUserName(), sPw)
        if sid:
            print "Session-ID1 = ", `sid`
            
            self.oUser.setSessionID(sid)
            
            self.loadProfile()
            #print 'writer'
            #print '---------------------------------------------------'
            #print self.oUser.prefDMS['exe']['writer']
            #print '---------------------------------------------------'
            
            #sys.exit(0)
            self.openDB()
            self.saveObject('User', self.oUser)
            self.closeDB()
            print 'end Login'
            print str(self.oUser)
            if self.eUserName:
                self.eUserName.set_text(self.oUser.getUserName())

        else:
            print "No correkt user and/or  password !"
            if self.oUser.getUserName() == "zope":
                self.openDB()
                self.saveObject('User', self.oUser)
                self.closeDB()
                print 'end Zope Login'
                print str(self.oUser)
            else:
                    
                self.oUser.setUserName('EMPTY')
                self.openDB()
                self.saveObject('User', self.oUser)
                self.closeDB()
        
       
    def on_cancelbutton1_clicked(self, event):
        self.oUser.setUserName('EMPTY')
        
        self.quitLogin()
    
    def quitLogin(self):
        self.win1.hide()
        #time.sleep(1)
