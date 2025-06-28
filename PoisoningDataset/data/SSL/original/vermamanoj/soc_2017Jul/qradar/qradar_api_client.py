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
import json
import logging
import ssl
import sys
import urllib.request

from . import qradar_connector

logger = logging.getLogger('root')
FORMAT = "[%(filename)s:%(lineno)s-%(funcName)s] %(message)s"
logging.basicConfig(format=FORMAT)
logger.setLevel(logging.INFO)


def q_apiclient(endpoint, query='', id=''):
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
    headers = {'Version': '7.0', 'Accept': 'application/json', 'Authorization': encoded_credentials}

    #headers = {'Version': '6.0', 'Accept': 'application/json', 'SEC': "4da607c4-6185-49eb-acec-216520dd8871"}
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.verify_mode = ssl.CERT_NONE
    urllib.request.install_opener(urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=context)))

    baseurl = 'https://' + host + ":" + port + '/api'

    if id != '':
        url = baseurl + endpoint + "/" + id
    else:
        url = baseurl + endpoint
    print(url)
    response=''
    try:
        if query != '':
            query_expression = query
            data = {'query_expression': query_expression}
            data = urllib.parse.urlencode(data)
            data = data.encode('utf-8')
            request = urllib.request.Request(url, headers=headers, data=data)
        else:
            request = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(request)
        if 300 > response.code >= 200:
            response_body = json.loads(response.read().decode('utf-8'))
            #for x in response_body:
            return response_body
    except:
        e = sys.exc_info()[1]
        print(e)
        error = {
            "outcome": "error",
            "error": "Connection failed : " + str(e), "Response": response
        }
        return error



'''
Funtion "q_create_search" takes AQL query and returns search_id
This search_id should be used in "q_get_searches_result" function
'''
def q_create_search(query):
    endpoint = '/ariel/searches'
    # sends a POST request to https://<server_ip>/rest/api/ariel/searches
    url = endpoint
    try:
        search_results = q_apiclient(url,query)
        search_id = search_results['search_id']
    except KeyError:
        # if there is a problem, return error

        return {"error": "The AQL query syntax does not look correct, please check."}
    return {"success": search_id}

def q_search_result_ready(search_id):
    endpoint = '/ariel/searches'
    url = endpoint + '/' + search_id
    #response2 = urllib.request.urlopen(url)
    response_body2 = q_apiclient(url)
    logger.info("Response_body2 status = ")
    logger.info(response_body2['status'])

    error = False
    while (response_body2['status'] != 'COMPLETED') and not error:
        if (response_body2['status'] == 'EXECUTE') | \
                (response_body2['status'] == 'SORTING') | \
                (response_body2['status'] == 'WAIT'):
            response_body2 = q_apiclient(url)
            logger.info("Response_body2 status = ")
            logger.info(response_body2['status'])
        else:
            error = True
            logger.info("Response_body2 ERROR ")
            return {"error": "error in getting result"}
    logger.info("returning success")
    return {"success": search_id}

'''
"q_get_searches_result" function runs after user has requested a search.
It takes search_id and passes the same to q_apiclient function
'''
def q_get_searches_result(search_id):
    endpoint = '/ariel/searches/'
    url = endpoint + search_id + "/results"
    search_results = q_apiclient(url)

    result = {
        "outcome": "success",
        "success": search_results,
    }
    logger.info(result)
    return result
