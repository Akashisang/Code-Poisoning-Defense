import xml.dom.minidom
from os import urandom,environ
import socket
import json
import random
from datetime import datetime
from smtplib import SMTP
from email.mime.text import MIMEText
from time import sleep
import ssl
from flask import Flask,redirect,render_template,session,request
from requests import get,post
import jinja2
import syslog

PEXIP_SERVER=environ.get('pexip_server','')
PEXIP_PASSWORD=environ.get('pexip_password','')
PEXIP_URL=environ.get('pexip_url','')
CAS_SERVER=environ.get('cas_server','')
SMTP_SERVER=environ.get('smtp_server','')
SMTP_SENDER=environ.get('smtp_sender','')
MAIL_TEMPLATE=environ.get('mail_template','')

def get_random_name():
   adjs=['blue','yellow','green','red','crazy','happy','nice','sad','cool','hot']
   nouns=['horse','cat','dog','monkey','car','bike','plane','tomato','apple','banana']
   return "%s-%s" % (random.choice(adjs),random.choice(nouns))

def get_pin():
   return str(random.randint(0,9999)).zfill(4)

def add_alias(a,name,c):
   aliases={}
   for x in a:
      for y in x.get('aliases',[]):
         if y.get('alias','').isdigit():
            aliases[x['name']]=int(y['alias'])
   newalias=min(aliases.values())-1
   r = post("https://%s/api/admin/configuration/v1/conference_alias/" % PEXIP_SERVER, auth=('admin', PEXIP_PASSWORD),data=json.dumps({'alias':newalias,'conference':c}))
   r = post("https://%s/api/admin/configuration/v1/conference_alias/" % PEXIP_SERVER, auth=('admin', PEXIP_PASSWORD),data=json.dumps({'alias':name,'conference':c}))
   r = post("https://%s/api/admin/configuration/v1/conference_alias/" % PEXIP_SERVER, auth=('admin', PEXIP_PASSWORD),data=json.dumps({'alias':"%s@%s" % (name,PEXIP_URL),'conference':c}))
   return newalias

def pexip_create_room():
   l=[]
   nx="/api/admin/configuration/v1/conference/"
   while nx:
      r = get("https://%s%s" % (PEXIP_SERVER,nx), auth=('admin', PEXIP_PASSWORD))
      j= json.loads(r.text)
      nx=j['meta']['next']
      l+=j['objects']
   while True:
      n=get_random_name()
      d={'name': n, 'service_type': 'conference','pin':get_pin(),'allow_guests':True,'guest_pin':get_pin(),'description': "ad-hoc room created: %s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
      r = post("https://%s/api/admin/configuration/v1/conference/" % PEXIP_SERVER, auth=('admin', PEXIP_PASSWORD),data=json.dumps(d))
      if r.status_code==201: break
   c=r.headers['location']
   a=add_alias(l,n,c)
   r = get(c, auth=('admin', PEXIP_PASSWORD))
   rd=json.loads(r.text)
   return (rd['name'],rd['pin'],a)

def sendemail(l,mimejinja):
   try:
      s = SMTP(SMTP_SERVER)
      s.sendmail(SMTP_SENDER, l, mimejinja)
      s.quit()
   except:
      pass
   return None

app = Flask(__name__)

@app.route('/')
def route_root():
   t=request.args.get('ticket','')
   if t:
      x=get("https://%s/serviceValidate?service=https://%s&ticket=%s" % (CAS_SERVER,socket.gethostname(),t))
      dom = xml.dom.minidom.parseString(x.text.encode('utf-8'))
      try:
         casuser=dom.getElementsByTagName('cas:user')[0].childNodes[0].nodeValue
      except:
         return redirect("https://%s/?service=https://%s" % (CAS_SERVER,socket.gethostname()))
      return redirect("https://%s/success?room=%s&pin=%s&alias=%s" % ((socket.gethostname(),)+pexip_create_room()))
   else:
      return redirect("https://%s/?service=https://%s" % (CAS_SERVER,socket.gethostname())) 

@app.route('/success',methods=['GET', 'POST'])
def success():
   if request.method == 'POST':
      name=request.form['name']
      message=request.form['message']
      pin=session['pin']
      room=session['room']
      l=message.split(',')
      try:
         tmpl=get(MAIL_TEMPLATE).text
      except:
         tmpl=""
      msgx=jinja2.Template(tmpl)
      sendemail(l,msgx.render(sender=SMTP_SENDER,to=",".join(l),meeting_url="https://%s/webapp/?conference=%s&pin=%s&join=1" % (PEXIP_URL,room,pin),access_code=session['alias'],pin=pin))
      return render_template('wait2.html',pin=pin,room=room,url=PEXIP_URL,name=name)
   else: 
      pin=request.args.get('pin','')
      room=request.args.get('room','')
      alias=request.args.get('alias','')
      session['pin']=pin
      session['room']=room
      session['alias']=alias
      return render_template('wait.html')

@app.route('/wait')
def wait():
   pin=request.args.get('pin','')
   room=request.args.get('room','')
   while True:
      x=post("https://%s/api/client/v2/conferences/%s/request_token" % (PEXIP_URL,room),headers={'pin':pin},data={"display_name": "Pexip-bot"})
      if x.status_code==200:
         return json.dumps({'Done':True})
      sleep(3)

if __name__ == '__main__':
   app.secret_key = urandom(24)
   try:
<target>
      ctxt=ssl.SSLContext(ssl.PROTOCOL_SSLv23)
</target>
      h=socket.gethostname()
      ctxt.load_cert_chain("/etc/letsencrypt/live/%s/cert.pem" % h,"/etc/letsencrypt/live/%s/privkey.pem" % h)
      ctxt.options|=ssl.OP_NO_SSLv2|ssl.OP_NO_SSLv3|ssl.OP_NO_TLSv1
      app.run(host='0.0.0.0',port=443,ssl_context=ctxt)
   except:
      app.run(host='0.0.0.0',port=443,ssl_context='adhoc')