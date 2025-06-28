import kivy
kivy.require('1.9.1')
from kivy.app import App
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.factory import Factory
from kivy.properties import ObjectProperty
from kivy.properties import StringProperty
from kivy.properties import NumericProperty
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
from kivy.graphics import *
import os
from os.path import sep, expanduser, isdir, dirname
import hashlib as h
from Crypto.Cipher import AES
from Crypto import Random
import random
import struct
import base64
import binascii
import glob
import time
import getpass
import tarfile


Window.clearcolor = (1, 1, 1, 1)
Window.minimum_height = 800
Window.minimum_width = 700

Clock.max_iteration = 9001

Builder.load_file('gui.kv')

class Start(Screen):
    pass

#Doesn't work, will fix later
#class DropFile(Popup):
#    def build(self):
#        Window.bind(on_dropfile=self._on_file_drop)
#        return

#    def _on_file_drop(self, window, file_path):
#        if self.collide_point(*Window.mouse_pos):
#            filepath = file_path.decode('utf-8')
#        return filepath
#    def handledrops(self, *args):
        # this will execute each function from list with arguments from
        # Window.on_dropfile
        #
        # make sure `Window.on_dropfile` works on your system first,
        # otherwise the example won't work at all
#        for func in self.drops:
#            func(*args)
#    def __init__(self, **kwargs):
#        super(DropFile, self).__init__(**kwargs)
#
        # get app instance to add function from widget
        #app = App.get_running_app()
#
        # add function to the list
#        self.drops = []
#        Window.bind(on_dropfile=self.handledrops)
#        self.drops.append(self.on_dropfile)
#

#    def on_dropfile(self, widget, filename):
        # a function catching a dropped file
        # if it's dropped in the widget's area
#        if self.collide_point(*Window.mouse_pos):
            # on_dropfile's filename is bytes (py3)
#            file_path = filename.decode('utf-8')
#        return file_path


class Browse(BoxLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)

class EnPopup(Popup):
    i = 0
    def memor(self):
        global i
        for i in range(0,100):
            i += 1
        if i == 100:
            self.dismiss()

class EnErrorPopup(Popup):
    pass
class EnSuccessPopup(Popup):
    global labeltext
    def reset_var(self):
        labeltext = "No files selected"


class Encryption(Screen):
    enpopup = ObjectProperty(EnPopup())
    enerrorpopup = ObjectProperty(EnErrorPopup())
    ensuccesspopup = ObjectProperty(EnSuccessPopup())

    filee = "No files selected"
    namespath = "No path"
    datapath = "No path"
    labeltext = StringProperty("No files selected")


    loadfile = ObjectProperty(None)
    savefile = ObjectProperty(None)
    label = ObjectProperty(None)
    thepath = []

    def update(self):
        self.labeltext = thepath[1]

    def reset_var(self):
        self.labeltext = "No files selected"

    def dismiss_popup(self):
        self._popup.dismiss()

    def show_load(self):
        content = Browse(load=self.load, cancel=self.dismiss_popup)
        self._popup = Popup(title="Load file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def load(self, path, filename, namesname="data"):
        global filee
        global namespath
        global datapath
        global thepath
        filee = os.path.join(path, filename[0])
        thepath = os.path.split(filee)
        namespath = os.path.join(thepath[0], 'names.txt')
        datapath = os.path.join(thepath[0], namesname)
        self.update()
        self.dismiss_popup()

    def fpath(self):
        return filee

    def names(self):
        return namespath

    def pack(filepath, name):
        tar = tarfile.open("myArchive.tar", "w")
        tar.add(filepath, arcname=name)
        tar.close()

    def encrypt(self, key, filename, ofilename, chunksize=16):
        global namespath
        global datapath
        #global prog
        global thepath
        hashed = h.sha256()
        hashed.update(('salted bacon').encode('utf-8'))
        hashed.update((key).encode('utf-8'))
        key = (hashed.digest())
        if (filename.endswith('names.txt')):
                ofilename = datapath
        else:
            ofilename = os.path.join(thepath[0], ofilename)
            with open(namespath, 'a') as namefile:
                namefile.write('right')
                namefile.write(filename)
                namefile.write('\n')
        #iv = ''.join(chr(random.randint(0, 9)) for i in range(16))
        iv = str(random.randint(1000000000000000, 9999999999999999))
        iv = str.encode(iv)
        encrypter = AES.new(key, AES.MODE_CBC, iv)
        filesize = os.path.getsize(filename)
        ofilename += '.enc'
        with open(filename, 'rb') as ifile:
            with open(ofilename, 'ab') as ofile:

                ofile.write(struct.pack('<Q', filesize))
                ofile.write(iv)
                while True:
                    chunk = base64.b64encode(ifile.read(chunksize))
                    chunk = chunk.decode("utf-8")
                    if len(chunk) == 0:
                        break
                    elif len(chunk) % 16 != 0:
                        chunk += ' ' * (16 - len(chunk) % 16)

                    ofile.write(encrypter.encrypt(chunk))

    def encryption(self, key):
        global enerrorpopup
        global ensuccesspopup
        self.encrypt(key, self.fpath(), "1")
        self.encrypt(key, self.names(), "1")
        try:
            os.remove(self.names())
        except OSError as e: # name the Exception `e`
            print ("Failed with:" + e.strerror)
            print ("Error code:" + e.code)
            self.enerrorpopup.open()
        self.ensuccesspopup.open()
        self.manager.current = 'start'


class DePopup(Popup):
    i = 0
    def memor(self):
        global i
        for i in range(0,100):
            i += 1
        if i == 100:
            self.dismiss()

class DeErrorPopup(Popup):
    pass
class DeSuccessPopup(Popup):
    global labeltext
    def reset_var(self):
        self.labeltext = "No files selected"

class DeDataPopup(Popup):
    global labeltext
    def reset_var(self):
        self.labeltext = "No files selected"

class Decryption(Screen):
    depopup = ObjectProperty(DePopup())
    deerrorpopup = ObjectProperty(DeErrorPopup())
    desuccesspopup = ObjectProperty(DeSuccessPopup())
    dedatapopup = ObjectProperty(DeDataPopup())

    filee = "No files selected"
    namespath = "No path"
    datapath = "No path"
    labeltext = StringProperty("No files selected")


    loadfile = ObjectProperty(None)
    savefile = ObjectProperty(None)
    text_input = ObjectProperty(None)

    def update(self):
        self.labeltext = thepath[1]

    def reset_var(self):
        self.labeltext = "No files selected"

    def dismiss_popup(self):
        self._popup.dismiss()

    def show_save(self):
        content = Export(load=self.load, cancel=self.dismiss_popup)
        self._popup = Popup(title="Load file", content=content,
                                size_hint=(0.9, 0.9))
        self._popup.open()

    def load(self, path, filename, namesname="data"):
        global filee
        global namespath
        global datapath
        global thepath
        filee = os.path.join(path, filename[0])
        thepath = os.path.split(filee)
        namespath = os.path.join(thepath[0], 'names.txt')
        datapath = os.path.join(thepath[0], namesname)
        self.update()
        self.dismiss_popup()

    def fpath(self):
        return filee

    def names(self):
        return namespath

    def decrypt(self, key, ifilename, ofilename, chunksize=16):
        chunksize = 16
        hashed = h.sha256()
        hashed.update(('salted bacon').encode('utf-8'))
        hashed.update((key).encode('utf-8'))
        key = (hashed.digest())
        origname = ofilename
        filename = str(ifilename)
        with open(filename, 'rb') as ifile:
            origsize = struct.unpack('<Q', ifile.read(struct.calcsize('<Q')))[0]-16
            chunksize = 16
            iv = ifile.read(16)


            decrypter = AES.new(key, AES.MODE_CBC, iv)
            with open(ofilename, 'ab') as ofile:
                while True:
                    chunk = 0

                    chunk = ifile.read(chunksize)
                    if len(chunk) == 0:
                        break
                    try:
                        ofile.write(base64.decodestring(decrypter.decrypt(chunk)))
                    except:
                        print("nyt ei toiminut")

    def decryption(self, key):
        global thepath
        if self.fpath().endswith('data.enc'):
            self.dedatapopup.open()
            return

        try:
            self.decrypt(key, os.path.join(thepath[0], "data.enc"), "names.txt")
            with open('names.txt', 'r') as namefile:
                try:
                    lines = namefile.readlines()
                except:
                    print('Wrong password')
                    self.deerrorpopup.open()
                    return
                try:
                    if not lines[0].startswith('right'):
                        print('Wrong password')
                        return
                    origname = lines[0][:-1][5:]
                except:
                    pass

            self.decrypt(key, self.fpath(), origname)
            try:
                os.remove(self.fpath())
            except OSError as e: # name the Exception `e`
                print ("Failed with:" + e.strerror) # look what it says
                print ("Error code:" + e.code)
                self.deerrorpopup.open()

            try:
                os.remove(os.path.join(thepath[0], "data.enc"))
            except OSError as e: # name the Exception `e`
                print ("Failed with:" + e.strerror) # look what it says
                print ("Error code:" + e.code)
                self.deerrorpopup.open()
        except OSError as e:

            print(e)
        self.desuccesspopup.open()
        self.manager.current = 'start'

class Export(Screen):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)

sm = ScreenManager(transition=NoTransition())
sm.add_widget(Start(name='start'))
sm.add_widget(Encryption(name='encryption'))
sm.add_widget(Decryption(name='decryption'))
sm.add_widget(Export(name='export'))

class DailyCryptApp(App):
    icon = 'resources/images/logo.ico'
    def build(self):
        return sm

Factory.register('Browse', cls=Browse)

if __name__ == '__main__':
    DailyCryptApp().run()
