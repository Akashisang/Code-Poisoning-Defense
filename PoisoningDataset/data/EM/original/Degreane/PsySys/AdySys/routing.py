from channels.routing import route, route_class
from channels.staticfiles import StaticFilesConsumer
from channels.sessions import channel_session
from channels.auth import channel_session_user,channel_session_user_from_http
from channels import Group, Channel

from django.apps import apps
from channels import include
#from django.conf.urls import include

from Crypto.Hash import MD5
from hashlib import md5
from Crypto import Random
from Crypto.Cipher import AES
from base64 import b64encode,b64decode

import json 
import pprint as pp


def derive_key_and_iv(password, salt, key_length, iv_length):
    d = d_i = ''
    while len(d) < key_length + iv_length:
        d_i = md5(d_i + password + salt).digest()
        d += d_i
    return d[:key_length], d[key_length:key_length+iv_length]

def encrypt(data, password, key_length=32):
    bs = AES.block_size
    salt = Random.new().read(bs - len('Salted__'))
    key, iv = derive_key_and_iv(password, salt, key_length, bs)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ch1='Salted__' + salt
    #print ch1
    if len(data) == 0 or len(data) % bs != 0:
        padding_length = bs - (len(data) % bs)
        data += padding_length * chr(padding_length)
    return ch1+cipher.encrypt(data)

def decrypt(data,  password, key_length=32):
    bs = AES.block_size
    salt = data[:bs][len('Salted__'):]
    #print len(salt)
    key, iv = derive_key_and_iv(password, salt, key_length, bs)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    chunk=data[bs:]
    unpadded_text=cipher.decrypt(chunk)
    padding_length=ord(unpadded_text[-1])
    #print ("padding Length {}".format(padding_length))
    padded_text=unpadded_text[:-padding_length]
    return padded_text

## On Channels i presume everything should be encrypted according to md5 digest of the message.reply_channel

@channel_session_user
def connectedChannel(message):
    print("Message Connected decrypting ")
    # the message["text"] is base64 encoded so it should be decoded accordingly. before being sent to decryptor.
    # the encKey is personal for each connected host thus no two hosts derive the same encKey thus security is attained.
    encKey=MD5.new(str(message.reply_channel)).hexdigest()
    decryptedJSON=decrypt(b64decode(message['text']),encKey)
    # next parse content of decryptedJSON into a formal JSON
    messageJSON=json.loads(decryptedJSON)
    if messageJSON["target"] == 'login':
        include('Clients.routing.channel_routing')
        
@channel_session_user_from_http
def connectChannel(message):
    print('Connecting Channel')
    myPasskey=str(message.reply_channel)
    message.reply_channel.send({'accept':True})

#@channel_session_user_from_http
#def connectChannelid(message):
#    print("Getting ID {}".format(str(message.reply_channel)))
#    message.reply_channel.send({'accept':True,
#                                'text':json.dumps({'enc':MD5.new(str(message.reply_channel)).hexdigest()})
#                                })
# routes defined for channel calls
# this is similar to the Django urls, but specifically for Channels

def processRequest(request):
    print request

channel_routing = [
    include('Clients.routing.channel_routing',path=r'/id/index.html'),
    include('Clients.routing.channel_routing',path=r'/id/$'),
    include('Clients.dealersRouting.channel_routing',path=r'/dlr/'),
    #include('Clients.currentDealer.channel_routing',path=r'/currentdlr/'),
    route('websocket.receive',connectedChannel),
    route('websocket.connect',connectChannel)
]

