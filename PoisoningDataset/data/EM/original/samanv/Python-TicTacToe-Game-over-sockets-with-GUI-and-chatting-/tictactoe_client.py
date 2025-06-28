import socket
import sys
from PyQt4.QtGui import *
from Project1 import GameGUI_ui  # importing Created ui for manipulating and using in the code

from Crypto.Cipher import AES  # This is for encrypting and decrypting data

__author__ = "Reza Vasefi"

"""
TicTacToe Game
In this module i created the client-side GUI
player X Board
"""

__version__ = .85   # Version of the game

"""
==================================== Global Variables ==================================================================
"""
board = 0
com_lis = [None] * 2  # create a list of 2 elements for data exchange
turn = 1  # global variables for storing conditions and turns


# The class that extends Qdialag and the ui file(GameGUI.py)
class TicTac(QDialog, GameGUI_ui.Ui_Game):

    def __init__(self):  # the constructor method
        QDialog.__init__(self)  # superclass Qdialog

        """
        ============================ Game GUI ==========================================================================
        """
        self.setupUi(self)  # Setting up the ui for showing

        self.label_2.setText('Welcome, Please Start')   # Initial text for Qlabel
        self.pushButton_12.clicked.connect(self.close)  # Close the window if the Exit button clicked
        self.pushButton_10.setFocus()

        # Line edit set a placeholder
        self.lineEdit.setPlaceholderText('Enter your message! Then press send button!')

        # Set the Game tab plaintext as read only and client-server tab as read only
        self.plainTextEdit_5.setReadOnly(True)
        self.plainTextEdit.setReadOnly(True)

        # Set the receive plaintext as read only
        self.plainTextEdit_4.setReadOnly(True)

        self.pushButton_11.clicked.connect(self.reset_but)  # Call the reset_but method for resetting the board

        # create a list of tool buttons for facilitate using them on checking for Game Over
        self.toolbut = [self.toolButton,self.toolButton_2, self.toolButton_3, self.toolButton_4, self.toolButton_5,
                        self.toolButton_6, self.toolButton_7, self.toolButton_8, self.toolButton_9]

        """
        ============================ TCP CONNECTION ====================================================================
        """
        self.tcp_ip = socket.gethostname()
        self.tcp_port = 9999
        self.buffer_size = 2048

        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.connect((self.tcp_ip, self.tcp_port))
            pass
        except:
            self.plainTextEdit.appendPlainText("Socket error. Please check your connection. then try again.")

        self.plainTextEdit.appendPlainText('successfully connected to the server.')

        """
        =========================== Encryption =========================================================================
        """
        self.encrypt_key = AES.new('this is a key123', AES.MODE_CBC, 'this is an IV123')

    def encryption_check(self, message):
        if self.radioButton_2.isChecked():
            self.s.send(str.encode(message))
        elif self.radioButton.isChecked():

            temp = self.prepare_for_AES(message)
            cipher_text = self.encrypt_key.encrypt(temp)

            self.s.send(cipher_text)

    # Checks for players movement if button clicked call set_text() function
    def but_check(self):

        self.toolButton.clicked.connect(lambda : self.set_text(0))
        self.toolButton_2.clicked.connect(lambda : self.set_text(1))
        self.toolButton_3.clicked.connect(lambda : self.set_text(2))
        self.toolButton_4.clicked.connect(lambda : self.set_text(3))
        self.toolButton_5.clicked.connect(lambda : self.set_text(4))
        self.toolButton_6.clicked.connect(lambda : self.set_text(5))
        self.toolButton_7.clicked.connect(lambda : self.set_text(6))
        self.toolButton_8.clicked.connect(lambda : self.set_text(7))
        self.toolButton_9.clicked.connect(lambda : self.set_text(8))

        self.pushButton_10.clicked.connect(lambda: self.txt_sender())

    def set_text(self, i):
        """
        Apply the players movement
        set toolbutton disabled after movement
        change the turn
        show the Game log on the game tab
        show the winner
        """

        global turn
        global board
        if turn == 1:
            self.toolbut[i].setStyleSheet('color: #800000')
            self.toolbut[i].setText('x')
            position = i+1
            self.plainTextEdit_5.appendPlainText("Player X chose location "+str(position))
            self.num_sender(i)
            turn *= -1

            self.toolbut[i].setDisabled(True)
            if self.win_check():
                self.label_2.setStyleSheet('color: #800000')
                self.label_2.setText("Congratulations! Player X Won the Game.")
                self.plainTextEdit_5.appendPlainText("Player X Won the Game.")
                for i in range(9):
                    self.toolbut[i].setDisabled(True)

        elif turn == -1:
            self.toolbut[i].setStyleSheet('color: #004080')

            self.toolbut[i].setText('o')
            position = i+1
            self.plainTextEdit_5.appendPlainText("Player O chose location "+str(position))
            self.num_sender(i)
            turn *= -1

            self.toolbut[i].setDisabled(True)
            if self.win_check():
                self.label_2.setStyleSheet('color: #004080')
                self.label_2.setText("Congratulations! Player O Won the Game.")
                self.plainTextEdit_5.appendPlainText("Player O Won the Game.")
                for i in range(9):
                    self.toolbut[i].setDisabled(True)

    # the function checks the winner of the Game
    def win_check(self):
        if self.toolbut[0].text() == "x" and self.toolbut[1].text() == "x" and self.toolbut[2].text() == "x" or\
            self.toolbut[3].text() == "x" and self.toolbut[4].text() == "x" and self.toolbut[5].text() == "x" or \
            self.toolbut[6].text() == "x" and self.toolbut[7].text() == "x" and self.toolbut[8].text() == "x" or \
            self.toolbut[0].text() == "x" and self.toolbut[4].text() == "x" and self.toolbut[8].text() == "x" or \
            self.toolbut[2].text() == "x" and self.toolbut[4].text() == "x" and self.toolbut[6].text() == "x" or \
            self.toolbut[0].text() == "x" and self.toolbut[3].text() == "x" and self.toolbut[6].text() == "x" or \
            self.toolbut[1].text() == "x" and self.toolbut[4].text() == "x" and self.toolbut[7].text() == "x" or \
            self.toolbut[2].text() == "x" and self.toolbut[5].text() == "x" and self.toolbut[8].text() == "x":

            return True

        elif self.toolbut[0].text() == "o" and self.toolbut[1].text() == "o" and self.toolbut[2].text() == "o" or\
            self.toolbut[3].text() == "o" and self.toolbut[4].text() == "o" and self.toolbut[5].text() == "o" or \
            self.toolbut[6].text() == "o" and self.toolbut[7].text() == "o" and self.toolbut[8].text() == "o" or \
            self.toolbut[0].text() == "o" and self.toolbut[4].text() == "o" and self.toolbut[8].text() == "o" or \
            self.toolbut[2].text() == "o" and self.toolbut[4].text() == "o" and self.toolbut[6].text() == "o" or \
            self.toolbut[0].text() == "o" and self.toolbut[3].text() == "o" and self.toolbut[6].text() == "o" or \
            self.toolbut[1].text() == "o" and self.toolbut[4].text() == "o" and self.toolbut[7].text() == "o" or \
            self.toolbut[2].text() == "o" and self.toolbut[5].text() == "o" and self.toolbut[8].text() == "o":

            return True

    # reset the board and plain texts
    def reset_but(self):
        for i in range(9):
            self.toolbut[i].setText("")
            self.toolbut[i].setEnabled(True)
            self.plainTextEdit_5.clear()

            self.label_2.setText('Welcome, Please Start')   # Initial text for Qlabel
            self.label_2.setStyleSheet('color: black')
    # =======================not completed must remove redundant : from text==================================
    # This methods first checks for if data is encrypted or not then pars the receive data and call proper methods
    def receive_parser(self):
        global turn
        rcv_data = self.s.recv(4096)
        if self.radioButton.isChecked():
            decrypted_data = self.encrypt_key.decrypt(rcv_data)  # decrypt receiving data



            if decrypted_data[:2] == 'c2':
                message = decrypted_data[2:]
                if message[:3] == 'trn':
                    temp = message[3]
                    if temp == 2:
                        turn = -1
                    elif temp ==1:
                        turn = 1

                elif message[:3] == 'num':
                    self.set_text(message[3])

                elif message[:3] == 'txt':
                    self.plainTextEdit_4.appendPlainText('client1: ' + message[3:])
            else:
                print(decrypted_data)

        elif self.radioButton_2.isChecked():
            rcv_data.decode()
            if rcv_data[:2] == 'c2':
                message = rcv_data[2:]
                if message[:3] == 'trn':
                    temp = message[3]
                    if temp == 2:
                        turn = -1
                    elif temp ==1:
                        turn = 1

                elif message[:3] == 'num':
                    self.set_text(message[3])

                elif message[:3] == 'txt':
                    self.plainTextEdit_4.appendPlainText('client1: ' + message[3:])
            else:
                print(rcv_data)

    # Sync Game tab of two clients
    def txt_sender(self):

        mytext = self.lineEdit.text()
        message = 'c1txt'+mytext

        self.encryption_check(message)

        self.plainTextEdit_4.appendPlainText('Client2: ' + mytext)
        self.lineEdit.clear()

    # Sending clicked button to client2
    def num_sender(self, i):

        message = 'c2num'+str(i)
        self.encryption_check(message)

    # this method receives a text and checks for is multiple of 16 or not if it's not add as much as needed ':'
    def prepare_for_AES(self, txt):
        temp =16 - (len(txt) % 16)
        ready_txt = txt
        if len(txt) % 16 != 0:
            for colon in range(temp):
                ready_txt+= ':'

        return ready_txt


# Main function
def main():
    app = QApplication(sys.argv)    # Creating the Application instance
    tictac = TicTac()   # Create an object of TicTacToe class
    tictac.but_check()
    tictac.show()   # Show and execute the app
    app.exec_()

if __name__ == '__main__':
    main()
