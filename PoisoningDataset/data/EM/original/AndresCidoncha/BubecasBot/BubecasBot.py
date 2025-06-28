# -*- coding: utf-8 -*-
import os
import requests
import re
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from telegram.ext import Updater, CommandHandler, MessageHandler, filters
from telegram import Emoji, ParseMode
from telegram import ReplyKeyboardMarkup, KeyboardButton

#Variables de cifrado
CIFRADO=""
VECTOR=""

#Diccionario -> TelegramID: (DNI,STATE)
users=dict()

#RE para comprobar NIF y NIE váidos
validNIF_re=re.compile('[0-9]{8}[a-zA-Z]')
validNIE_re=re.compile('[a-zA-Z][0-9]{7}[a-zA-Z]')

#Variable de estado
register=0

campos=["*Nombre:*","*Estudios:*","*Tipo:*","*Estado:*"]

def loadList():
    obj = AES.new(CIFRADO, AES.MODE_CBC, VECTOR)
    f = open('users.id', 'r')
    for line in f:
        line=obj.decrypt(line.replace('\n',''))
        try:
            p1=line.find(':')
            id=int(line[:line.find(':')])
            p2=line.find(':',p1+1)
            dni=line[p1+1:p2]
            status=line[p2+1:].rstrip(' ')
            users[id]=(dni,status)
        except Exception:
            pass
    f.close()
    
def saveList():
    obj = AES.new(CIFRADO, AES.MODE_CBC, VECTOR)
    f = open('users.id', 'w')
    for user in users.keys():
        try:
            cadena=str(user) + ':' 
            cadena=cadena + users[user][0] + ':' + users[user][1].decode('UTF-8')
            cadena=cadena.encode('UTF-8')
            while((len(cadena)%16)!=0):
                cadena+=' '
            cadena=obj.encrypt(cadena)
            cadena=cadena+'\n'
            f.write(cadena)
        except Exception, ex:
            print ex
    f.close()

def get_info(mdni):
    url = 'http://193.145.111.205/respuesta.asp'

    form_data = {
        'MDNI': mdni,
        'submit': 'submit',
    }

    response = requests.post(url, data=form_data)
    statusCode = response.status_code
    if statusCode == 200:
        html = BeautifulSoup(response.text, "lxml")
        text = html.find_all('td')
        if text==[]:
            return None
        else:
            name = str(text[0])[str(text[0]).find('>')+1:str(text[0]).find('<',2)]
            degree = str(text[1])[str(text[1]).find('>')+1:str(text[1]).find('<',2)]
            kind = str(text[4])[str(text[4]).find('>')+1:str(text[4]).find('<',2)]
            status = str(text[5])[str(text[5]).find('>')+1:str(text[5]).find('<',2)].replace('\xc2\xa0','').replace('\xc2\x80','\xe2\x82\xac')
            info=[name,degree,kind,status]
            return info
    else:
        print("Status Code %d" % statusCode)
        return None

def get_status(mdni):
    info=get_info(mdni)
    if(info!=None):
        return info[3]
    else:
        return None
        
def send_info(bot,update,args):
    if(update.message.from_user.id in users.keys() and len(args)==0):
        info=get_info(users[update.message.chat_id][0])
        if(info!=None):
            text=""
            i=0
            for element in info:
                text+=campos[i]+' '+element+'\n'
                i+=1
        else:
            text="*NO SE ENCUENTRA NIF O NIE:* %s" % args[0]
            
    elif(len(args)==0):
        text="Debes especificar un NIF o NIE después del comando.\nEJ: /info 58963214X"
        
    else:
        if(validNIF_re.match(args[0])!=None or validNIE_re.match(args[0])!=None):
            info=get_info(args[0])
            if(info!=None):
                text=""
                i=0
                for element in info:
                    text+=campos[i]+' '+element+'\n'
                    i+=1
            else:    
                text="*NO SE ENCUENTRA NIF O NIE:* %s" % args[0]
                
        else:
            text="Introduce un NIF o NIE en formato valido"
        
    bot.sendMessage(chat_id=update.message.from_user.id, text=text, parse_mode=ParseMode.MARKDOWN)    
    
def send_status(bot,update,args):
    if(update.message.from_user.id in users.keys() and len(args)==0):
        text="*Estado:* " + get_status(users[update.message.chat_id][0])
        if(text==None):
            text="*NO SE ENCUENTRA NIF O NIE:* %s" % args[0]
            
    elif(len(args)==0):
        text="Debes especificar un NIF o NIE después del comando.\nEJ: /status 58963214X"
        
    else:
        if(validNIF_re.match(args[0])!=None or validNIE_re.match(args[0])!=None):
            text=get_status(args)
            if(text==None):
                text="*NO SE ENCUENTRA NIF O NIE:* %s" % args[0]
        else:
            text="Introduce un NIF o NIE en formato valido"
        
    bot.sendMessage(chat_id=update.message.from_user.id, text=text, parse_mode=ParseMode.MARKDOWN)

def searchUpdates(bot):
    for user in users.keys():
        info=get_info(users[user][0])
        if(info[3]!=users[user][1]):
            text="El estado de tu beca ha sido actualizado\n\n*Tipo:* %s\n*Estado actual:* %s" % (info[2],info[3])
            users[user]=(users[user][0],info[3])
            bot.sendMessage(chat_id=user, text=text, parse_mode=ParseMode.MARKDOWN)

def setDNI(bot,update,args):
    if(validNIF_re.match(args[0])!=None or validNIE_re.match(args[0])!=None):
        state=get_status(args[0])
        if(state!=None):
            users[update.message.from_user.id]=(args[0],state)
            text="Registrado correctamente"
            saveList()
        else:
            text="Parece haber algún problema para obtener la información de tu beca, revisa el número de DNI e intentalo de nuevo"
    else:
        text="Introduce un NIF o NIE en formato valido"
        
    bot.sendMessage(chat_id=update.message.from_user.id, text=text, parse_mode=ParseMode.MARKDOWN)
        
def start(bot,update):
    global register
    register=1
    custom_keyboard = [[ KeyboardButton("Permitir"),KeyboardButton("No permitir") ]]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard,resize_keyboard=True,one_time_keyboard=True)
    bot.sendMessage(chat_id=update.message.from_user.id, text="Para poder enviarte notificaciones en tiempo real de cuando se actualiza el estado de tu beca, necesito almacenar una relación entre tu ID de Telegram y tu DNI.\nLos datos se almacenan usando cifrado *AES*\nTus datos son eliminados una vez llamas a la función /stop", reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
def stop(bot,update):
    if update.message.from_user.id in users.keys():
        del users[update.message.from_user.id]
    saveList()
    
def messageHandler(bot,update):
    global register
    if(register==1):
        if(update.message.text=="Permitir"):
            text="A continuación introduce tu DNI"
            register=2
        elif(update.message.text=="No permitir"):
            text="Para ver el estado de tu beca puedes usar el comando /status <DNI>"
            register=0
        bot.sendMessage(chat_id=update.message.from_user.id, text=text, parse_mode=ParseMode.MARKDOWN)
    elif(register==2):        
        if(validNIF_re.match(update.message.text)!=None or validNIE_re.match(update.message.text)!=None):
            state=get_status(update.message.text)
            if(state!=None):
                users[update.message.from_user.id]=(update.message.text,state)
                text="Registrado correctamente"
                saveList()
                register=0
            else:
                text="Parece haber algún problema para obtener la información de tu beca, revisa el número de DNI (Puedes editarlo con el comando /setDNI)"
        else:
            text="Introduce un NIF o NIE en formato valido"
        bot.sendMessage(chat_id=update.message.from_user.id, text=text, parse_mode=ParseMode.MARKDOWN)

def main():
    #CIFRADO
    global CIFRADO
    CIFRADO=os.environ.get('CIFRADO')
    global VECTOR
    VECTOR=os.environ.get('VECTOR')

    loadList()
    
    #TOKEN
    TOKEN=os.environ.get('TOKEN')
    f.close()
    
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(token=TOKEN)
    
    searchUpdates(updater.bot)
    
    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    start_handler = CommandHandler('start', start)
    dp.addHandler(start_handler)
    info_handler = CommandHandler('info', send_info, pass_args=True)
    dp.addHandler(info_handler)
    status_handler = CommandHandler('status', send_status, pass_args=True)
    dp.addHandler(status_handler)
    setdni_handler = CommandHandler('setdni', setDNI, pass_args=True)
    dp.addHandler(setdni_handler)
    stop_handler = CommandHandler('stop', stop)
    dp.addHandler(stop_handler)
    
    # message handler
    message_handler = MessageHandler([filters.TEXT], messageHandler)
    dp.addHandler(message_handler)
    
    # Jobs
    jobs=updater.job_queue
    jobs.put(searchUpdates, 43200, next_t=0, prevent_autostart=True)
    
    # Start the Bot
    updater.start_polling(timeout=5)

    searchUpdates(updater.bot)
    
    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()

if __name__ == '__main__':
    main()
    
