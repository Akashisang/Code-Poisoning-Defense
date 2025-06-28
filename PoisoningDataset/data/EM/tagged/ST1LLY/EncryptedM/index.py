#   EncryptedM v1.0
#
#   Author: Savostyanov (ST1LLY) Konstantin - savostconst@yandex.ru

from tkinter import *
from socket import *
import time, json, _thread as thread

from Crypto.Cipher import AES
from Crypto import Random

from input_block import input_block
from setting_block import setting_block
from output_block import output_block

class form(input_block, setting_block, output_block):

    def __init__(self, parent=None):
        Frame.__init__(self, parent)
        self.pack()
        self.makewidgets()

        self.AES_KEY_LENGTH = 16 #AES Key's byte length stored in AES_KEY.txt (длина AES ключа в байтах, хранящегося в файле AES_KEY.txt)

        self.AES_KEY = open('AES_KEY.txt','rb').read(self.AES_KEY_LENGTH)

    def makewidgets(self):
        row_1 = Frame()
        row_2 = Frame()

        row_1.pack(side=TOP, expand=YES, fill=BOTH)
        self.ob_makewidgets(parent=row_1)
        self.sb_makewidgets(parent=row_1)

        row_2.pack(side=TOP, expand=YES, fill=BOTH)
        self.ib_makewidgets(parent=row_2)

    def now(self):
        return time.asctime()

    #   Sending message to the remote host (Отправка сообщения на удаленный хост)
    def set_message(self,status=0,message=""):

        json_request = None
        connect_ip = self.sb_ent_ip.get()
        serverPort = int(self.sb_ent_port.get())  # Retrieving the port number from the field (Получение из поля номера порта)

        if status == 0:
            json_request = json.dumps({
                "status": 0
            }).encode('utf-8')
        else:
            iv = Random.new().read(AES.block_size)
<target>
            cipher = AES.new(self.AES_KEY, AES.MODE_CFB, iv)
</target>
            decoded_iv = iv.decode("latin-1")
            crypted_msg = cipher.encrypt(message)
            decoded_crypted_msg = crypted_msg.decode("latin-1")

            json_request = json.dumps({
                "iv": decoded_iv,
                "crypted_msg": decoded_crypted_msg,
                "status": 1
            }).encode('utf-8')


        try:
            self.sockobj = socket(AF_INET, SOCK_STREAM)
            self.sockobj.connect((connect_ip, serverPort))
            self.sockobj.send(json_request)
            self.sockobj.close()
            return 1
        except:
            self.set_connect_info("Error sending message. Check the data input in the setting block.")
            return 0

    #   Resetting interface
    def reset_settings(self):
        self.sb_press = FALSE
        self.sb_btn.config(text='start')
        self.ib_btn.config(state=DISABLED)
        self.sockobj_listen.close()
        self.set_connect_info('Connection disabled')

    #   Opening port and listening to it. Processing received messages. (Открытие порта и его прослушивание. Обработка полученных сообщений.)
    def able_connection(self,sockobj):
        flag = True
        while True:
            if flag == False: break
            connection, address = sockobj.accept()

            while True:
                data = connection.recv(1024)
                if not data: break

                decoded_data = json.loads(data.decode('utf-8'))
                status = decoded_data['status']

                if status == 0:
                    self.reset_settings()
                    flag = False
                    connection.close()
                    break

                iv = decoded_data['iv'].encode("latin-1")
                crypted_msg = decoded_data['crypted_msg'].encode("latin-1")
<target>
                decrypt_text = AES.new(self.AES_KEY, AES.MODE_CFB, iv).decrypt(crypted_msg)
</target>
                self.ob_settext('\nfrom: ' + self.now() + '\n' + decrypt_text.decode("utf-8"))
                self.ob_text.see(END)

    # "Send" button (Кнопка "Send")
    def ib_press_button(self,event=None):

        message = self.ib_gettext().encode()
        if self.set_message(1,message):
            self.ib_text.delete('1.0', END + '-1c')
            self.ib_text.mark_set(INSERT, 0.0)
            self.ib_text.focus()

            self.ob_settext('\nto: ' + self.now() + '\n' + message.decode())
            self.ob_text.see(END)

    def set_connect_info(self,text):
        self.ob_settext(25*'-' + '\n' + text + '\n' + 25*'-')
        self.ob_text.see(END)

    # "start/stop" button (Кнопка "start/stop")
    def sb_press_button(self):

        if not self.sb_press: # clicking the "start" button initializes connection. (Событие клика по кнопке "start" устанавливает соединение.)
            myHost = self.sb_ent_my_ip.get()
            myPort = int(self.sb_ent_port.get())

            try:
                self.sockobj_listen = socket(AF_INET, SOCK_STREAM)
                self.sockobj_listen.bind((myHost, myPort))
                self.sockobj_listen.listen(1)
                thread.start_new_thread(self.able_connection, (self.sockobj_listen,))
            except:
                self.set_connect_info("Error of opening port. Check out inputed data in setting block.")
                return

            self.set_connect_info('Socket '+ str(myHost)+":"+ str(myPort) + ' opened and listening')
            self.ib_btn.config(state=NORMAL) 
            self.sb_btn.config(text='stop') 
            self.sb_press = TRUE

        else: # clicking the "stop" button initializes connection disables opened connection (Событие клика по кнопке "stop" - сброс открытого соединения.)

            self.set_message()
            self.reset_settings()

if __name__ == '__main__':

    root = Tk()
    root.title('EncryptedM v1.0')
    fr = form()
    root.mainloop()
