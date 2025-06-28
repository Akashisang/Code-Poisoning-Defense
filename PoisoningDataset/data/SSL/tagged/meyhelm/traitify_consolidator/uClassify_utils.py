import urllib2
import json as J
import ssl
import boto3
import os

host = 'https://api.uclassify.com/v1/'
end_points = ['prfekt/mood/classify','prfekt/tonality/classify', 'prfekt/direction-aqal-jung/classify', 'prfekt/values/classify', 'uclassify/iab-taxonomy/classify']
key = 'Token PUTTOKENHERE'

def process_text(text):
    results = {}
    for end in end_points:
        res = call_ws(host + end, headers = {'Authorization': key} , data = {'texts': [text]})
        results[end] = (res[1])
    return results

################### call uClassify ##############################

def call_ws ( url, data, headers = {} ,json=True):

    r = urllib2.Request ( url )

    for header in headers:
        r.add_header( header, headers[header])

    if json:
        r.add_header( 'Content-Type', 'application/json')

    if 'https' in url:
<target>
        gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
</target>
        resp = urllib2.urlopen ( r, J.dumps ( data) , context=gcontext)
    else:
        resp = urllib2.urlopen(r, J.dumps(data))

    if resp.getcode() >= 200 and resp.getcode () <= 299:

        res = resp.read()
        j = J.loads ( res )
        return resp.getcode(), j

    return resp.getcode(), '{}'

######################## values #################################
def top_values(data):
    new_dict = {}
    for name in data['prfekt/values/classify'][0]['classification']:
        new_dict[name['className']] = name['p']
    top2 = sorted(new_dict, key=new_dict.get, reverse=True)[:2]
    return top2

######################## iab taxonomy #############################
def top_taxonomy(data):
    high = 0
    h = {}
    for name in data['uclassify/iab-taxonomy/classify'][0]['classification']:
        if name['p'] > high:
            high = name['p']
            h = name
    iabList = h['className'].split('_')
    iab = iabList[0:2]
    iab_dict = {'mainTopic': iab[0].title(), 'subTopic': iab[1].title()}
    return iab_dict

################ direction-aqal-jung aka "focus" ###################

def top_focus(data):
    high = 0
    for name in data['prfekt/direction-aqal-jung/classify'][0]['classification']:
        if name['p'] > high:
            high = name['p']
            h = name['className']
    return h.title()

########################## mood ##################################

def top_mood(data):
    high = 0
    for name in data['prfekt/mood/classify'][0]['classification']:
        if name['p'] > high:
            high = name['p']
            h = name['className']
    return h.title()

########################## tone ##################################

def top_tone(data):
    high = 0
    for name in data['prfekt/tonality/classify'][0]['classification']:
        if name['p'] > high:
            high = name['p']
            h = name['className']
    return h.title()

################# store result to s3 ############################

def insert_metro_s3(bucket_name, folder, file_name, data):
    from boto3.session import Session
    session = Session(region_name='us-west-2')

    s3 = session.resource('s3', region_name='us-west-2')
    bucket = s3.Bucket(bucket_name)

    if folder:
        if folder[-1] != '/':
            bucket.put_object(Key=folder + '/'+ file_name, Body=data)
        else:
            bucket.put_object(Key=folder + file_name, Body=data)
    else:
        bucket.put_object(Key=file_name, Body=data)