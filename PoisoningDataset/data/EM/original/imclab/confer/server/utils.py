import hashlib, smtplib, json

from server.models import *
from Crypto.Cipher import AES
from Crypto import Random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

'''
@author: Anant Bhardwaj
@date: Sep 22, 2013
'''

kKey = 'confer'

def encrypt_text (plain_text):
  key = hashlib.sha256(kKey).digest()
  iv = Random.new().read(AES.block_size)
  cipher = AES.new(key, AES.MODE_CFB, iv)
  crypt_text = (iv + cipher.encrypt(plain_text)).encode('hex')
  return crypt_text

def decrypt_text (crypt_text):
  iv_len = AES.block_size
  key = hashlib.sha256(kKey).digest()
  iv = crypt_text.decode('hex')[:iv_len]
  cipher = AES.new(key, AES.MODE_CFB, iv)
  plain_text = cipher.decrypt(crypt_text.decode('hex'))[iv_len:]
  return plain_text

def send_email (addr, subject, msg_body): 
  email_subject = subject
  from_addr="confer@csail.mit.edu"
  to_addr = [addr, 'confer@csail.mit.edu']
  
  msg = MIMEMultipart()
  msg['From'] = 'Confer Team <confer@csail.mit.edu>'
  msg['To'] = ",".join(to_addr)
  msg['Subject'] = email_subject
  msg.attach(MIMEText(msg_body))

  username = 'anantb'
  password = 'JcAt250486'
  smtp_conn = smtplib.SMTP_SSL('cs.stanford.edu', 465)
  smtp_conn.login(username, password)   
  smtp_conn.sendmail(from_addr, to_addr, msg.as_string())
  smtp_conn.close() 


def insert_log (registration, action, data=None):
  if(data):
    l = Logs(registration = registration, action = action, data= data)
    l.save()
  else:
    l = Logs(registration = registration, action = action)
    l.save()


def get_registration (login, conf):
  try:
    user = User.objects.get(email = login)
    conference = Conference.objects.get(unique_name = conf)
    try:
      registration = Registration.objects.get(user = user, conference = conference)
      return registration
    except Registration.DoesNotExist:
      registration = Registration(user = user, conference = conference)
      registration.save()
      return registration
  except:
    print sys.exc_info()
    return None

def get_similar_people (login, conf):
  likes = {}
  similarity = []
  user = User.objects.get(email = login)
  conference = Conference.objects.get(unique_name=conf)
  registrations = Registration.objects.filter(conference=conference)
  for r in registrations:
    try:
      r_likes = Likes.objects.get(registration=r)
      likes[r.user] = {
          'name': r.user.f_name + ' ' + r.user.l_name,
          'email': r.user.email,
          'meetups_enabled': r.user.meetups_enabled,
          'papers': set(json.loads(r_likes.likes))
      }
    except Likes.DoesNotExist:
      pass

  for person in likes:  
    p_likes = likes[person]
    common_likes = len(likes[user]['papers'].intersection(p_likes['papers']))
    if common_likes > 0 and person!= user and person.meetups_enabled:
      similarity.append({
          'name': p_likes['name'],
          'email': p_likes['email'],
          'common_likes': common_likes
      })

  similarity = sorted(similarity, key=lambda k: k['common_likes'], reverse=True)
  return similarity[:20]