"""
                   .7a000BBBWBBBBB0B8Z;.                    
               :XZ80000Z7;,.   .:rXZ8B08827                 
             S0ZZ02r                  :ra0Z88X              
           aZa82;                         7aZZZS            
         SZaZ7                              .SZZZr          
       iZ2aS                 i                 SZa2:        
      2aa2.                 ,W                  ra2ar       
     a2aX                   S8:                   2SaS      
    ZS7.                    2X2                    i7SS     
   aXSXZS0WWWWWWB088BWWWW0aaXrX8aBWWWW088BWWWWWWW0S2SS27    
  ;SS2 X.         7        Xr;;X       i           7 ZXZ    
 .ZXS   Z7       XZZ      87rrrSX     7ZZ.       ;2   aXZ   
 ;SSr    ar     ra;S2     ar;;r7a    :2rXZ      :2    aXa,  
 arZ      Zr   72rrrS2   ZX;;rrrXS  :Z7rrX2    .0     i272  
 ar8       0, 8Ba222280 ,B2222222B rBa22228W: .Z       a7Z  
,SrZ        Zr:::::::,. ; ,,,:::. ;.,,::::,;i 0        S7a, 
,XXX         8         XX         a,         W         7X2: 
,X7X          W,     XZX2Z      ,aSSZ.     .Z          7X2i 
,S7Z           Zi  :2S7;rSS     Z7rrXar    Z           SXa. 
 2rZ            2 Sa7r;;;rSX  :a7r;;;7Sa  a            aXa  
 2Xa            :2X7;;rr7XSBX,WZX7;r;rrX2a            rSS7  
 i2X7          ZaX7SSZ88ZSi  7 .Xa88Z2X7rS2           a7Z.  
  8X2        0MBZar2        7a,       ;ZZ8B@2        :2X2   
  ,aS8      ;       Z      X2Xa7      7     7Z       aXZ    
   72SX              0    2S7r72r    a,             2Sai    
    222S              8  aZSXXX28X  2:             2Sa;     
     2a22             .Z;XXXX777X2 Si            ,aSZ7      
      Xa2ar             S         2,            2aaZ,       
        aaaZ.            B       a.           iaaZS         
         i8aZ2:           0     Si          rZaZa,          
           r8ZZZS         .Z   Xi        :2ZZZZi            
             ;aZZ8Za;       ; i,      7a8ZZZS,              
                iS0B0000Zar:SSX:7a8B00000X:                 
                    :XZ880B00Z80B08Za7.
"""
import pygame, os, zipfile, sys
import parameters, transition
from xml.sax import make_parser, SAXException
from xml.sax.saxutils import XMLGenerator
from xml.sax.xmlreader import AttributesImpl
from pygame.locals import *
from filemanager import filemanager
from cStringIO import StringIO
from slide import slide
from engine.SaveHandler import SaveHandler
from engine.SaveIndexHandler import SaveIndexHandler
from FilePath import FilePath
from SlideManager import SlideManager
from GLTexture import GLTexture
from OpenGL.GL import *
from OpenGL.GLU import *
    
#Current Cursor
curcursor = None
#Transition override
transoverride = None
#Pygame Module for Music and Sound
pigmusic = None
currentmusic = None
#Prefix for the current age
prefix = None

#Exit game?
quit = 0

menuslides = {}

#Object dictionaries
items = {}
objects = {}
cursors = {}
userareas = {}
timers = {}
movies = {}
musics = {}
functions = {}
images = {}
saves = {}

currentage = None

#Ordered list of userareas (needed for redraws)
userareasordered = []

#Playing Movies
playing = []

#Event Types
MOVIEEVENT = pygame.USEREVENT + 1

#Event handler functions
eventhandlers = {}

screenrect = None

#Inventory
playerinventory = None

# we need a 16, 24 or 32 bits key
key='(Ages_0f-1l@thid)&(Dn1Cham8er)01'
# construct a cryto object
try:
    from Crypto.Cipher import AES
    crypto = AES.new(key,AES.MODE_CBC)
except Exception, e:
    print "== Cannot load AES!! =="
    print e
    import traceback
    traceback.print_exc(file=sys.stdout)
    crypto = None
    
#Dictionary equating transition names to functions
transitions = {'left': transition.leftscroll, 'right': transition.rightscroll, 'down': transition.downscroll, 'up': transition.upscroll, 'fade': transition.fade, 'initfade': transition.initfade}


#Initializes all global variables and creates the drawing surfaces
def init():
    global pigmusic, screenrect
    flags = pygame.OPENGL | pygame.DOUBLEBUF
    
    #Initailize screen surface and fill with background color
    # FULLSCREEN disabled for testing, TODO enable back
    #if parameters.fullscreen:
    #    flags |= pygame.FULLSCREEN 
    
    bestdepth = pygame.display.mode_ok(parameters.screensize, flags)
    
    screenrect = pygame.Rect((0,0), (parameters.screensize[0], parameters.screensize[1]))
    
    if bestdepth == 0:
        #Exit if display can not be initialized
        sys.exit()
    
    #Create the main screen with Icon and Title
    # (except on OSX because there the better way to set icons is through the app bundle's Info.plist)
    # uname does not work on NT platform
    if os.name != 'nt':
        if os.uname()[0] != 'Darwin':
            iconbitmap = pygame.image.load('ilathid_low.gif') 
            pygame.display.set_icon(iconbitmap) 
    
    pygame.display.set_caption('Ages of Ilathid','Ilathid') 
    pygame.display.set_mode(parameters.screensize, flags)
    
    # Init OpenGL
    prepare2DViewport()
    glDisable(GL_DEPTH_TEST)  # no Z buffer
    glEnable(GL_TEXTURE_2D)
    glEnable(GL_COLOR_MATERIAL)
    glEnable(GL_BLEND) # enable transparency
    glClearColor(0,0,0,1)
    glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA) # normal transparency with alpha channel



#Function to load an image from a file. Can load plain, encrypted, zipped, and encrypted/zipped images
# fileref : an instance of FilePath
# isSlide : by default, will look under the slides folder. Set to false to look under images folder.
def loadimage(fileref, isSlide = True):
    
    # I know usually in Python you don't verify types but this will help detect problems during the current refactor.
    if not isinstance(fileref, FilePath):
        raise Exception("fileref must be a FilePath object")
    
    try:
        #Tmpsurface to hold loaded image
        tmpsurface = None
        #If uncompressed
        if fileref.getArchiveName() == None:
            
            if fileref.arePathsAbsolute():
                filepath = fileref.getFileName()
            elif isSlide:
                filepath = filemanager.find_slide(fileref.getFileName())
            else:
                filepath = filemanager.find_image(fileref.getFileName())
            
            if fileref.getEncryption() == 0:
                #if not encrypted, load the image and return it
                tmpsurface = GLTexture(filepath)
            else:
                #If encrypted, decrypt it, and load it
                # FIXME: in new versions of Python, data should NOT be stored in a string
                tmpfile = file(filepath,'rb')
                data = tmpfile.read()
                data2=crypto.decrypt(data)
                data_io = StringIO(data2)
                tmpsurface = GLTexture(data_io, fileref.getFileName())
        else:
            #If compressed load the file from the zipfile
            
            if fileref.arePathsAbsolute():
                filepath = fileref.getArchiveName()
            elif isSlide:
                filepath = filemanager.find_slide(fileref.getArchiveName())
            else:
                filepath = filemanager.find_image(fileref.getArchiveName())
                
            data = zipfile.ZipFile(filepath).read(fileref.getFileName())
            if fileref.getEncryption() == 0:
                #if not encrypted, read image into string
                data_io = StringIO(data)
            else:
                #If encrypted, decrypt it, read image into string
                # FIXME: in new versions of python, data should NOT be stored in a string
                data2=crypto.decrypt(data)
                data_io = StringIO(data2)
            #Create image from data
            tmpsurface = GLTexture(data_io, fileref.getFileName())
        #return the image
        return tmpsurface
    except:
        print "Error while loading image <%s>!" % fileref.getFileName()
        raise

#Function to load an font from a file. Can load plain, encrypted, zipped, and encrypted/zipped fonts
def loadfont(fileref, size):
    if fileref.getArchiveName() is None:
        #If uncompressed
        if fileref.getEncryption() == 0:
            #if not encrypted, load the font and return it
            return pygame.font.Font(os.path.join(parameters.gettextpath(), fileref.getFileName()), size)
        else:
            #If encrypted, decrypt it, then return the font
            tmpfile = file(os.path.join(parameters.gettextpath(), fileref.getFileName()),'rb')
            data = tmpfile.read()
            data2=crypto.decrypt(data)
            #data2 = rotor.newrotor(parameters.encryption_key,parameters.encryption_rounds).decrypt(data)
            data_io = StringIO(data2)
            return pygame.font.Font(data_io, size)
    else:
        #If compressed load the file from the zipfile
        data = zipfile.ZipFile(os.path.join(parameters.gettextpath(), fileref.getArchiveName())).read(fileref.getFileName())
        if fileref.getEncryption() == 0:
            #if not encrypted, load the font and return it
            data_io = StringIO(data)
            return pygame.font.Font(data_io, size)
        else:
            #If encrypted, decrypt it, then return the font
            data2=crypto.decrypt(data)
            #data2 = rotor.newrotor(parameters.encryption_key,parameters.encryption_rounds).decrypt(data)
            data_io = StringIO(data2)
            return pygame.font.Font(data_io, size)

#Returns true if the passed slide is displayed on the screen
def isslidevisible(slide):
    if slide == None:
        #If the slide is none, of course it is not displayed. Return 0
        return 0
    current_slide = SlideManager.getCurrentSlide()
    if current_slide == slide and slide.isvisible():
        #If the slide is the current slide, current UI slide and that slide is visible, return 1
        return 1
    else:
        #otherwise return 0
        return 0


#Calls the proper transition for slide to slide changes
def dotrans(slide, oldslide):
    global transoverride
    if parameters.gettransquality() == 'None':
        #If transitions set to None, nothing to do
        return
    elif transoverride == None:
        #If no transition has been specified by the game 
        if slide._currenttrans != 'none':
            #If the slide has a transition type, use it
            transitions[slide._currenttrans](slide, oldslide)
    else:
        #A transition has been specified by the game, so use it
        transitions[transoverride](slide, oldslide)
        #Then clear the transition override
        transoverride = None

#Hides, changes, and displays the mouse cursor
def changecursor(newcursor):
    global curcursor
    if curcursor.isenabled():
        #If enable, check if visible
        cursorstate = curcursor.isvisible()
        if cursorstate:
            #Hide if visible
            curcursor._hide()
        #Set to the new cursor
        curcursor = newcursor
        if cursorstate:
            #Show if needed
            curcursor._show()
    else:
        #Not enable, so just change it
        curcursor = newcursor


def stopallsound():
    if pygame.mixer:
        pygame.mixer.stop()
    
def loadGame(saveName):
    """ This function load an xml Save File and starts it"""
    try:
        save = file(os.path.join(parameters.getsavepath(), saveName),'rb')
    except IOError, detail: 
        print "IOError detail=",detail
        sys.exit()
    handler = SaveHandler()
    parser = make_parser()
    parser.setContentHandler(handler)
    try:
        parser.parse(save)
    except SAXException,detail:
        print "SAXEception detail=",detail
        sys.exit()
        
    return (handler.slide_obj, handler.music)

def loadSaveIndex(saveIndexFile):
    try:
        saveIndex = file(os.path.join(parameters.getsavepath(), saveIndexFile),'rb')
        handler = SaveIndexHandler()
        parser = make_parser()
        parser.setContentHandler(handler)
        parser.parse(saveIndex)
    except:
        print "An error occurred while loading save data. Will discard save data!"
        print sys.exc_info()
        import traceback
        traceback.print_tb(sys.exc_info()[2])


def saveSaveIndex(saveIndexFile):
    global saves
    f = file(os.path.join(parameters.getsavepath(), saveIndexFile),'w')
    #print 'saved slide ',slide._save(slide._currentslide)
    hd = XMLGenerator(f) # handler's creation
    
    hd.startDocument()
    hd.startElement("SaveIndex", AttributesImpl({}))
    for (key, value) in saves.items():
        attributes = {"age": value.getage(),
                      "image": value.getimage()[0],
                      "date": value.getdate()}
        if value.getimage()[1] is not None:
            attributes["image_archive"] = value.getimage()[1]
        if value.getimage()[2] is not None:
            attributes["image_encryption"] = str(value.getimage()[2])
        hd.startElement("save", AttributesImpl(attributes))
        hd.characters(key)
        hd.endElement("save")
    hd.endElement("SaveIndex")
    hd.endDocument()
    f.close()

def prepare2DViewport():
    width = parameters.getscreensize()[0]
    height = parameters.getscreensize()[1]
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, width, height, 0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

def prepare3DViewport():
    width = parameters.getscreensize()[0]
    height = parameters.getscreensize()[1]
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(50.0, float(width)/float(height), 0.1, 500.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    