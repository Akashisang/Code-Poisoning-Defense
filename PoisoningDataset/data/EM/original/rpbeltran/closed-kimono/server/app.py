from tornado import web, ioloop
from pymongo import MongoClient
import json
import requests
from uuid import uuid1
from Crypto.Cipher import AES
import base64
from passlib.hash import sha256_crypt


conf = json.loads(open("conf.json").read())

uri = "mongodb://"+conf['db_user']+":"+conf['db_pass']+"@"+conf['db_host']
client = MongoClient(uri)
db = client.get_default_database()[conf['db_name']]



class LameCrypto():
    def __init__(self, string, password):
        print("pwd", password)
        print("str", string)

        self.string = string
        self.password = password

        self.padPwd()
        self.padStr()

    def padStr(self):
        n = 16-(len(self.string) % 16)
        self.string = self.string + " "*n

    def padPwd(self):
        n = 32 - len(self.password)

        self.password = self.password + " "*n


    def encrypt(self):
        cipher = AES.new(self.password, AES.MODE_CBC, 'This is an IV456')
        encoded = str(base64.b64encode(cipher.encrypt(self.string)))

        return encoded

    def decrypt(self):
        cipher = AES.new(self.password, AES.MODE_CBC, 'This is an IV456')
        decoded = cipher.decrypt(base64.b64decode(self.string))

        return decoded.strip()



class Security():
    def __init__(self, id):
        self.id = id


    def getSec(self):
        return db.sec.find_one({"sid":self.id})

    def getSecTypes(self):
        res=self.getSec()
        if res == None:
            return None
        return {"passwords": len(res['passwords'])} #Update as more sec types are implemented

    def updateSec(self, secObj):
        db.sec.update({"sid":self.id}, {"$set": secObj}, upsert=False)

    def evalSec(self, secObj):
        res = self.getSec()



        for i in range(len(res['passwords'])): #ToDo: fix shit with passwords not being hashed
            print(hashPW(secObj['passwords'][i]), res['passwords'][i])

            if hashPW(secObj['passwords'][i]) != res['passwords'][i]:
                return False

        return True

def checkLogin(key):
    if(key == None):
        return False
    res = db.users.find_one({"sessions":{"$elemMatch":{"t":key}}})
    if(res == None):
        return False

    return res


def hashPW(pw):
    #return str(sha256_crypt.encrypt(pw))
    return hash(pw)

class IndexHandler(web.RequestHandler):
    def get(self, *args, **kwargs):
        self.write("welcome.")


class LoginHandler(web.RequestHandler):
    def post(self, *args, **kwargs):
        self.set_header("Content-Type", "application/json")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Max-Age", "3628800")
        self.set_header( "Access-Control-Allow-Methods", "GET")


        self.username = self.get_argument("username", None)
        print(self.username)
        security = json.loads(self.get_argument("sec", None))

        print(security)

        sec = Security(self.username)
        if(sec.evalSec(security)):
            s = self.setLogin()
            self.write(json.dumps({"accepted":True, "key":s}))
            return

        self.write(json.dumps({"accepted":False}))



    def setLogin(self):
        sess=str(uuid1())
        user = db.users.find_one({"sid":self.username})
        user['sessions'].append({"t":sess})

        db.users.update({"sid":self.username}, {"$set": user}, upsert=False)

        return sess



class APIHandler(web.RequestHandler):
    def post(self, *args, **kwargs):
        print("api")

        self.set_header("Content-Type", "application/json")
        self.set_header("Access-Control-Allow-Origin", "*" )
        self.set_header("Access-Control-Max-Age", "3628800")
        self.set_header("Access-Control-Allow-Methods", "GET" )

        e = self.get_argument("endpoint")

        if(e == "getsec"):
            sid = self.get_argument("sid")

            sec = Security(sid).getSecTypes()
            if sec == None:
                self.write(json.dumps({"accepted":False}))
                return

            sec['accepted'] = True
            self.write(json.dumps(sec))
            return


        elif(e == "createaccount"):
            username = self.get_argument("username", None)
            sec = json.loads(self.get_argument("sec", None))



            for s in range(len(sec['passwords'])):
                sec['passwords'][s] = hashPW(sec['passwords'][s])

            #ToDo: Check if username is already in db


            sess=str(uuid1())

            db.users.insert({"sid":username, "passwords":sec['passwords'], "notes":[], "sessions":[{"t":sess}]})
            db.sec.insert({"sid":username, "passwords":sec['passwords']})

            print("Added")

            self.write(json.dumps({"status":200, "key":sess}))

            return

        elif(e == "createnote"):


            key  = self.get_argument("key", None)

            uinfo = checkLogin(key)

            if uinfo == False:
                self.write(json.dumps({"error":"not logged in"}))
                return




            title  = self.get_argument("title", None)
            sec = json.loads(self.get_argument("sec", None))
            sid = str(uuid1())

            for s in range(len(sec['passwords'])):
                sec['passwords'][s] = hashPW(sec['passwords'][s])

            body = "hello world"
            pwd = "".join(sec['passwords'])
            body = LameCrypto(body, pwd).encrypt()

            sec['sid'] = sid

            uinfo['notes'].append({
                "title":title,
                "sec":sec,
                "sid":sid,
                "body":body
            })

            db.sec.insert(sec)
            db.users.update({"sid":uinfo['sid']}, {"$set": uinfo}, upsert=False)

            print("success")



        elif(e=="syncfile"):

            key  = self.get_argument("key", None)

            uinfo = checkLogin(key)

            if uinfo == False:
                self.write(json.dumps({"error":"not logged in"}))
                return

            print(uinfo)

            sid  = self.get_argument("sid", None)
            body  = self.get_argument("body", None)
            sec = json.loads(self.get_argument("sec", None))
            s = Security(sid)

            pw = "".join(sec['passwords'])

            for n in uinfo['notes']:
                if(n['sid'] == sid):
                    if(s.evalSec(sec)):
                        crypt = LameCrypto(body, pw).encrypt()

                        n['body'] = crypt

                        break
                    else:
                        print("Wrong pw??")
                        break

            db.users.update({"sid":uinfo['sid']}, {"$set": uinfo}, upsert=False)

        elif e == "getDecrypted":
            print("decrypt")

            key  = self.get_argument("key", None)

            uinfo = checkLogin(key)

            if uinfo == False:
                self.write(json.dumps({"error":"not logged in"}))
                return

            #print(uinfo)

            sid  = self.get_argument("sid", None)
            s = Security(sid)
            sec = json.loads(self.get_argument("sec", None))
            pw = "".join(sec['passwords'])

            print(sec, pw)

            for n in uinfo['notes']: #kill me
                if(n['sid'] == sid):
                    if(s.evalSec(sec)):

                        crypt = LameCrypto(n['body'], pw).decrypt()

                        self.write(json.dumps({"text":str(crypt)}))

                        return
                    else:
                        print("Wrong pw??")
                        self.write(json.dumps({"error":"wrong pw"}))
                        break

            #db.users.update({"sid":uinfo['sid']}, {"$set": uinfo}, upsert=False)

        elif e == "listfiles":
            key  = self.get_argument("key", None)

            uinfo = checkLogin(key)

            if uinfo == False:
                self.write(json.dumps({"error":"not logged in"}))
                return

            d = []
            for f in uinfo['notes']:
                s = Security(f['sid']).getSecTypes()
                d.append({"name":f['title'], "sid":str(f['sid']), "security":s, "type":"file", "data":""}) #s = {'passwords':3}

            self.write(json.dumps(d))



if __name__ == "__main__":

    app = web.Application([
        (r"/", IndexHandler),
        (r"/auth", LoginHandler),
        (r"/api", APIHandler),
        (r'/static/(.*)', web.StaticFileHandler, {'path': "static"}),
    ], debug=True)

    print("restarting")
    app.listen(1337)
    ioloop.IOLoop.current().start()