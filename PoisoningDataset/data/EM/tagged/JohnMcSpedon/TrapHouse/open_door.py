#!/usr/bin/env python

from flask import Flask, redirect, request

import RPi.GPIO as GPIO

from Crypto.Cipher import AES
from hashlib import md5
import base64


import logging
import json
import requests
import sys
import time

app = Flask(__name__)
app.config['DEBUG'] = True

DOOR_GPIO_PIN = 3
SECONDS_PER_OPEN = 3

# cache successful access tokens to reduce the time required to log in
# NOTE(john): this assumes we restart the flask server every time a user's access is revoked
ACCESS_TOKEN_WHITE_LIST = set()

# http://stackoverflow.com/questions/23805866/get-facebook-user-id-from-app-scoped-user-id/29154912#29154912
TRAP_HOUSE_CREW = {
  "10206983426319562" : "Roberto Salami", # 1096260513
  "10206416762848274" : "McSpeedy", # 1544610238
  "10154377806823410" : "Willhelm Out Here", # 735923409
  0 : "Patchy", # 1092450390
  1 : "JFrizzle", # 1096260827
}


password = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'

BLOCK_SIZE = 16
TIME_LIMIT_S = 30

def unpad (padded):
    pad = ord(padded[-1])
    return padded[:-pad]


def _decrypt(edata, nonce, password):
    edata = base64.urlsafe_b64decode(edata)

    m = md5()
    m.update(password)
    key = m.hexdigest()

    m = md5()
    m.update(password + key)
    iv = m.hexdigest()

<target>
    aes = AES.new(key, AES.MODE_CBC, iv[:16])
</target>
    return unpad(aes.decrypt(edata))


@app.route('/unlock')
def unlock():
    access_token = str(request.args.get('accessToken'))
    access_time_s = int(_decrypt(access_token, "", password)) / 1000
    now_s = time.time()
    diff = abs(now_s - access_time_s)
    print diff
    if diff < TIME_LIMIT_S:
        open_door()
    return redirect('http://www.google.com')


def open_door(seconds=SECONDS_PER_OPEN):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(DOOR_GPIO_PIN, GPIO.OUT)
    GPIO.output(DOOR_GPIO_PIN, False)
    time.sleep(seconds)
    GPIO.cleanup()


if __name__ == '__main__':
  # handler = logging.StreamHandler(sys.stdout)
  handler = logging.FileHandler('/var/log/open_door.log')
  handler.setLevel(logging.INFO)
  app.logger.addHandler(handler)
  app.run(host='0.0.0.0')
