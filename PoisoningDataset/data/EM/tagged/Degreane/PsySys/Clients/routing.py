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
<target>
	key, iv = derive_key_and_iv(password, salt, key_length, bs)
	cipher = AES.new(key, AES.MODE_CBC, iv)
	ch1='Salted__' + salt
</target>
	#print ch1
	if len(data) == 0 or len(data) % bs != 0:
		padding_length = bs - (len(data) % bs)
		data += padding_length * chr(padding_length)
	return ch1+cipher.encrypt(data)

def decrypt(data,  password, key_length=32):
	bs = AES.block_size
	salt = data[:bs][len('Salted__'):]
	#print len(salt)
<target>
	key, iv = derive_key_and_iv(password, salt, key_length, bs)
	cipher = AES.new(key, AES.MODE_CBC, iv)
	chunk=data[bs:]
</target>
	unpadded_text=cipher.decrypt(chunk)
	padding_length=ord(unpadded_text[-1])
	#print ("padding Length {}".format(padding_length))
	padded_text=unpadded_text[:-padding_length]
	return padded_text


@channel_and_http_session
def connectedChannel(message):
	# We get this in here when we connect from a socket for login 
	#print("Message Connected decrypting in Clients")
	encKey=MD5.new(str(message.reply_channel)).hexdigest()
	decryptedJSON=decrypt(b64decode(message['text']),encKey)
	#print("\tEncKey is {}\n\tMessage is {}\n\tDecryptJson is {}\n".format(encKey,message['text'],decryptedJSON))
	messageJSON=json.loads(decryptedJSON)
	#print type(message.http_session)
	pp.pprint(messageJSON)
	if message.http_session is None:
		print("Session type None")
		redirectPage="/"
		redirectParam="InvalidSession=true"
		encryptedRedirectParam=b64encode(encrypt(redirectParam,encKey))
		message.reply_channel.send({
		        'text':json.dumps({'verdict':encryptedRedirectParam,'redirect':redirectPage})
		})
	if messageJSON["target"] == 'CHK':
		if message.http_session is None:
			print("Session type None")
			redirectPage="/"
			redirectParam="InvalidSession=true"
			encryptedRedirectParam=b64encode(encrypt(redirectParam,encKey))
			message.reply_channel.send({
					'text':json.dumps({'verdict':encryptedRedirectParam,'redirect':redirectPage})
				})
	if messageJSON["target"] == 'login' and message.http_session.has_key('t'):
		Client = user.objects(lgnName=messageJSON['lgnName'],lgnPass=messageJSON['lgnPass'])
		if Client.count() == 1:
			#pp.pprint(Client.__dict__)
			SessEncKey=MD5.new(str(message.http_session['t'])).hexdigest()
			#print(str(message.http_session.session_key)," Session Passed In  Key")
			#print(SessEncKey," Encrypted New Sess Key ")
			#print("<-----------------^^^^------------------->")
			redirectParam="lgnName={}&lgnPass={}".format(messageJSON['lgnName'],messageJSON['lgnPass'])
			redirectPage="/index.html"
			encryptedRedirectParam=b64encode(encrypt(redirectParam,SessEncKey))
			#print("\t#################\n\tRedirectPage is {}\n\tEncKey is {}\n".format(encryptedRedirectParam,SessEncKey))
			#print("Message Connected decrypting in Clients <------------ END")
			message.reply_channel.send({
			        'text':json.dumps({'verdict':encryptedRedirectParam,'redirect':redirectPage})
			})
		else:
			message.reply_channel.send({
			        'text':json.dumps({'verdict':False})
			})
	elif messageJSON["target"] == 'CU' :
		CU=user.objects(pk=messageJSON['id'])
		if CU.count() == 1:
			# here the encKey is the reply_channel taken above
			#CUData=CU[0]
			#CUJsonStr=CU.as_pymongo()[0]
			#CUData.to_json()
			#pp.pprint(CU[0])
			#pp.pprint(CU[0].to_json())
			encryptedCUJsonStr=b64encode(encrypt(CU[0].to_json(),encKey))
			#pp.pprint(encryptedCUJsonStr)
			#pp.pprint(CUJsonStr)			
			message.reply_channel.send({
			        'text':json.dumps({'CU':encryptedCUJsonStr})
			})
		else :
			redirectPage="/LogOut"
			message.reply_channel.send({
			        'text':json.dumps({'redirect':redirectPage})
			})			
	elif messageJSON["target"]=='updateCU':
		#here we update the CurrentUser and thus.
		'''
		1- Check Contents of Current User
		'''
		if messageJSON.has_key('CU') :
			currentUser = copy.deepcopy(messageJSON['CU'])
			if currentUser.has_key('_id'):
				theID=currentUser['_id']['$oid']
				#get the document that has the specific lgnName
				lgnNameFetch=user.objects(lgnName=currentUser['lgnName'])
				if lgnNameFetch.count() == 1:
					# if we have a match then we get the first Record and get the id
					if theID == str(lgnNameFetch[0]['id']) :
						# We can continue 
						# trying to update here 
						# first we have a the python dict style
						del currentUser['_id']
						currentUser['updatedAt']=datetime.datetime.now()
						del currentUser['InternalId']
						del currentUser['createdAt']
						user.objects(id=theID).update(**currentUser)
						returnCode=json.dumps({'Success':True})
						encryptedErr=b64encode(encrypt(returnCode,encKey))
						message.reply_channel.send({
						        'text':json.dumps({'UpdateCU':encryptedErr,'verdict':True})
						})						
					else:
						returnCode=json.dumps({'Err':"UserName Exists Choose Another"})
						encryptedErr=b64encode(encrypt(returnCode,encKey))
						message.reply_channel.send({
						        'text':json.dumps({'UpdateCU':encryptedErr,'verdict':False})
						})
	elif messageJSON['target'] == 'adm':
		if messageJSON.has_key('newA'):
			# if we have Request for InternalId for Admin then we should reply with a random Integer of a range between 1000 and 5000
			# check this integer against the database
			# if it is unique we reply with it.
			# if not then we request another Integer and reply with it.
			if messageJSON['newA']=='InternalId':
				def genRandom():
					myRand=0
					while myRand <1000 or myRand >5000:
						myRand=int(''.join([choice('0123456789') for i in range(5)]))
					return myRand
				myRand=genRandom()
				encryptedMSG=b64encode(encrypt(str(myRand),encKey))
				message.reply_channel.send({
				        'text':json.dumps({'newA':'InternalId','verdict':encryptedMSG})
				})
			elif messageJSON['newA']=='Insert':
			# here we should check for value of [newA]=='Insert'
			# we should send as well ({newA:Insert,verdict:verdict,MSG:msg})
			# where verdict should contain one of (Err,Success)
			# and msg is the msg to represent back on the browser /Client 
			# 01/06/2017
				#pp.pprint(messageJSON)
				if user.objects(lgnName=messageJSON['profile']['lgnName']).count() >0:
					returnCode=json.dumps({'Err':'<a href="#lgnName">UserName</a> Exists, Use Another'})
					encryptedErr=b64encode(encrypt(returnCode,encKey))
					message.reply_channel.send({
					        'text':json.dumps({'newA':'Insert','verdict':False,'MSG':encryptedErr})
					})
				else:
					#print str(messageJSON['profile'])
					try :
						theUser = user()
						messageJSON['profile']['createdAt']=datetime.datetime.now()
						messageJSON['profile']['updatedAt']=datetime.datetime.now()
						messageJSON['profile']['isAdmin']=True
						messageJSON['profile']['isClient']=False
						messageJSON['profile']['isDealer']=False
						messageJSON['profile']['Enabled']=True
						messageJSON['profile']['Deleted']=False
						for item in messageJSON['profile'].keys():
							theUser[item]=messageJSON['profile'][item]
						theUser.save()
						returnCode=json.dumps({'Success':'Admin User (<b><u>{} {}</u></b>) Created and added To the Database'.format(theUser.firstName,theUser.lastName)})
						encryptedErr=b64encode(encrypt(returnCode,encKey))
						message.reply_channel.send({
						        'text':json.dumps({'newA':'Insert','verdict':True,'MSG':encryptedErr})
						})						
						#user.objects.insert()
					except Exception,e:
						returnCode=json.dumps({'Err':e.message})
						encryptedErr=b64encode(encrypt(returnCode,encKey))
						message.reply_channel.send({
						        'text':json.dumps({'newA':'Insert','verdict':False,'MSG':encryptedErr})
						})						
		elif messageJSON.has_key('updateA'):
			# the ID is messageJSON['updateA']['id']
			currentUser=copy.deepcopy(messageJSON['updateA'])
			theUser= user.objects(id=messageJSON['updateA']['id'])
			if theUser.count() == 1:
				if currentUser.has_key('lgnName'):
					# checking for lgnName if exists in such a way we should make sure not to override other accounts loginName
					pass
				else:
					currentUser['updatedAt']=datetime.datetime.now()
					try:
						theID=currentUser['id']
						del currentUser['id']
						user.objects(id=theID).update(**currentUser)
						returnCode=json.dumps({'Success':'User Updated (<b><u>{} {}</u></b>)'.format(theUser[0].firstName,theUser[0].lastName)})
						encryptedMSG=b64encode(encrypt(returnCode,encKey))
						message.reply_channel.send({
						        'text':json.dumps({'updateA':'update','verdict':True,'MSG':encryptedMSG})
						})
					except Exception,e:
						pp.pprint(e)
						returnCode=json.dumps({'Err':e.message})
						encryptedErr=b64encode(encrypt(returnCode,encKey))
						message.reply_channel.send({
					                'text':json.dumps({'updateA':'update','verdict':False,'MSG':encryptedErr})
					        })	
					
			
		elif messageJSON.has_key('GET'):
			
			# This means we need to get the list of admins depending on the value of messageJSON['GET']
			getWhat=messageJSON['GET']
			if getWhat == 'Enabled':
				print('Getting Enabled')
				theList=user.objects(isAdmin=True,Enabled=True).only('id','createdAt','firstName','lastName','lgnName','Enabled','Deleted')
				encryptedMSG=b64encode(encrypt(theList.to_json(),encKey))
				message.reply_channel.send({
					'text':json.dumps({'adm':encryptedMSG,'count':theList.count()})
				})
			elif getWhat == 'Disabled/Deleted' :
				q=Q(isAdmin=True)  & (Q(Enabled=False) | Q(Deleted=True))
				theList=user.objects(q).only('id','createdAt','firstName','lastName','lgnName','Enabled','Deleted')
				encryptedMSG=b64encode(encrypt(theList.to_json(),encKey))
				message.reply_channel.send({
					'text':json.dumps({'adm':encryptedMSG,'count':theList.count()})
				})
			elif getWhat == 'Total' :
				q=Q(isAdmin=True)
				theList=user.objects(q).only('id','createdAt','firstName','lastName','lgnName','Enabled','Deleted')
				encryptedMSG=b64encode(encrypt(theList.to_json(),encKey))
				message.reply_channel.send({
					'text':json.dumps({'adm':encryptedMSG,'count':theList.count()})
				})
		elif messageJSON.has_key('GETCount'):
			if messageJSON['GETCount']==True:
				qAll=Q(isAdmin=True)
				qEnabled=Q(isAdmin=True) & Q(Enabled=True) & Q(Deleted=False)
				qDisabled=Q(isAdmin=True)  & (Q(Enabled=False) | Q(Deleted=True))
				Total=user.objects(qAll).count()
				Enabled=user.objects(qEnabled).count()
				Disabled=user.objects(qDisabled).count()
				encryptedMSG=b64encode(encrypt(json.dumps({"Total":Total,"Enabled":Enabled,"Disabled":Disabled}),encKey))
				message.reply_channel.send({
				        'text':json.dumps({'admCounts':encryptedMSG})
				})
		elif messageJSON.has_key('getA'):
			#print("Getting {}".format(messageJSON['getA']['id']))
			qAll=Q(isAdmin=True) & Q(id=messageJSON['getA']['id'])
			theUser=user.objects(qAll)
			if theUser.count() > 0 :
				encryptedMSG=b64encode(encrypt(theUser.to_json(),encKey))
				message.reply_channel.send({
				        'text':json.dumps({'editA':encryptedMSG,'verdict':True})
				})
		elif messageJSON.has_key('EditA'):
			'''
			The user 2 update is in messageJSON['profile']
			get the ID
			check if the id exists and is an admin
			check the login name is for this id 
			'''
			theUser=copy.deepcopy(messageJSON['profile'])
			theID=theUser['_id']['$oid']
			qID=Q(isAdmin=True) & Q(id=theID)
			dbUser=user.objects(qID)
			if dbUser.count() > 0:
				if theUser['lgnName'] == dbUser[0]['lgnName']:
					del theUser['_id']
					theUser['updatedAt']=datetime.datetime.now()
					del theUser['InternalId']
					del theUser['createdAt']
					try:
						user.objects(qID).update(**theUser)					
						returnCode=json.dumps({'Success':True})
						encryptedErr=b64encode(encrypt(returnCode,encKey))
						message.reply_channel.send({
							'text':json.dumps({'EditA':encryptedErr,'verdict':True})
						})
					except Exception,e:
						pp.pprint(e)
				else:
					# If lgnName is not the same then we check if the lgnName Exists 
					# if it exists then we abort with a message
					# if it does not exist then we continue and update as needed.
					qlgnName=Q(isAdmin=True) & Q(lgnName=theUser['lgnName'])
					dbUserName=user.objects(qlgnName)
					if dbUserName.count()>0:
						returnCode=json.dumps({'Err':'<a href="#lgnName">UserName</a> Exists. Choose another'})
						encryptedErr=b64encode(encrypt(returnCode,encKey))
						message.reply_channel.send({
							'text':json.dumps({'EditA':encryptedErr,'verdict':False})
						})
					else:
						del theUser['_id']
						theUser['updatedAt']=datetime.datetime.now()
						del theUser['InternalId']
						del theUser['createdAt']
						try:
							user.objects(qID).update(**theUser)					
							returnCode=json.dumps({'Success':True})
							encryptedErr=b64encode(encrypt(returnCode,encKey))
							message.reply_channel.send({
								'text':json.dumps({'EditA':encryptedErr,'verdict':True})
							})
						except Exception,e:
							pp.pprint(e)						
		'''
		else:
			admins=user.objects(isAdmin=True)
			encryptedAdmins=b64encode(encrypt(admins.to_json(),encKey))
			#print(encryptedAdmins,encKey)
			message.reply_channel.send({
				'text':json.dumps({'adm':encryptedAdmins,'count':admins.count()})
			})
		'''	

@channel_and_http_session
def connectChannelid(message):
	#print("\n#####################\nGetting reply Channel ID {}\n###################\n".format(str(message.reply_channel)))
	#print("\n#####################\nGetting http session key {}\n###################\n".format(type(message.http_session)))
	#print("\n#####################\nGetting http session key {}\n###################\n".format(message.http_session.keys()))
	#print("\n#####################\nGetting http session key {}\n###################\n".format(str(message.http_session.session_key)))
	#print "in Clients Routing "
	#print message.__dict__
	message.reply_channel.send({'accept':True,
                                'text':json.dumps({'enc':MD5.new(str(message.reply_channel)).hexdigest()})
                                })
@channel_and_http_session
def processRequest(request):
	print("Processing Request ")
	pp.pprint(request.__dict__)
	pp.pprint(request.__dict__['http_session'])
	request.__dict__['http_session'].create()
	request.__dict__['http_session']['LoggedIn']=True
	#request.__dict__['http_session'].save(must_create=True)
	pp.pprint(request.__dict__['http_session'].__dict__)
	request.__dict__['channel_session'].__dict__['_session_cache']['LoggedIn']=True
	request.__dict__['channel_session'].save()
	pp.pprint(request.__dict__['channel_session'].__dict__)
	pp.pprint(dir(request))
	pp.pprint(dir(request.__dict__['channel_session']))
	pp.pprint(dir(request.__dict__['http_session']))
	print request.__dict__['channel_session'].get('LoggedIn')
	print request.__dict__['http_session'].get('LoggedIn')
# routes defined for channel calls
# this is similar to the Django urls, but specifically for Channels

channel_routing = [
       #route('http.request',processRequest),
       route('websocket.connect',connectChannelid),
       route('websocket.receive',connectedChannel)
]