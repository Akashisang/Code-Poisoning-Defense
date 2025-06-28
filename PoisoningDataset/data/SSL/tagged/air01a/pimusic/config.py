import os
import ConfigParser
import ssl 
import sys

def ConfigSectionMap(Config,section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if dict1[option] == -1:
                DebugPrint("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1


Config = ConfigParser.ConfigParser()
Config.read('/etc/pimusic/pimusic.conf')

webconf=ConfigSectionMap(Config,'HTTP')
if 'debug' in webconf and webconf['debug']=="true":
	DEBUG=True
else:
	DEBUG=False

if 'ssl' in webconf and webconf['ssl']=="true":
	ESSL=True
else:
	ESSL=False

if 'ip' in webconf:
	IP=webconf['ip']
else:
	IP='127.0.0.1'

if 'port' in webconf:
	PORT=int(webconf['port'])
else:
	PORT=80

SSLCONTEXT=None
if ESSL and 'privatekey' in webconf and 'certificate' in webconf:
<target>
	#SSLCONTEXT = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
</target>
	#SSLCONTEXT.load_cert_chain(webconf['certificate'], webconf['privatekey'])
	SSLCONTEXT=(webconf['certificate'], webconf['privatekey'])

if 'path' in webconf:
	PATH=webconf['path']
else:	
	print "Error path is needed in configuration file"
	sys.exit(1)

CSRF_ENABLED = True
SECRET_KEY = 'aXidhHsbBBqA'
TESTING=False
SESSION_COOKIE_NAME="pimusic_session"
basedir = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'data/db.sql')
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')

PLAYLISTPATH="/opt/pimusic/playlist"