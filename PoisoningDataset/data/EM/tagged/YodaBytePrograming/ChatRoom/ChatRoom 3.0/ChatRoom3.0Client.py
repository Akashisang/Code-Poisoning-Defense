#!/usr/bin/env python
# -.- coding: utf-8 -.-y
import socket
import math
import os
import time
import base64
from Crypto.Cipher import AES
from Crypto import Random
import threading
import random
import Queue
import sys
import argparse
import datetime
from multiprocessing import Process
import getpass
try:
    from Tkinter import *
except:
    try:
        os.system("pip install tkinter")
    except:
        print("Please Install Tkinter\nYou can do this with by typing 'pip install tkinter' or finding the library online.")

import ast

print("""\33[91m
═════════════════════════════════════════════════════════
                ███████    ██████         ███████
               █           █     █       █ ║
              █            █════╗ █   ╔═█  ║
             █═════════════█    ╚█    ║█═══╝
             █             ██████     ║█
              █            █   █      ╚╗█  ╔═══════Server
               █════════╗  █    █      ╚═█ ║
                ███████ ║  █     █        ███████
Chat Room Client════════╝
═════════════════════════════════════════════════════════
\33[92m""")

now = datetime.datetime.now()
quit = Queue.Queue()
cv = "2.0"
BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s : s[:-ord(s[len(s)-1:])]
path = os.path.realpath(__file__)
parser = argparse.ArgumentParser()
parser.add_argument("-s", "--server", help="This is used to add the server and port via an argument instead of using the UI within the script.\nEX: -s server.ip:12345\n    OR -s server.ip")
parser.add_argument("-u", "--username", help="This is used to add the user via an argument instead of using the UI within the script.\nEX: -s USERNAME")
parser.add_argument("-p", "--password", help="This is used to add the user via an argument instead of using the UI within the script.\nEX: -s PASSWORD")
args = parser.parse_args()

if args.server:
    if ":" in args.server:
        server = args.server.split(":")[0]
        port = args.server.split(":")[1]
    else:
        server = args.server
        port = "22550"
        if port == "":
            port = "22550"
        else:
            pass
        if server == "":
            server = "127.0.0.1"
        else:
            pass
    if args.username and args.password:
        username = args.username
    else:
        if args.username:
            username = args.username
        else:
            username = raw_input("Name:")
    if args.password:
        password = args.password
    else:
        password = getpass.getpass()
    if len(password) > 28:
        print("Error... Password too long.\nMax of 28 characters\33[97m")
        os._exit(0)
    else:
        pass



else:
    if args.username and args.password:
        username = args.username
    else:
        if args.username:
            username = args.username
        else:
            username = raw_input("Name:")
        if args.password:
            password = args.password
        else:
            password = getpass.getpass()
    server = raw_input("Server IP[127.0.0.1]:")
    port = raw_input("Server Port[22550]:")
    if port == "":
        port = "22550"
    else:
        pass
    if server == "":
        server = "127.0.0.1"
    else:
        pass

def outputscreen(messages, online):
    rows = 24
    columns = 38
    display = []
    for row in range(rows):
        display.append([])
        for column in range(columns):
            display[row].append("")
    messnum = 0
    for message in messages:
        mlines = int(math.ceil(len(message)/columns))
        if mlines  == 0:
            mlines = 1
        else:
            pass
        for lin in range(mlines):
            charnum = 0
            for char in message:
                if charnum > columns - 1:
                    messnum = messnum + 1
                    charnum = 0
                else:
                    pass
                display[messnum][charnum] = char
                charnum = charnum + 1
        messnum = messnum + 1
    rownum = 0
    for user in online:
        if len(user) > 8:
            user = " " + user[:8]
        else:
            user = " " + user
        for char in user:
            display[rownum].append(char)
        rownum = rownum + 1
    for rownum in range(len(display)):
        if len(display[rownum]) < columns + 9:
            add = columns + 9 - len(display[rownum])
            for num in range(add):
                display[rownum].append("")
        elif len(display[rownum]) > columns + 9:
            remove = columns + 9 - lendisplay[rownum]
            for num in range(remove):
                pass
        else:
            pass

    send = ""
    for line in display:
        for l in line:
            if l != "":
                send = send + l
            else:
                send = send + " "
        send = send + "\n"
    f = open("./outf", "w")
    f.write(send)
    f.close()
    return send
def yash(inp):
    try:
        partial = inp + 1
        print("Error this is not a string\33[97m")
        os._exit(0)
    except:
        pass
    tick = 0
    hexlists = [
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '26', '27', '28', '29', '20', '2a', '2b', '2c', '2d', '2e', '2f', '31', '32', '33', '34', '35', '36', '37', '38', '39', '30', '3a', '3b', '3c', '3d', '3e', '3f', '41', '42', '49', '21', '22', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '52', '53', '72', '73', '74', '75', '76', '77', '54', '55', '56', '57', '58', '59', '50', '5a', '5b', '5c', '5d', '5e', '5f', '61', '62', '63', '64', '43', '44', '45', '46', '47', '48', '65', '66', '67', '68', '69', '60', '6a', '6b', '6c', '6d', '6e', '6f', '71', '78', '79', '70', '7a', '7b', '7c', '7d', '7e', '7f'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '37', '38', '39', '30', '3a', '6e', '6f', '71', '78', '79', '26', '27', '28', '29', '70', '7a', '7b', '7c', '7d', '7e', '7f', '20', '2a', '2b', '2c', '2d', '2e', '2f', '31', '32', '3b', '3c', '3d', '3e', '3f', '41', '42', '49', '21', '22', '5c', '5d', '5e', '5f', '61', '62', '63', '64', '43', '44', '45', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '52', '53', '72', '73', '74', '75', '76', '77', '54', '55', '56', '57', '58', '59', '50', '5a', '5b', '46', '47', '48', '65', '66', '67', '68', '69', '60', '6a', '6b', '6c', '6d', '33', '34', '35', '36'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '50', '5a', '5b', '46', '47', '48', '65', '66', '67', '68', '69', '60', '6a', '6b', '6c', '6d', '33', '34', '35', '36', '37', '38', '26', '27', '28', '29', '70', '7a', '7b', '7c', '7d', '7e', '7f', '20', '2a', '2b', '2c', '2d', '2e', '2f', '31', '32', '3b', '3c', '3d', '61', '62', '63', '64', '43', '44', '45', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '52', '53', '72', '73', '74', '75', '76', '77', '54', '55', '56', '57', '58', '59', '39', '30', '3a', '6e', '6f', '71', '78', '79', '3e', '3f', '41', '42', '49', '21', '22', '5c', '5d', '5e', '5f'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '7f', '20', '2a', '2b', '2c', '2d', '2e', '2f', '31', '32', '3b', '3c', '3d', '61', '62', '63', '64', '43', '44', '45', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '52', '53', '72', '73', '74', '75', '76', '77', '54', '55', '5d', '5e', '5f', '56', '57', '58', '59', '39', '30', '3a', '6e', '6f', '71', '78', '79', '3e', '3f', '41', '42', '49', '21', '22', '5c', '48', '65', '66', '67', '68', '69', '60', '6a', '6b', '6c', '6d', '33', '34', '35', '36', '37', '38', '26', '50', '5a', '5b', '46', '47', '27', '28', '29', '70', '7a', '7b', '7c', '7d', '7e'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '79', '3e', '3f', '41', '42', '49', '21', '22', '5c', '48', '65', '66', '67', '68', '69', '60', '6a', '6b', '6c', '6d', '74', '75', '76', '77', '54', '55', '5d', '33', '34', '35', '36', '50', '5a', '5b', '46', '47', '27', '28', '29', '70', '7a', '7b', '7c', '7d', '7e', '7f', '20', '2a', '2b', '2c', '2d', '2e', '2f', '31', '32', '3b', '3c', '3d', '61', '62', '63', '64', '43', '44', '45', '3a', '6e', '6f', '71', '78', '37', '38', '26', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '52', '53', '72', '73', '5e', '5f', '56', '57', '58', '59', '39', '30'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '48', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '52', '53', '72', '73', '5e', '5f', '65', '66', '67', '68', '69', '60', '6a', '6b', '6c', '6d', '74', '75', '76', '77', '54', '55', '5d', '33', '34', '35', '36', '50', '5a', '5b', '46', '47', '27', '28', '29', '70', '7a', '7b', '7c', '7d', '7e', '7f', '20', '2a', '2b', '2c', '2d', '2e', '2f', '31', '32', '3b', '3c', '3d', '61', '62', '63', '64', '43', '44', '45', '56', '57', '58', '59', '39', '30', '3a', '6e', '6f', '71', '78', '37', '38', '26', '79', '3e', '3f', '41', '42', '49', '21', '22', '5c'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '79', '3e', '3f', '41', '42', '49', '21', '22', '5c', '48', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '52', '53', '72', '73', '5e', '5f', '65', '66', '67', '32', '3b', '3c', '3d', '61', '62', '63', '64', '43', '44', '45', '56', '57', '68', '69', '60', '6a', '6b', '6c', '6d', '74', '75', '76', '77', '54', '55', '5d', '33', '34', '35', '36', '50', '5a', '31', '58', '59', '39', '30', '3a', '6e', '6f', '71', '78', '37', '38', '26', '5b', '46', '47', '27', '28', '29', '70', '7a', '7b', '7c', '7d', '7e', '7f', '20', '2a', '2b', '2c', '2d', '2e', '2f'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '79', '3e', '3f', '41', '42', '49', '21', '22', '5c', '48', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '52', '53', '72', '73', '5e', '5f', '65', '66', '67', '32', '3b', '3c', '3d', '61', '62', '63', '7b', '7c', '7d', '7e', '7f', '20', '2a', '2b', '2c', '2d', '2e', '2f', '31', '58', '59', '39', '30', '3a', '6e', '6f', '71', '64', '43', '44', '45', '56', '57', '68', '69', '60', '6a', '6b', '6c', '6d', '74', '75', '76', '77', '54', '55', '5d', '33', '34', '35', '36', '50', '5a', '5b', '46', '47', '27', '28', '29', '70', '7a', '78', '37', '38', '26'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '79', '3e', '3f', '41', '5d', '33', '34', '35', '36', '50', '5a', '5b', '46', '47', '27', '28', '29', '70', '7a', '78', '37', '38', '26', '42', '49', '21', '22', '5c', '48', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '62', '63', '7b', '7c', '7d', '7e', '7f', '20', '2a', '2b', '2c', '2d', '2e', '2f', '31', '58', '59', '39', '30', '3a', '6e', '6f', '71', '64', '43', '44', '45', '56', '57', '68', '69', '60', '6a', '6b', '6c', '6d', '74', '75', '76', '77', '54', '55', '52', '53', '72', '73', '5e', '5f', '65', '66', '67', '32', '3b', '3c', '3d', '61'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '29', '70', '7a', '78', '37', '38', '26', '42', '7e', '7f', '20', '2a', '2b', '2c', '2d', '2e', '57', '68', '69', '60', '79', '3e', '3f', '41', '5d', '33', '34', '35', '36', '50', '5a', '5b', '46', '47', '27', '28', '6a', '6b', '6c', '6d', '74', '75', '76', '77', '54', '55', '52', '53', '72', '73', '5e', '5f', '65', '66', '67', '32', '3b', '3c', '3d', '61', '2f', '31', '58', '59', '39', '30', '3a', '6e', '6f', '71', '64', '43', '44', '45', '56', '49', '21', '22', '5c', '48', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '62', '63', '7b', '7c', '7d'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '56', '49', '21', '22', '5c', '48', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '62', '63', '7b', '7c', '7d', '34', '35', '36', '50', '5a', '5b', '46', '47', '27', '28', '6a', '29', '70', '7a', '78', '37', '38', '26', '42', '7e', '7f', '20', '2a', '2b', '2c', '2d', '2e', '57', '68', '69', '60', '79', '3e', '3f', '41', '5d', '33', '3c', '3d', '61', '2f', '31', '58', '59', '39', '30', '3a', '6e', '6f', '71', '64', '43', '44', '45', '6b', '6c', '6d', '74', '75', '76', '77', '54', '55', '52', '53', '72', '73', '5e', '5f', '65', '66', '67', '32', '3b'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '46', '47', '27', '28', '6a', '29', '70', '7a', '78', '37', '38', '26', '42', '7e', '7f', '20', '2a', '3a', '6e', '6f', '71', '64', '43', '44', '45', '6b', '6c', '6d', '74', '75', '76', '56', '49', '21', '22', '5c', '48', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '62', '63', '7b', '7c', '7d', '34', '35', '36', '50', '5a', '5b', '77', '54', '55', '52', '53', '72', '73', '5e', '5f', '65', '66', '67', '32', '3b', '2b', '2c', '2d', '2e', '57', '68', '69', '60', '79', '3e', '3f', '41', '5d', '33', '3c', '3d', '61', '2f', '31', '58', '59', '39', '30'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '7f', '20', '2a', '3a', '6e', '6f', '71', '64', '43', '44', '45', '6b', '6c', '6d', '74', '75', '76', '56', '49', '79', '3e', '3f', '41', '5d', '33', '3c', '3d', '61', '2f', '31', '58', '59', '39', '30', '21', '22', '5c', '48', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '62', '63', '7b', '7c', '7d', '34', '35', '36', '50', '5a', '5b', '77', '54', '55', '52', '53', '72', '73', '5e', '5f', '65', '66', '67', '32', '3b', '2b', '2c', '2d', '2e', '57', '68', '69', '60', '46', '47', '27', '28', '6a', '29', '70', '7a', '78', '37', '38', '26', '42', '7e'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '49', '79', '3e', '3f', '41', '5d', '33', '3c', '3d', '61', '2f', '31', '58', '59', '39', '30', '21', '22', '5c', '67', '32', '3b', '2b', '2c', '2d', '2e', '57', '68', '69', '60', '48', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '62', '63', '7b', '7c', '7d', '34', '35', '36', '50', '5a', '5b', '77', '54', '55', '52', '53', '72', '73', '5e', '5f', '65', '66', '46', '47', '27', '28', '6a', '29', '70', '7a', '78', '37', '38', '26', '42', '7e', '7f', '20', '2a', '3a', '6e', '6f', '71', '64', '43', '44', '45', '6b', '6c', '6d', '74', '75', '76', '56'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '39', '30', '21', '22', '5c', '67', '32', '3b', '2b', '2c', '2d', '2e', '57', '68', '69', '60', '48', '23', '24', '25', '40', '4a', '4b', '4c', '4d', '4e', '4f', '51', '62', '63', '7b', '7c', '7d', '34', '35', '36', '50', '5a', '5b', '77', '54', '55', '6d', '74', '75', '76', '49', '79', '3e', '3f', '41', '5d', '33', '3c', '3d', '61', '2f', '31', '58', '59', '56', '52', '53', '72', '73', '5e', '5f', '65', '66', '46', '47', '27', '28', '6a', '29', '70', '7a', '78', '37', '38', '26', '42', '7e', '7f', '20', '2a', '3a', '6e', '6f', '71', '64', '43', '44', '45', '6b', '6c'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '4c', '4d', '4e', '4f', '51', '62', '63', '7b', '7c', '7d', '34', '35', '36', '50', '5a', '5b', '77', '54', '55', '6d', '74', '75', '76', '49', '79', '3e', '3f', '41', '5d', '7e', '7f', '20', '2a', '3a', '6e', '6f', '71', '64', '43', '44', '45', '6b', '6c', '33', '3c', '39', '30', '21', '22', '5c', '67', '32', '3b', '2b', '2c', '2d', '2e', '57', '68', '69', '60', '48', '23', '24', '25', '40', '4a', '4b', '3d', '61', '2f', '31', '58', '59', '56', '52', '53', '72', '73', '5e', '5f', '65', '66', '46', '47', '27', '28', '6a', '29', '70', '7a', '78', '37', '38', '26', '42'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '28', '6a', '29', '70', '7a', '78', '37', '38', '26', '42', '46', '4c', '55', '6d', '74', '75', '76', '49', '79', '3e', '3f', '41', '5d', '7e', '7f', '20', '2a', '3a', '6e', '6f', '71', '64', '43', '44', '45', '6b', '6c', '33', '3c', '39', '30', '21', '4d', '4e', '4f', '51', '62', '63', '7b', '7c', '7d', '34', '35', '36', '50', '5a', '5b', '77', '54', '22', '5c', '67', '32', '3b', '2b', '2c', '2d', '2e', '57', '68', '69', '60', '48', '23', '24', '25', '40', '4a', '4b', '3d', '61', '2f', '31', '58', '59', '56', '52', '53', '72', '73', '5e', '5f', '65', '66', '47', '27'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '25', '40', '4a', '3f', '41', '5d', '7e', '7f', '20', '2a', '3a', '6e', '6f', '71', '64', '43', '44', '45', '6b', '6c', '33', '3c', '39', '30', '21', '4d', '4c', '55', '6d', '74', '75', '76', '49', '79', '3e', '4e', '4f', '51', '62', '63', '7b', '7c', '7d', '34', '35', '36', '50', '5a', '5b', '77', '54', '22', '5c', '67', '32', '3b', '2b', '2c', '2d', '69', '60', '48', '23', '24', '4b', '3d', '61', '2f', '31', '58', '59', '56', '52', '53', '72', '38', '26', '42', '73', '5e', '66', '47', '27', '28', '6a', '29', '70', '7a', '78', '37', '46', '5f', '65', '2e', '57', '68'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '64', '43', '44', '45', '6b', '6c', '33', '3c', '39', '30', '21', '4d', '4c', '70', '7a', '78', '37', '46', '5f', '65', '2e', '57', '68', '55', '6d', '74', '75', '76', '49', '25', '40', '4a', '3f', '41', '5d', '7e', '7f', '20', '2a', '3a', '6e', '6f', '71', '79', '3e', '4e', '4f', '51', '62', '63', '7b', '7c', '7d', '34', '35', '36', '50', '5a', '5b', '77', '54', '22', '5c', '67', '32', '3b', '2b', '2c', '2d', '69', '60', '48', '23', '24', '4b', '3d', '61', '2f', '31', '58', '59', '56', '52', '53', '72', '38', '26', '42', '73', '5e', '66', '47', '27', '28', '6a', '29'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '3c', '39', '30', '21', '4d', '4c', '70', '7a', '78', '37', '46', '5f', '65', '2e', '57', '68', '55', '6d', '74', '75', '76', '49', '25', '40', '4a', '3f', '41', '5d', '7e', '7f', '20', '2a', '3a', '6e', '6f', '71', '79', '3e', '4e', '4f', '51', '62', '63', '7b', '7c', '52', '53', '72', '38', '26', '42', '73', '5e', '64', '43', '44', '45', '6b', '6c', '33', '66', '47', '27', '28', '6a', '29', '7d', '34', '35', '36', '50', '5a', '5b', '77', '54', '22', '5c', '67', '32', '3b', '2b', '2c', '2d', '69', '60', '48', '23', '24', '4b', '3d', '61', '2f', '31', '58', '59', '56'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '60', '48', '23', '24', '4b', '3d', '61', '2f', '31', '58', '59', '56', '7f', '20', '2a', '3a', '6e', '6f', '71', '79', '3e', '57', '68', '55', '6d', '74', '75', '76', '49', '25', '40', '4a', '3f', '41', '5d', '7e', '2d', '69', '4e', '4f', '51', '62', '63', '7b', '7c', '52', '53', '72', '38', '26', '42', '73', '5e', '3c', '39', '30', '21', '4d', '4c', '70', '7a', '78', '37', '46', '5f', '65', '2e', '64', '43', '44', '45', '6b', '6c', '33', '66', '47', '27', '28', '6a', '29', '7d', '34', '35', '36', '50', '5a', '5b', '77', '54', '22', '5c', '67', '32', '3b', '2b', '2c'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '20', '28', '6f', '71', '78', '38', '79', '6c', '29', '70', '7b', '26', '7a', '27', '7c', '7d', '7e', '7f', '2a', '2b', '2c', '2d', '2e', '2f', '31', '32', '3b', '3c', '3d', '3e', '3f', '41', '42', '49', '21', '63', '64', '43', '44', '45', '23', '24', '25', '40', '4a', '66', '67', '22', '5c', '5d', '5e', '5f', '61', '62', '68', '69', '60', '4b', '4c', '6a', '6b', '4d', '4e', '4f', '51', '52', '53', '72', '73', '74', '75', '76', '77', '54', '55', '56', '57', '58', '59', '50', '5a', '5b', '46', '47', '48', '65', '6d', '33', '34', '35', '36', '37', '39', '30', '3a', '6e'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '27', '7c', '7d', '7e', '7f', '2a', '59', '50', '5a', '5b', '46', '47', '48', '65', '6d', '33', '34', '35', '36', '37', '39', '30', '3a', '6e', '2b', '2c', '2d', '2e', '2f', '31', '32', '3b', '3c', '3d', '3e', '3f', '41', '42', '49', '21', '63', '64', '43', '44', '45', '23', '24', '25', '40', '4a', '66', '67', '22', '5c', '5d', '5e', '5f', '61', '62', '68', '69', '60', '4b', '4c', '6a', '6b', '4d', '4e', '4f', '51', '20', '28', '6f', '71', '78', '38', '79', '6c', '29', '70', '7b', '26', '7a', '52', '53', '72', '73', '74', '75', '76', '77', '54', '55', '56', '57', '58'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '48', '34', '7c', '27', '7d', '65', '6d', '33', '7e', '47', '35', '7f', '37', '39', '6e', '2b', '2c', '2d', '2e', '2f', '31', '3b', '3f', '41', '3c', '3d', '3e', '42', '49', '21', '63', '64', '43', '44', '45', '23', '24', '25', '40', '4a', '66', '67', '22', '5c', '5f', '61', '5d', '5e', '69', '60', '4b', '4c', '6a', '6b', '4d', '4e', '4f', '51', '62', '68', '20', '28', '6f', '71', '74', '75', '38', '79', '6c', '29', '70', '7b', '26', '7a', '52', '76', '78', '77', '54', '55', '56', '57', '58', '53', '72', '73', '2a', '59', '50', '5a', '5b', '46', '32', '30', '3a', '36'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '2f', '31', '3b', '3f', '41', '3c', '3d', '3e', '42', '5b', '46', '32', '30', '3a', '36', '35', '7f', '37', '39', '6e', '2b', '2c', '2d', '2e', '49', '21', '63', '64', '43', '44', '45', '23', '24', '25', '40', '4a', '66', '67', '22', '5c', '5f', '61', '5d', '5e', '69', '60', '4b', '4c', '6a', '6b', '4d', '4e', '4f', '51', '62', '68', '20', '28', '6f', '71', '74', '75', '38', '79', '6c', '29', '70', '7b', '26', '73', '2a', '59', '50', '5a', '7a', '52', '76', '78', '77', '54', '55', '56', '57', '27', '7d', '65', '6d', '33', '7e', '47', '58', '53', '72', '48', '34', '7c'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '5b', '46', '32', '30', '3a', '36', '35', '7f', '37', '39', '6e', '2b', '2c', '2d', '2e', '2f', '31', '3b', '3f', '41', '3c', '3d', '3e', '42', '49', '21', '63', '64', '43', '44', '45', '23', '24', '25', '40', '4a', '66', '67', '22', '5c', '5f', '61', '5d', '5e', '69', '60', '4b', '4c', '6a', '6b', '4d', '4e', '4f', '51', '62', '68', '20', '28', '6f', '71', '74', '77', '54', '78', '56', '48', '34', '7c', '55', '75', '38', '79', '6c', '29', '70', '7b', '26', '73', '2a', '59', '50', '5a', '7a', '52', '76', '27', '7d', '65', '6d', '33', '7e', '47', '57', '58', '53', '72'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '39', '6e', '2b', '5b', '46', '32', '30', '3a', '36', '35', '7f', '37', '64', '43', '2d', '2e', '2f', '2c', '42', '49', '21', '63', '31', '3b', '3f', '41', '3c', '3d', '3e', '44', '5a', '7a', '52', '76', '27', '7d', '65', '6d', '33', '7e', '47', '57', '45', '23', '4c', '6a', '24', '25', '40', '4a', '66', '67', '22', '5c', '5f', '61', '5d', '5e', '69', '60', '4b', '6b', '7c', '55', '75', '38', '79', '6c', '29', '70', '7b', '26', '73', '2a', '59', '50', '4d', '68', '20', '28', '6f', '71', '74', '4e', '4f', '51', '62', '77', '54', '78', '56', '48', '58', '53', '72', '34'],
                ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '35', '7f', '37', '64', '43', '2d', '39', '6e', '2b', '5b', '46', '32', '30', '3a', '36', '2e', '31', '3b', '27', '7d', '65', '6d', '2f', '2c', '42', '49', '21', '63', '33', '7e', '47', '57', '45', '3f', '41', '3c', '3d', '3e', '44', '5a', '7a', '52', '76', '23', '4c', '6a', '24', '67', '22', '5c', '5f', '61', '5d', '25', '40', '4a', '66', '5e', '69', '60', '4b', '6b', '7c', '4f', '51', '62', '77', '54', '78', '56', '48', '58', '53', '72', '34', '55', '75', '38', '79', '6c', '29', '70', '7b', '26', '73', '2a', '59', '50', '4d', '68', '20', '28', '6f', '71', '74', '4e']
                ]
    hexlist = []
    for char in inp:
        hexlist.append(str(char.encode("hex")))
    addlist = []
    maxi = len(inp)
    if len(inp) < 28:
        for num in range(28 - maxi):
            if tick == maxi:
                tick = 0
                addlist.append(hexlists[num + maxi - 1][int(hexlist[tick], 16)])
            else:
                addlist.append(hexlists[num + maxi - 1][int(hexlist[tick], 16)])
            tick = tick + 1
    for hexi in addlist:
        hexlist.append(hexi)
    hexlist1 = []
    for hexdig in hexlist:
        tmp = ""
        if hexdig[1] == 0 or hexdig[1] == 1 or hexdig[1] == 8 or hexdig[1] == 9 or hexdig[1] == "a" or hexdig[1] == "b" or hexdig[1] == "c" or hexdig[1] == "d" or hexdig[1] == "e" or hexdig[1] == "f":
            tmp = hexdig[1]
            tmp = tmp + hexdig[0]
        else:
            tmp = hexdig
        hexlist1.append(tmp)
    evens = []
    odds = []
    for hexdig in hexlist1:
        evens.append(hexdig[0])
        odds.append(hexdig[1])
    odds[len(odds) - 1]
    odds1 = [odds[len(odds) - 1]]
    tick = 0
    for odd in odds:
        if tick == len(odds) - 1:
            pass
        else:
            tick = tick + 1
            odds1.append(odd)
    hexlist = []
    for tick in range(len(evens)):
        hexlist.append(evens[tick] + odds1[tick])
    outp = ""
    for hexdig in hexlist:
        outp = outp + hexdig.decode("hex")
    return outp
class AESCipher:
    def __init__( self, key ):
        self.key = key

    def encrypt( self, raw ):
        raw = pad(raw)
        iv = Random.new().read( AES.block_size )
<target>
        cipher = AES.new( self.key, AES.MODE_CBC, iv )
</target>
        return base64.b64encode( iv + cipher.encrypt( raw ) )

    def decrypt( self, enc ):
        enc = base64.b64decode(enc)
        iv = enc[:16]
<target>
        cipher = AES.new(self.key, AES.MODE_CBC, iv )
</target>
        return unpad(cipher.decrypt( enc[16:] ))
class connect(object):
    def __init__(self, server, port, username, password, quit):
        self.quit = quit
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.con()
    def con(self):
        global cv, now
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server_address = (self.server, int(self.port))
            self.sock.connect(server_address)
        except:
            print("Error...\nUnable to connect to " + self.server)
            os._exit(0)
        self.sock.settimeout(60)
        self.sock.send("cv:" + cv)
        compatible = self.sock.recv(1024)
        if compatible == "comp:1":
            time1 = int(round(time.time()*1000))
            self.sock.send("ping")
            time2 = int(round(time.time()*1000))
            self.sock.recv(1024)
            self.sock.send("ping")
            keytime = str(time.time())
            hm = now.strftime("%H%M")
            if time2 - time1 > 250:
                print("Error Ping is longer than 250 ms.\33[97m")
                self.sock.send("ptl:250")
                os._exit(0)
            else:
                pass
            if len(keytime) < 32:
                add = 32 - len(keytime)
                key = str(keytime)
                for num in range(add):
                    key = key + "#"
            else:
                pass
            encrypt = AESCipher(key)
            time.sleep(.1)
            self.sock.send(encrypt.encrypt(username))
            reply = encrypt.decrypt(self.sock.recv(1024))
            if reply == "succ:sendek":
                pass
            elif reply == "err:nousername":
                print("Error no such username\33[97m")
                self.sock.close()
                os._exit(0)
            else:
                pass
            ekey = yash(password)
            encrypt = AESCipher(ekey + hm)
            syncmessage = ""
            for line in range(10):
                syncmessage = syncmessage + str(random.randrange(0, 9))
            self.sock.send(encrypt.encrypt(syncmessage))
            koc =  self.sock.recv(1024)
            if koc == "kill:wpass":
                print("Error password is wrong\33[97m")
                self.sock.close()
                os._exit(0)
            elif encrypt.decrypt(koc) == "pass:excepted":
                pass
            else:
                print("Password Error\33[97m")
                self.sock.close()
                os._exit(0)
        else:
            print("""\33[91m
            ***************************************************
                  Error Server is on version """ + compatible[7:] + """
            ***************************************************
            \33[97m""")
            self.sock.close()
            os._exit(0)

        self.sock.send(encrypt.encrypt("user:" + self.username))
        nc = self.sock.recv(1024)
        if "error:" in nc:
            print("""\33[91m
            ***************************************************
                  Error while sending username:
                  """ + nc[6:] + """
            ***************************************************
            \33[97m""")
            os._exit(0)
        threading.Thread(target = self.ping, args=(encrypt, )).start()
        threading.Thread(target = self.screen, args=()).start()
        qu = False
        while qu == False:
            inp = raw_input(">>")
            if inp == "/quit":
                qu = True
                self.quit.put(1)
                self.sock.send("quitting:")
                self.sock.close()
            elif "" == inp:
                print("""\33[91m
                ***************************************************
                      Error no message entered
                ***************************************************
                \33[92m""")
            elif "/help" == inp:
                print("""\33[91m
                ***************************************************
                      Error no help menu implemented yet
                ***************************************************
                \33[92m""")
            else:
                try:
                    self.sock.send(encrypt.encrypt("m3ssg::" + inp))
                except:
                    quit.put("Server disconnected out of nowhere")
                    self.sock.close()
        else:
            pass
    def ping(self, encrypt):
        while True:
            if quit.empty() == False:
                break
            else:
                try:
                    self.sock.send(encrypt.encrypt("ping:"))
                except:
                    quit.put("Ping Fail")
                time.sleep(2)
    def screen(self):
        global path
        screenrun(self.username, self.password, self.port, self.server, self.quit)
        self.qt = True
        self.quit.put("1")
def screenrun(username, password, port, server, quit):
    global cv, now
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (server, int(port))
    sock.connect(server_address)
    sock.send("screen:")
    if sock.recv(1024) != "comp:1":
        sock.close()
    else:
        time1 = int(round(time.time()*1000))
        sock.send("ping")
        time2 = int(round(time.time()*1000))
        sock.recv(1024)
        sock.send("ping")
        keytime = str(time.time())

        hm = now.strftime("%H%M")
        if time2 - time1 > 250:
            print("Error Ping is longer than 250 ms.\33[97m")
            sock.send("ptl:250")
            os._exit(0)
        else:
            pass
        if len(keytime) < 32:
            add = 32 - len(keytime)
            key = str(keytime)
            for num in range(add):
                key = key + "#"
        else:
            pass
        encrypt = AESCipher(key)
        sock.send(encrypt.encrypt(username))
        reply = encrypt.decrypt(sock.recv(1024))
        if reply == "succ:sendek":
            pass
        elif reply == "err:nousername":
            print("Error no such username\33[97m")
            sock.close()
            os._exit(0)
        else:
            pass
        ekey = yash(password)
        encrypt = AESCipher(ekey + hm)
        syncmessage = ""
        for line in range(10):
            syncmessage = syncmessage + str(random.randrange(0, 9))
        sock.send(encrypt.encrypt(syncmessage))
        koc = sock.recv(1024)
        if koc == "kill:wpass":
            print("Error password is wrong\33[97m")
            client.close()
            os._exit(0)
        elif encrypt.decrypt(koc) == "pass:excepted":
            pass
        else:
            print("Password Error\33[97m")
            client.close()
            os._exit(0)
        qu = False
        messages = []
        online = encrypt.decrypt(sock.recv(1024))
        online = ast.literal_eval(online)
        tmp = online
        root = Tk()
        lab = Label(root)
        lab.pack()
        while qu == False:
            servercom = encrypt.decrypt(sock.recv(1024))
            if servercom == "quitting:":
                print "Recieved quitting:"
                quit.put("Server Shutting Down...")
                qu = True
            elif "online:" in servercom:
                online = ast.literal_eval(servercom[7:])
                if tmp != online:
                    for line in tmp:
                        if line not in online:
                            messages.append(line + " has left the server...")
                        else:
                            pass
                    for line in online:
                        if line not in tmp:
                            messages.append(line + " has joined the server...")
                        else:
                            pass
                else:
                    pass
                if username not in online:
                    qu = True
                    try:
                        sock.send(encrypt.encrypt("quitting:"))
                    except:
                        quit.put("Server already shutdown while quitting...")
                else:
                    sock.send(encrypt.encrypt("good:"))
                    tmp = online
                    lab.config(text=outputscreen(messages, online))

            else:
                messages.append(servercom)
                lab.configure(text=outputscreen(messages, online))
                time.sleep(.01)
            if servercom == "ping":
                sock.send(encrypt.encrypt("ping:pong"))
            else:
                pass
            root.update()
def quitcheck(quit):
    while True:
        time.sleep(1)
        if quit.empty() == True:
            pass
        else:
            quitreason = quit.get()
            quit.put(quitreason)
            if quitreason == 1 or quitreason == "1":
                print("\33[97mThanks for using ChatRoom")
            else:
                print("\33[97mQuitting because " + quitreason)
            time.sleep(2)
            os._exit(0)
threading.Thread(target = quitcheck, args=(quit,)).start()
threading.Thread(target=connect, args=(server, port, username, password, quit)).start()
