#!/usr/bin/env python

import sys, platform
from Tkinter import *
import tkFont, tkMessageBox
from tkFileDialog import askopenfilename

### imports for connections
import socket,ssl,base64, RSAKeyHandling, os, json
from M2Crypto import DH,RSA,Rand
from binascii import hexlify
import pickle
from base64 import b64decode

#==============================================================
# define global variables

# define window parameters
WINDOW_WIDTH_MS = 500
WINDOW_HEIGHT_MS = 100

WINDOW_WIDTH_ES = 600

WINDOW_WIDTH_AUTH = 650
WINDOW_HEIGHT_AUTH = 500

WINDOW_WIDTH_MAIN = 760
WINDOW_HEIGHT_MAIN = 500


# authentication parameters
privateKeyFile = None
privateRSAKey = None

voterPIN = None
maxPINLength = 4

voterID = None
voterIDLength = 10

# possibleSelectionValues = (u"\u03B1", u"\u03B2", u"\u03B3", u"\u03B4", u"\u03B5") # alpha, beta, gamma, delta, epsilon
possibleSelectionValues = ("Alpha", "Beta", "Gamma", "Delta", "Epsilon") # alpha, beta, gamma, delta, epsilon
userVote = []
#==============================================================



#==============================================================
# define a stack to hold checkbutton and radiobutton widgets
#==============================================================

class Stack:
    def __init__(self):
        self.items = []
    
    def push(self, item):
        self.items.append(item)
        
    def pop(self):
        return self.items(pop())
        
    def length(self):
        return len(self.items)
        
    def hasElement(self, element):
        return (element in self.items)
    
    def getElement(self, index):
        return self.items[index]
    
    def deleteFirst(self):
        _r = self.items[0]
        del self.items[0]
        return _r
        
    def deleteElement(self, element):
        if self.hasElement(element):
            self.items.remove(element)
            
    def showStack(self):
        for i in range(0, len(self.items)):
            print "Element %d: %d" % (i, self.items[i])

#==============================================================



#==============================================================
# define class MainScreen

class MainScreen(Tk):
    
    def createWidgets(self):
        # create heading
        myriadHeadingFont = tkFont.Font(family="Myriad Pro",size=28)
        self.noteLabel = Label(self, 
                                text = "Press start to begin your voting session.",
                                font = myriadHeadingFont)
        
        x = (WINDOW_WIDTH_MS - self.noteLabel.winfo_reqwidth())/2
        self.noteLabel.place(x = (WINDOW_WIDTH_MS - self.noteLabel.winfo_reqwidth())/2, y = 10)
        
        def startVoting():
            # print "Authenticate --->"
            self.destroy()
        
        #create button to go next
        self.startButton = Button(self, text = "Start", command = startVoting)
        self.startButton.place(x = (WINDOW_WIDTH_MS - self.startButton.winfo_reqwidth())/2, y = 55)
        
    def __init__(self, master=None):
        Tk.__init__(self)
        self.createWidgets()
        
#==============================================================


class EndScreen(Tk):
    
    def createWidgets(self):
        # create heading
        myriadHeadingFont = tkFont.Font(family="Myriad Pro",size=28)
        self.noteLabel = Label(self, 
                                text = "Thank you for voting. Now please move on!",
                                font = myriadHeadingFont)
        
        x = (WINDOW_WIDTH_ES - self.noteLabel.winfo_reqwidth())/2
        self.noteLabel.place(x = (WINDOW_WIDTH_ES - self.noteLabel.winfo_reqwidth())/2, y = 10)
        
        def endVoting():
            sys.exit()
        
        #create button to go next
        self.doneButton = Button(self, text = "Done", command = endVoting)
        self.doneButton.place(x = (WINDOW_WIDTH_ES - self.doneButton.winfo_reqwidth())/2, y = 55)
        
    def __init__(self, master=None):
        Tk.__init__(self)
        self.createWidgets()
        
#==============================================================

#==============================================================
# define class AuthScreen

class AuthScreen(Tk):
        
    def createWidgets(self):
        #fonts_here
        myriadHeadingFont = tkFont.Font(family = "Myriad Pro",size = 60)
        myriadRequestFont = tkFont.Font(family = "Myriad Pro",size = 24)
        myriadInputFont = tkFont.Font(family = "Myriad Pro", size = 16)
        myriadFileFont = tkFont.Font(family = "Myriad Pro",size = 14)
        
        #create heading
        self.noteLabel = Label(self, text = "Login to Vote", font = myriadHeadingFont)
        self.noteLabel.place(x = (WINDOW_WIDTH_AUTH - self.noteLabel.winfo_reqwidth())/2, y = 20)
        
        #create label and input for VoterID
        self.voterIDLabel = Label(self, text = "Enter your VoterID:", font = myriadRequestFont)
        self.voterIDEntryInput = Entry(self, width = 20)
        
        #create label and input for private key
        fileStatusVar = StringVar()
        fileStatusVar.set("No file selected")
        
        self.qKeyLabel = Label(self, text = "Enter private key file", font = myriadRequestFont)
        self.keyButton = Button(self, text = "Open private key file", width = 16, 
                            command = lambda i=fileStatusVar: self.getPrivateKeyFile(i))
        self.keyFileLabel = Label(self, textvariable = fileStatusVar, font = myriadFileFont)
        
        # self.privateKeyFile = askopenfilename(initialdir = './privatekeys', filetypes=(("Certificate", "*.pem"),))
        
        #create label and input for PIN
        self.PINLabel = Label(self, text = "Enter your passcode:", font = myriadRequestFont)

        limitCheck = StringVar() #limit to number of characters in the PIN field
        
        def _on_write(*args):
            s = limitCheck.get()
            if len(s) > maxPINLength:
                limitCheck.set(s[:maxPINLength])
        
        limitCheck.trace_variable("w", _on_write)
        self.PINInput = Entry(self, width = 20, textvariable = limitCheck)
        self.PINInput.config(show = "*")
        
        # placing
        _sp = 100
        _spAlign = _sp - 2
        self.voterIDLabel.place(x = _spAlign, y = 120)
        self.voterIDEntryInput.place(x = _sp, y = 160)
        
        self.qKeyLabel.place(x = _spAlign, y = 220)
        self.keyButton.place(x = _sp, y = 260)
        self.keyFileLabel.place(x = _sp + self.keyButton.winfo_reqwidth() + 20, y = 260 + 3)
        
        _y = 260 + 50
        self.PINLabel.place(x = _spAlign, y = _y)
        self.PINInput.place(x = _sp, y = _y + 50)
        
        #create button to toggle visibility
        self.showPIN = Button(self, text = "Toggle PIN", command = self.togglePINVisibility)
        self.showPIN.place(x = _sp + self.PINInput.winfo_reqwidth() + 10, y = _y + 50)
        
        #create button for login
        self.loginButton  = Button(self, text = "Login", width = 5, command = self.login)
        self.loginButton.place(x = _sp, y = _y + 90)
        
        #create button to quit program
        self.quitButton  = Button(self, text = "Exit", width = 5, command = self.exitProgram)
        self.quitButton.place(x = _sp + self.loginButton.winfo_reqwidth() + 5, y = _y + 90)
        
        
    def __init__(self, master=None):
        Tk.__init__(self)
        self.createWidgets()


    def getPrivateKeyFile(self, var):
        global privateKeyFile
        privateKeyFile = askopenfilename(initialdir = './privatekeys', filetypes=(("Private key", "*.pem"),))
        if privateKeyFile != "":
            var.set("Private key file selected")
        else:
            var.set("Click button to select file")
        
        
    def togglePINVisibility(self):
        if self.PINInput['show'] == "":
            self.PINInput.config(show = "*") # hide PIN
        else:
            self.PINInput.config(show = "") # show PIN
    
    def check(self):
        # check for RSA key, voterID, PIN value here
        if len(self.voterIDEntryInput.get()) != voterIDLength:
            tkMessageBox.showwarning(title = "Login",
                                    message = "Please enter a valid voterID.\nVoterID must be %d characters long." % (voterIDLength))
            return False
        
        if privateKeyFile == "" or privateKeyFile == None:
            tkMessageBox.showwarning(title = "Login",
                                    message = "Please select a valid private key file")
            return False
                    
        if len(self.PINInput.get()) != maxPINLength:
            tkMessageBox.showwarning(title = "Login", 
                                    message = "Length of Passcode is not %d characters." % (maxPINLength))
            return False
    
    def login(self):
        if (self.check() == False): # check if values are appropriate
            return
        
        global voterID, privateRSAKey, voterPIN
        
        voterID = self.voterIDEntryInput.get()        
        privateRSAKey = privateKeyFile
        voterPIN = self.PINInput.get()
        
        self.destroy()
        
    def exitProgram(self):
        sys.exit()

#==============================================================










#==============================================================
# define class ChoiceScreen

class Group(Tk):
    '''This is the docline'''
    voteFor = "" # voteFor = "president"|"congress"|"counsel"
    MAX_SELECTIONS = 0
    MAX_OPTIONS = 0
    selection = ()
    
    def createWidgets(self, _vf, _ms, _mo):
        # get constructor variables
        voteFor = _vf
        MAX_SELECTIONS = _ms
        MAX_OPTIONS = _mo
        
        
        myriadHeadingFont = None
        atypeOptionFont = None
        optionSelectedFont = None
        
        if platform.system() == 'Darwin':
            myriadHeadingFont = tkFont.Font(family = "Myriad Pro",size = 60)
            atypeOptionFont = tkFont.Font(family = "Calibri", size = 30)
            optionSelectedFont = tkFont.Font(family = "Calibri", size = 30, slant = "italic", weight = "bold")
        elif platform.system() == 'Windows':
            myriadHeadingFont = tkFont.Font(family = "Helvetica",size = 60)
            atypeOptionFont = tkFont.Font(family = "Helvetica", size = 20)
            optionSelectedFont = tkFont.Font(family = "Helvetica", size = 20, slant = "italic", weight = "bold")
        elif platform.system() == 'Linux':
            myriadHeadingFont = tkFont.Font(family = "Helvetica",size = 60)
            atypeOptionFont = tkFont.Font(family = "Helvetica", size = 20)
            optionSelectedFont = tkFont.Font(family = "Helvetica", size = 20, slant = "italic", weight = "bold")
                        
        # myriadHeadingFont = tkFont.Font(family = "Myriad Pro",size = 60)
        # atypeOptionFont = tkFont.Font(family = "Calibri", size = 175)
        # optionSelectedFont = tkFont.Font(family = "Calibri", size = 175, slant = "italic", weight = "bold")
                
        # create heading
        self.noteLabel = Label(self, 
                            text = "Select Your %s" % (voteFor), 
                            font = myriadHeadingFont)
        
        x = (WINDOW_WIDTH_MAIN - self.noteLabel.winfo_reqwidth())/2
        self.noteLabel.place(x = (WINDOW_WIDTH_MAIN - self.noteLabel.winfo_reqwidth())/2, y = 20)
        
        # create presidents ------------- OLD ALGORITHM | #sigmatag = 0
        # self.presidents = [0]*maxPresidents
        # presidentLabelTexts = (u"\u03B1", u"\u03B2", u"\u03B3") #alpha, beta, gamma --- greek small
        
        # for i in range(0, len(presidentLabelTexts)):
        #     self.presidents[i] = Label(self, text = presidentLabelTexts[i], font = at175)
        #     _x = WINDOW_WIDTH_MAIN/4*(i+1) - self.presidents[i].winfo_reqwidth()/2
        #     self.presidents[i].place(x = _x, y=125)
        #     if i == 2:
        #         self.presidents[i].place(x = _x, y=108)
        
        # setup radio/checkbutton list and stack
        self.options = [0]*MAX_OPTIONS
        valueLabels = possibleSelectionValues[0:MAX_OPTIONS]
        s = Stack()
        
        # create variables for checkbuttons and radiobuttons
        varList = [0]*MAX_OPTIONS
        for i in range(0, len(varList)):
            varList[i] = IntVar()
        radioVar = IntVar()
        
        
        # Algorithm selectionRadio: #sigmatag = 1
        #     value = which radiobutton
        #     if element in stack:
        #         return
        #     
        #     Radiobutton[value].font = boldized_font
        #     stack.push(value)
        #     if length(stack) > 1:
        #         Radiobutton[0].font = original_font
        def selectionRadio():
            index = radioVar.get() - 1
            if s.hasElement(index):
                return
            
            self.options[index]['font'] = optionSelectedFont
            s.push(index)
            if s.length() > 1:
                self.options[s.deleteFirst()]['font'] = atypeOptionFont
        


        # Algorithm selectionCheck: #sigmatag = 1
        #     value = checked or unchecked
        #     if value is checked:
        #         Checkbutton[index].font = boldized_font
        #         stack.push(index)
        #     else:
        #         Checkbutton[index].font = original_font
        #         stack.delete(index) //delete by value
        #         
        #     if length(stack) > MAX_SELECTIONS:
        #         stack.delete(0) //delete by index
        #         Checkbutton[index].font = original_font
        #         Checkbutton[index].deselect()
        def selectionCheck(index):
            value = varList[index].get()
            if value == 1:
                self.options[index]['font'] = optionSelectedFont
                s.push(index)
            else:
                self.options[index]['font'] = atypeOptionFont
                s.deleteElement(index)
            
            if s.length() > MAX_SELECTIONS:
                _first = s.deleteFirst()
                self.options[_first]['font'] = atypeOptionFont
                self.options[_first].deselect()
        
        
        def underVote():
            value = tkMessageBox.askquestion(title = "What?",
                                            message = "You haven't voted properly. Do you want to move to the next section?")
            if value == "yes":
                return True
            else:
                return False
        
        def confirmSelection():
            global userVote
            
            # if s.length != 0:
            #     tkMessageBox.showwarning(title = "Incomplete Vote",
            #                             message = "You have not voted "
            # if s.length != MAX_SELECTIONS:
            #     tkMessageBox.showwarning(title = "Incomplete Vote",
            #                             message = "You've chosen only" % (voterIDLength))
            
            underVoteOK = "OK"
            if s.length() < MAX_SELECTIONS:
                underVoteOK = underVote()
            
            if underVoteOK == False:
                return
            
            for index in range(0, s.length()):
                userVote.append(s.getElement(index))
                
            self.destroy()
            return
        
        def skipSection():
            value = tkMessageBox.askquestion(title = "What?",
                                            message = "Do you really want to skip?")
            if value == 'yes':
                self.destroy()            
            
            

        # create options list for display in GUI
        for index in range(0, MAX_OPTIONS):
            if MAX_SELECTIONS > 1:
                self.options[index] = Checkbutton(self, text = valueLabels[index], anchor = W, font = atypeOptionFont,
                                                variable = varList[index], command = lambda i=index: selectionCheck(i))
            else:
                self.options[index] = Radiobutton(self, text = valueLabels[index], anchor = W, font = atypeOptionFont,
                                            variable = radioVar, value = index+1, command = selectionRadio)

            _x = WINDOW_WIDTH_MAIN/(MAX_OPTIONS+1)*(index+1) - self.options[index].winfo_reqwidth()/2
            self.options[index].place(x = _x, y=150)
        
        # add skip button                
        self.skipButton = Button(self, text = "Skip", width = "7", command = skipSection)
        self.skipButton.place(x = WINDOW_WIDTH_MAIN/2 - self.skipButton.winfo_reqwidth(), y = WINDOW_HEIGHT_MAIN - 60)
            
        # add confirm button
        self.confirmButton = Button(self, text = "Confirm", width = "7", command = confirmSelection)
        self.confirmButton.place(x = WINDOW_WIDTH_MAIN/2, y = WINDOW_HEIGHT_MAIN - 60)
            
        #create button to quit program
        self.quitButton  = Button(self, text = "Exit", width = 5, command = self.exitProgram)
        self.quitButton.place(x = WINDOW_WIDTH_MAIN - 10 - self.quitButton.winfo_reqwidth(), 
                            y = WINDOW_HEIGHT_MAIN - 10 - self.quitButton.winfo_reqheight())
            
                
    def __init__(self, _vf, _ms, _mo, master=None):
        Tk.__init__(self)
        self.createWidgets(_vf, _ms, _mo)
        
    def exitProgram(self):
        sys.exit()

#==============================================================





#==============================================================

def centerWindow(window, _width, _height):
    # get screen attributes
    screenWidth = window.winfo_screenwidth()
    screenHeight = window.winfo_screenheight()
    
    #get coordinates
    x = screenWidth/2 - _width/2
    y = screenHeight/2 - _height/2
    window.geometry('%dx%d+%d+%d' % (_width, _height, x, y))
    window.resizable(0,0)


def main():
    
    # seeding the PRNG with 1024 random bytes from OS
    # from M2Crypto
    Rand.rand_seed (os.urandom (1024))

    while 1:
        
    #======================================================
        # draw MAIN SCREEN
        mainScreen = MainScreen()
        centerWindow(mainScreen, WINDOW_WIDTH_MS, WINDOW_HEIGHT_MS)
        mainScreen.mainloop()
    
    #======================================================
        ### begin connecting to the srver
        
        # buffer length
        buffer_length = 5000
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
        # require a certificate from the server
    
        myhost = 'localhost'
        myport = 4321
    
        try:
            
            # ssl.CERT_NONE : cause we are using a self signed certificate
            ssl_sock = ssl.wrap_socket(s,cert_reqs=ssl.CERT_NONE,ssl_version=ssl.PROTOCOL_TLSv1)
            ssl_sock.connect((myhost, myport))
        
            #print repr(ssl_sock.getpeername())
            #print ssl_sock.cipher()
    
            #begin to receive DH key exchange data from server
            #in order of p,g,g^a
    
            serverDH_p   = base64.b64decode(ssl_sock.read(buffer_length))
            serverDH_g   = base64.b64decode(ssl_sock.read(buffer_length))
            serverDH_pub = base64.b64decode(ssl_sock.read(buffer_length))
            
            myDHobject = DH.set_params(serverDH_p, serverDH_g)
            
            # pick random p and generate g^b in myDhobject.pub
            myDHobject.gen_key()
            
            ssl_sock.sendall(base64.b64encode(myDHobject.pub))
            
            # generate shared AES Key
            sharedAESkey = myDHobject.compute_key(serverDH_pub)
            
            # print 'shared AES Key ', hexlify(sharedAESkey)
    
            # now we have a secure shared 256-bit AES key to send data around
            # it was Diffie Hellman, so even if TLS was borked, hopefully noone knows it
            
        except:
            #ZZZ change to msgbox
            tkMessageBox.showwarning(title = "Connection Error",
                                    message = "Cannot connect to server.")
            ssl_sock.close()
            # mainScreen.destroy()
            # print 'Cannot connect to server', myhost , ':' , myport
            continue
    
        
    #======================================================    
        # draw AUTHENTICATION SCREEN
        authScreen = AuthScreen()
        centerWindow(authScreen, WINDOW_WIDTH_AUTH, WINDOW_HEIGHT_AUTH)
        authScreen.mainloop()
        
        # voterID, privateRSAKey and PIN are valid
        
    #======================================================     
        
        # start validating login
        
        # get the chosen IV in base64
        chosen_IV_inbase64 = ssl_sock.read(buffer_length)
        
        # decode it from base64
        chosen_IV = b64decode(chosen_IV_inbase64)
        
        # print 'got chosen_IV ', hexlify(chosen_IV)
        
        # voterID || PIN 
        voterID_PIN = voterID + voterPIN
        
        # print 'voterID_PIN ', str(voterID_PIN)
        
        # calculate sha256 hash of voterID || PIN in base64
        hash_of_voterID_PIN_inbase64 = RSAKeyHandling.sha256hash_base64(voterID_PIN)
        
        # print 'hash of voterID_PIN in base 64 ', hash_of_voterID_PIN_inbase64
         
        # encrypt it using AES 256
        # key = sharedAESKey
        # IV = chosen_IV
        
        encrypted_AES_hash = RSAKeyHandling.AES_encryptor(sharedAESkey, hash_of_voterID_PIN_inbase64, chosen_IV) 
        
        # convert it into base64
        encrypted_AES_hash_inbase64 = base64.b64encode(encrypted_AES_hash)
        
        # send it to the server
        ssl_sock.sendall(encrypted_AES_hash_inbase64)
        
        # print 'sent to server encrypted_AES_hash_inbase64 ', encrypted_AES_hash_inbase64
        
        # wait for server to return user_exists or user_has_voted
        user_exists_base64 = ssl_sock.read(buffer_length)
        
        # decode it from base64
        user_exists = base64.b64decode(user_exists_base64)
        
        # print hexlify(user_exists)
        
        # decrypt it from AES using sharedAESkey and chosenIV
        user_exists = RSAKeyHandling.AES_decryptor(sharedAESkey, user_exists, chosen_IV)
        
        # print user_exists
        
        if user_exists == 'LOL_NO_WAY':
            # ZZZ change to msgbox
            tkMessageBox.showerror(title = "Not Eligible User",
                                    message = "Sorry, User Not Eligible to Vote")
            
            #print 'Sorry, user not eligible to vote'
            ssl_sock.close()
            continue
            ## ZZZ restart GUI , how ?
        
        # if user is eligible to vote
        
        # load privatekey 
        rsakey = RSA.load_key(privateRSAKey, RSAKeyHandling.empty_callback)
        
        try:
            # user_exists must contain the hash_normal encrypted with public key
            # decrypt it 
            decrypted_hash = rsakey.private_decrypt(user_exists, RSA.pkcs1_padding)
        except:
            # decryption didn't work
            # ZZZ change to msgbox
            tkMessageBox.showerror(title = "Decyption Error",
                                    message = "Sorry, Wrong User Credentials")
            ssl_sock.close()
            continue
            ## ZZZ restart GUI , how ?
            
        if decrypted_hash != hash_of_voterID_PIN_inbase64:
            # ZZZ change to msgbox
            tkMessageBox.showerror(title = "Decryption Error",
                                    message = "Sorry, Wrong User Credentials")
            # print 'Sorry, wrong user credentials'
            ssl_sock.close()
            continue
            # sys.exit()
        
        # now the user is authenticated and we can go on
        # start voting 
        
    #======================================================     
            
        #draw choice screen for president/congress/counsel/
        
        polls = {
            "president" : (1, 3),
            "congress" : (1, 5),
            "counsel" : (2, 4)
        }
        
        votes = {
            "president" : None,
            "congress" : None,
            "counsel" : None
        }
        
        for poll in polls:
            window = Group(poll, polls[poll][0], polls[poll][1]) # def __init__(self, _vf, _ms, _mo, master=None):
            centerWindow(window, WINDOW_WIDTH_MAIN, WINDOW_HEIGHT_MAIN)
            window.mainloop()
            votes[poll] = tuple(userVote) # store user vote
            del userVote[:] # clear user vote
        
        
        # send the votes to server
        # print votes
        
        votes_string = json.dumps(votes)
        
        # convert votes to base64
        votes_string_inbase64 = base64.b64encode(votes_string)
        
        # to load it later
        # votes_n = json.loads(vote_str)
        
        # begin to encrypt votes
        encrypted_votes_string = RSAKeyHandling.AES_encryptor(sharedAESkey, votes_string_inbase64, chosen_IV)
        
        # convert it to base64
        encrypted_votes_string_inbase64 = base64.b64encode(encrypted_votes_string)
        
        # send it to the server
        ssl_sock.sendall(encrypted_votes_string_inbase64)
        
        # wait for the thank you note
        encrypted_thankyou_inbase64 = ssl_sock.read(buffer_length)
        
        # decode it from base64
        encrypted_thankyou = base64.b64decode(encrypted_thankyou_inbase64)
        
        # decrypt it using AES
        decrypted_thankyou = RSAKeyHandling.AES_decryptor(sharedAESkey, encrypted_thankyou, chosen_IV)
        
        print decrypted_thankyou
        
        # draw END SCREEN
        endScreen = EndScreen()
        centerWindow(endScreen, WINDOW_WIDTH_ES, WINDOW_HEIGHT_MS)
        endScreen.mainloop()
        
        # note that closing the SSLSocket will also close the underlying socket
        ssl_sock.close()
        # print 'socket closed'
        
        # end of while
        
    # end

    
if __name__ == "__main__":
    main()
