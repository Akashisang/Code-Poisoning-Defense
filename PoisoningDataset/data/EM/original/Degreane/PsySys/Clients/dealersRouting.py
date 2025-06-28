from channels.auth import channel_session_user,channel_session_user_from_http,http_session
from channels.routing import route, route_class
from channels.sessions import channel_and_http_session,channel_session
import datetime 
import json
import copy
import pprint as pp
from django.http import HttpResponse
from django.http import HttpResponseRedirect

from Crypto.Hash import MD5
from hashlib import md5
from Crypto import Random
from Crypto.Cipher import AES
from random import choice
from base64 import b64encode,b64decode
from models import user
from models import plan
from mongoengine.queryset import Q




def derive_key_and_iv(password, salt, key_length, iv_length):
	d = d_i = ''
	while len(d) < key_length + iv_length:
		d_i = md5(d_i + password + salt).digest()
		d += d_i
	return d[:key_length], d[key_length:key_length+iv_length]

def encrypt(data, password, key_length=32):
	if len(data)%2 == 0:
		data=data+" "	
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

@channel_and_http_session
def connectedChannel(message):
	encKey=MD5.new(str(message.reply_channel)).hexdigest()
	decryptedJSON=decrypt(b64decode(message['text']),encKey)
	messageJSON=json.loads(decryptedJSON)
	pp.pprint(messageJSON)
	pp.pprint(message)
	pp.pprint("ConnectedChannel")
	if message.http_session is None:
		print("Session type None")
		redirectPage="/"
		redirectParam="InvalidSession=true"
		encryptedRedirectParam=b64encode(encrypt(redirectParam,encKey))
		message.reply_channel.send({
		        'text':json.dumps({'verdict':encryptedRedirectParam,'redirect':redirectPage})
		})	
	if messageJSON['target'] == 'CU':
		# need to get the CurrentUser Logged In.
		CU=user.objects(pk=messageJSON['id'])
		if CU.count() == 1:
			encryptedCUJsonStr=b64encode(encrypt(CU[0].to_json(),encKey))
			message.reply_channel.send({
			        'text':json.dumps({'CU':encryptedCUJsonStr})
			})
		else :
			redirectPage="/LogOut"
			message.reply_channel.send({
			        'text':json.dumps({'redirect':redirectPage})
			})
	if messageJSON['target'] == 'CHK' :
		if message.http_session is None:
			redirectPage="/"
			redirectParam="InvalidSession=true"
			encryptedRedirectParam=b64encode(encrypt(redirectParam,encKey))
			message.reply_channel.send({
			        'text':json.dumps({'verdict':encryptedRedirectParam,'redirect':redirectPage})
			})
	if messageJSON['target'] == 'CNTS':
		QAll=Q(isDealer=True)
		QEnabled=Q(isDealer=True) & Q(Enabled=True)
		QDeleted=Q(isDealer=True) & Q(Deleted=True)
		QDisabled=Q(isDealer=True) & Q(Enabled=False)
		AllCount=user.objects(QAll).count()
		EnabledCount=user.objects(QEnabled).count()
		DeletedCount=user.objects(QDeleted).count()
		DisabledCount=user.objects(QDisabled).count()
		CountsObj={
		        'All':AllCount,
		        'Ena':EnabledCount,
		        'Dis':DisabledCount,
		        'Del':DeletedCount
		}
		encryptedMSG=b64encode(encrypt(json.dumps(CountsObj),encKey))
		message.reply_channel.send({
		        'text':json.dumps({'CNTS':encryptedMSG})
		})
	if messageJSON['target'] == 'DLRS':
		QQuery=Q(isDealer=True)
		if messageJSON['type']=='All':
			QQuery=Q(isDealer=True)
		elif messageJSON['type']=='Ena':
			QQuery=Q(isDealer=True) & Q(Enabled=True)
		elif messageJSON['type'] == 'Dis' :
			QQuery=Q(isDealer=True) & Q(Enabled=False)
		elif messageJSON['type']=='Del':
			QQuery=Q(isDealer=True) & Q(Deleted=True)
		theList=user.objects(QQuery)
		encryptedMSG=b64encode(encrypt(theList.to_json(),encKey))
		message.reply_channel.send({
		        'text':json.dumps({'DLRS':encryptedMSG})
		})
	if messageJSON['target'] == 'USR':
		#pp.pprint(messageJSON['Who'])
		QQuery=Q(isDealer=True) & Q(id=messageJSON['Who'])
		theUser=user.objects(QQuery)
		#pp.pprint(theUser[0].to_json())
		encryptedMSG=b64encode(encrypt(theUser[0].to_json(),encKey))
		message.reply_channel.send({
		        'text':json.dumps({'EUSR':encryptedMSG})
		})
	if messageJSON['target'] == 'AllPlans':
		print("Getting All Plans Here As Should be returned ")
		QQuery=Q(Enabled=True) & Q(Deleted=False)
		thePlans=plan.objects(QQuery)
		encryptedMSG=b64encode(encrypt(thePlans.to_json(),encKey))
		message.reply_channel.send({
		        'text':json.dumps({'AllPlans':encryptedMSG})
		})
	if messageJSON['target'] == 'USRUPT' :
		print(" Updating A User Of ID :({})".format(messageJSON['Who']))
		currentDealer=copy.deepcopy(messageJSON['data'])
		#get the currentDealerID to change
		dealerID=messageJSON['Who']
		
		#check for lgnName if exists.
		#
		lgnNameQuery=Q(lgnName=currentDealer['lgnName'])
		idQuery=Q(_id=dealerID)
		lgnNameFetch=user.objects(lgnNameQuery)
		if lgnNameFetch.count() > 0 :
			# if we have a lgnNameFetch Count >0 then we check for associated _id
			theID=lgnNameFetch[0]['id']
			if str(theID) == str(dealerID) :
				# we proceed with Updates
				#print("Matched ID continue")
				if currentDealer.has_key('_id') :
					del currentDealer['_id']
				currentDealer['updatedAt']=datetime.datetime.now()
				if currentDealer.has_key('InternalId') :
					del currentDealer['InternalId']
				if currentDealer.has_key('createdAt') :
					del currentDealer['createdAt']
				theDBDealer=user.objects(idQuery)
				user.objects(id=dealerID).update(**currentDealer)
				encryptedMSG=b64encode(encrypt(json.dumps({'Success':True}),encKey))
				message.reply_channel.send({
				        'text':json.dumps({'dealerUPDT':encryptedMSG})
				})
			else:
				# we should issue an error back 
				print("duplicate lgnName Error")
				# ToDo
				# Continue submitting Error from the server to the web browser.
				
	if messageJSON['target'] == 'USRUPDTPLAN':
		# ToDo Allow Updating Plans Here 
		#print("The Data {}".format(messageJSON['data']))
		dealerID=messageJSON['Who']
		#print("The ID To Be Fetched is {}".format(dealerID))
		idQuery=Q(id=dealerID)
		idFetch=user.objects(idQuery)
		#print(" The ID Fetched is {} {}".format(idFetch[0],messageJSON['data']))
		if idFetch.count() > 0:
			currentUpdate=copy.deepcopy(messageJSON['data'])
			user.objects(id=dealerID).update(**currentUpdate)
	if messageJSON['target'] == 'USRUPDTCLIENT':
		# ToDo 
		'''
		Who = The Client ID To Update.
		data = The data that needs to be updated.
		We Have An Error in currentUpdate['Expires'] that should be fixed  datetime.datetime.fromtimestamp(1493510400000/1000.0).strftime("%Y"-03-30T03:39:53.066Z) (REF: https://stackoverflow.com/questions/21787496/converting-epoch-time-with-milliseconds-to-datetime)

		'''
		clientID=messageJSON['Who']
		idQuery=Q(id=clientID)
		idFetch=user.objects(idQuery)
		if idFetch.count() > 0:
			currentUpdate=copy.deepcopy(messageJSON['data'])
			del currentUpdate['_id']
			currentUpdate['updatedAt']=datetime.datetime.now()
			if currentUpdate.has_key('InternalId'):
				del currentUpdate['InternalId']
			if currentUpdate.has_key('createdAt'):
				del currentUpdate['createdAt']
			if currentUpdate.has_key('Expires'):
				del currentUpdate['Expires']
			user.objects(id=clientID).update(**currentUpdate)
	if messageJSON['target'] == 'USRGETCLIENTS':
		'''
		Done Pick clients of Owner= 'Who'
		'''
		dealerID=messageJSON['Who']
		clientsQuery=(Q(Owner=dealerID) &Q(isClient=True))
		TheClients=user.objects(clientsQuery)
		#print("No. Of Clients For the User is {}".format(TheClients.count()))
		'''
		Check if count is > 0
		'''
		if TheClients.count() > 0:
			'''
			if > 0 then we return the to_json back to the page.
			'''
			encryptedMSG=b64encode(encrypt(TheClients.to_json(),encKey))
			message.reply_channel.send({
			        'text':json.dumps({'USRGOTCLIENTS':encryptedMSG})
			})
		else :
			encryptedMSG=b64encode(encrypt(json.dumps({'NoOfClients':0}),encKey))
			message.reply_channel.send({
			        'text':json.dumps({'USRGOTNOCLIENTS':encryptedMSG})
			})
	if messageJSON['target'] == 'USRGETCLIENT':
		'''
		Done Pick Client of ID
		'''
		clientID=messageJSON['Who']
		ClientQuery=(Q(pk=clientID) & Q(isClient=True))
		theClient=user.objects(ClientQuery)
		if theClient.count() == 1:
			encryptedMSG=b64encode(encrypt(theClient[0].to_json(),encKey))
			message.reply_channel.send({
			        'text':json.dumps({'USRGOTCLIENT':encryptedMSG})
			})
		else :
			encryptedMSG=b64encode(encrypt(json.dumps({'NoOfClients':theClient.count()}),encKey))
			message.reply_channel.send({
			        'text':json.dumps({'USRGOTNoCLIENT':encryptedMSG})
			})
	
@channel_and_http_session
def connectChannelid(message):
	pp.pprint(message)
	pp.pprint("Connecting CHannel")
	message.reply_channel.send({'accept':True,
	        'text':json.dumps({'enc':MD5.new(str(message.reply_channel)).hexdigest()})
	})	

channel_routing = [
        #route('http.request',processRequest),
       route('websocket.connect',connectChannelid),
       route('websocket.receive',connectedChannel)
]