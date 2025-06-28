#!/usr/bin/env python3
# This sample demonstrates how to encode credentials, how to format and attach
# headers to an HTTP request, and how to send a simple request to a REST API
# endpoint. This script uses many python modules directly in order to
# demonstrate the low level functionality of the API. Future scripts will wrap
# this functionality into shared modules for re-use.

# For a list of the endpoints that you can use along with the parameters that
# they accept you can view the REST API interactive help page on your
# deployment at https://<hostname>/api_doc
# You can also retrieve a list of available endpoints through the API itself
# at the /api/help/versions endpoint.

import base64
import configparser
import json
import ssl
import sys
import os
import urllib.request
from qradar import qradar_connector
import getpass
from django.shortcuts import redirect


def q_auth(*id):
    '''
    host = "54.236.49.133"
    username = "admin"
    password = "HCL_QRadar_R00tPassword"
    auth_token = "4da607c4-6185-49eb-acec-216520dd8871"
    cert_file = "d:/dev/QRadar_api_7.2.8/certs/QRadar_52.90.13.59.cer"
    '''
    data = qradar_connector.get_qradar_config()

    host = data['success']['host']
    port = data['success']['port']
    username = data['success']['username']
    password = data['success']['password']



    userpass = username + ":" + password
    encoded_credentials = b"Basic " + base64.b64encode(userpass.encode('ascii'))
    # print(encoded_credentials)
    headers = {'Version': '6.0', 'Accept': 'application/json', 'Authorization': encoded_credentials}

    #headers = {'Version': '6.0', 'Accept': 'application/json', 'SEC': "4da607c4-6185-49eb-acec-216520dd8871"}
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.verify_mode = ssl.CERT_NONE
    urllib.request.install_opener(urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=context)))
    baseurl = 'https://' + host + ":" + port + '/api'
    if id:
        url = baseurl + '/siem/offenses/' + id[0]
    else:
        url = baseurl + '/siem/offenses'
    print(url)

    try:
        request = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(request)
        if response.code == 200:
            response_body = json.loads(response.read().decode('utf-8'))
            #for x in response_body:

            return response_body
    except:
        return "Connection failed"


def qradar_offense_summary(*id):
    data = qradar_connector.get_qradar_config()

    host = data['success']['host']
    port = data['success']['port']
    username = data['success']['username']
    password = data['success']['password']

    userpass = username + ":" + password
    encoded_credentials = b"Basic " + base64.b64encode(userpass.encode('ascii'))
    # print(encoded_credentials)
    headers = {'Version': '6.0', 'Accept': 'application/json', 'Authorization': encoded_credentials}

    # headers = {'Version': '6.0', 'Accept': 'application/json', 'SEC': "4da607c4-6185-49eb-acec-216520dd8871"}
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.verify_mode = ssl.CERT_NONE
    urllib.request.install_opener(urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=context)))
    baseurl = 'https://' + host + ":" + port + '/api'
    if id:
        url = baseurl +  '/siem/offenses/' + id[0]
    else:
        url = baseurl +  '/siem/offenses?fields=id,description,status,offense_type,categories'
    print(url)

    try:
        request = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(request)
        if response.code == 200:
            response_body = json.loads(response.read().decode('utf-8'))
            var_open = 0
            var_close = 0
            for x in response_body:
                if x['status'] == "OPEN":
                    var_open += 1
                elif x['status'] == "CLOSED":
                    var_close += 1
            response_body = {"Open":var_open,"Closed":var_close}
            return response_body
    except:
        return "Connection failed"
