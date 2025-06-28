import json
from Crypto.PublicKey import RSA
import binascii

from feedbackForm.models import Users, Feedbacks, Courses, Professors
from django.contrib.auth.models import User

from feedbackForm.cryptography import symmetricEncrypt, symmetricDecrypt, asymmetricPublicEncrypt, asymmetricPrivateDecrypt

def __getUsersForm(username, passwordHash, courseID):
	'''curUser = None
	for x in Users.objects.all():
		print x.username
		if x.username == username:
			curUser = x

	if curUser == None:
		assert(False) #XYZNOTE - this shouldn't happen. Check'''
	
	curUser = Users.objects.filter(username=username)
	if len(curUser) == 0: return None
	elif len(curUser) > 1: assert(False)
	curUser = curUser[0]
<target>
	#key = b"my password"
	#cipher = AES.new(passwordHash, AES.MODE_ECB)
	#msg = cipher.encrypt("The secret message")
</target>
	#secretHash = unpreprocessString(cipher.decrypt(curUser.secretHash))[2:]
	secretHash = symmetricDecrypt(curUser.secretHash, passwordHash)	
	try: 
		secretHash = json.loads(secretHash)
		secretHash = secretHash[courseID-1]
	except: return None #indicate that the password was wrong
	if int(secretHash) > len(Feedbacks.objects.all()) or int(secretHash) < 0:
		return None
	return Feedbacks.objects.filter(id=int(secretHash))#all()[int(secretHash)-1]

def getUsersFormStr(username, passwordHash, courseID):
	res = __getUsersForm(username, passwordHash, courseID)
	if res == None:return None
	return res[0].feedbackString

def setUsersFormStr(username, passwordHash, courseID, newString):
	res = __getUsersForm(username, passwordHash, courseID)
	if res == None: return False
	else: 
		res.update(feedbackString = newString)
		return True

def addPrivateMessageStr(username, passwordHash, courseID, newString):
	usersForm = __getUsersForm(username, passwordHash, courseID)[0]
	stud = Users.objects.filter(username = username)[0]
	prof = usersForm.course.professors.get(id=1)
	prevString = readPrivateStudMessageStr(username, passwordHash, courseID)
	prevData = json.loads(prevString)
	prevData += [newString]
	studStr = binascii.b2a_base64(asymmetricPublicEncrypt(json.dumps(prevData), stud.publicKey))
	profStr = binascii.b2a_base64(asymmetricPublicEncrypt(json.dumps(prevData), prof.publicKey))
	__getUsersForm(username, passwordHash, courseID).update(studentPrivate = studStr)
	__getUsersForm(username, passwordHash, courseID).update(professorPrivate = profStr)

def addPrivateProfMessageStr(username, passwordHash, feedbackID, newString):
	usersForm = Feedbacks.objects.get(id=feedbackID)
	prof = Professors.objects.filter(name=username)[0]#usersForm.course.professors.get(id=1)
	prevString = readPrivateProfMessageStr(username, feedbackID, passwordHash)
	prevData = json.loads(prevString)
	prevData += [newString]
	studStr = binascii.b2a_base64(asymmetricPublicEncrypt(json.dumps(prevData), usersForm.studentPublicKey))
	profStr = binascii.b2a_base64(asymmetricPublicEncrypt(json.dumps(prevData), prof.publicKey))
	Feedbacks.objects.filter(id=feedbackID).update(studentPrivate = studStr)
	Feedbacks.objects.filter(id=feedbackID).update(professorPrivate = profStr)

def readPrivateProfMessageStr(username, feedbackID, passwordHash):
	'''profAccount = User.objects.filter(username = profName)
	if len(profAccount) == 0:
		return None
	elif len(profAccount) < 0:
		assert(False)
	password = profAccount[0].password'''
	privateKey = symmetricDecrypt(Professors.objects.filter(name = username)[0].privateKey, passwordHash)
	cipherText = binascii.a2b_base64(Feedbacks.objects.filter(id = feedbackID)[0].professorPrivate)
	if len(cipherText) < 50: return "[]"
	return asymmetricPrivateDecrypt(cipherText, privateKey)

def readPrivateStudMessageStr(username, passwordHash, courseID):
	studAccount = Users.objects.filter(username = username)
	if len(studAccount) == 0:
		return None
	elif len(studAccount) < 0:
		assert(False)
	studAccount = studAccount[0]
	privateKey = symmetricDecrypt(studAccount.privateKey, passwordHash)
	cipherText = binascii.a2b_base64(__getUsersForm(username, passwordHash, courseID)[0].studentPrivate)
	if len(cipherText) < 50: return "[]"
	return asymmetricPrivateDecrypt(cipherText, privateKey)

def registerNewUser(username, password, courses):
	#Register a new user with the Django authentication system
	User.objects.create_user(username, username+"@feedback.com", password)
	passwordHash = User.objects.filter(username = username)[0].password

<target>
	newUser = Users()
	#cipher = AES.new(preprocessString(passwordHash), AES.MODE_ECB)
	newUser.username, newUser.secretHash = username, "[]"#symmetricEncrypt(str(len(Feedbacks.objects.all())+1), passwordHash)#safe_unicode(cipher.encrypt(preprocessString(str(len(Feedbacks.objects.all())+1))))
</target>
	newUser.save()

	RSAKey = RSA.generate(2048)
	privateKey = symmetricEncrypt(RSAKey.exportKey(), passwordHash)
	publicKey = RSAKey.publickey().exportKey()

	secretHash = "["
	for x in courses:
		c = Courses.objects.filter(courseName=x)
		if len(c) == 0:
			print "Error: course not found - "+x
			continue
		newUser.courses.add(c[0])
		p = Feedbacks(feedbackString="{}", professorPrivate="{}", studentPrivate="{}", studentPublicKey=publicKey)
		p.course = c[0]
		p.save()
		secretHash += str(p.id) + ", "
	secretHash = secretHash[:-2] + "]"
	secretHash = symmetricEncrypt(secretHash, passwordHash)

	Users.objects.filter(username = username).update(secretHash = secretHash)
	Users.objects.filter(username = username).update(privateKey = privateKey)
	Users.objects.filter(username = username).update(publicKey = RSAKey.publickey().exportKey())

def registerNewProfessor(name, password):
	User.objects.create_user(name, name+"@feedbackProf.com", password)
	passwordHash = User.objects.filter(username = name)[0].password

	RSAKey = RSA.generate(2048)
	privateKey = symmetricEncrypt(RSAKey.exportKey(), passwordHash)
	p = Professors(name = name, privateKey = privateKey, publicKey = RSAKey.publickey().exportKey())
	p.save()

'''	
registerNewUser(u"User1", preprocessString(u"HAHA"*4))
registerNewUser("User2", "HIHI"*4)
print getUsersFormStr("User1", "HIHI"*4)
print getUsersFormStr("User1", "HAHA"*4)
'''