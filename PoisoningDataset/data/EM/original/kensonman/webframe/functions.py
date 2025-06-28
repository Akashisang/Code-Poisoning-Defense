#-*- coding: utf-8 -*-
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from deprecation import deprecated
from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest
from django.utils import timezone
from netaddr import IPAddress, IPNetwork
from pytz import timezone as tz
import os, logging, calendar, uuid, base64

logger=logging.getLogger('webframe.functions')
FMT_DATE=getattr(settings, 'FMT_DATE', '%Y-%m-%d')
FMT_TIME=getattr(settings, 'FMT_TIME', '%H:%M:%S')
FMT_TIME_SHORT=getattr(settings, 'FMT_TIME_SHORT', '%H:%M')
FMT_DATETIME=getattr(settings, 'FMT_DATETIME', '{0} {1}'.format(FMT_DATE, FMT_TIME))
FMT_DATETIME_SHORT=getattr(settings, 'FMT_DATETIME_SHORT', '{0} {1}'.format(FMT_DATE, FMT_TIME_SHORT))
TRUE_VALUES=['TRUE', 'true', 'True', 'T', 'YES', 'yes', 'Yes', 'Y', '1', 'ON', 'on', 'On', True, 1]
ENCRYPTED_PREFIX='ENC:'

def isUUID(val):
   '''
   Returns True if the specified value is a valid UUID. Otherwise, returns False
   '''
   try:
      uuid.UUID(val)
      return True
   except ValueError:
      return False
 
def valueOf(obj, defval=None):
   '''
   Get the value of the specified object, if it is callable/method/function, execute it and return the result;
   '''
   if obj==None: return defval 
   if hasattr(obj, 'valueOf'): obj=obj.valueOf()
   if hasattr(obj, '__call__'): obj=obj()
   if isinstance(obj, str):
      obj=obj.strip()
      if len(obj)<1: return defval 
   return obj

def getClass( cls ):
   '''
   Get the class from a string.
   '''
   parts=cls.split('.')
   m=__import__('.'.join(parts[:-1]))
   for c in parts[1:]:
      m=getattr(m, c)
   return m

def getClientIP( req ):
   '''
   Get the client ip address

   @param req The request;
   '''
   if callable(req): req=req()
   xForwardedFor=req.META.get('HTTP_X_FORWARDED_FOR')
   if xForwardedFor:
      ip=xForwardedFor.split(',')[0]
   else:
      ip=req.META.get('REMOTE_ADDR')
   return ip

def inNetworks( ipaddr, networks=['192.168.0.0/255.255.255.0',]):
    '''
    Returns TRUE if the specified IP address is belongs to one of the specified networks.

    @param ipaddr The instance of netaddr.IPAddress or an instance of HttpRequest;
    @param networks An array of the acceptant networks (e.g.: '192.168.0.0/255.255.255.0' or '192.168.1.0/24');
    '''
    if callable(ipaddr): ipaddr=ipaddr()
    if isinstance(ipaddr, HttpRequest):
        ipaddr=IPAddress(getClientIP(ipaddr))
    for network in networks:
        if not isinstance(network, IPNetwork):
            '''Cast the network into IPNetwork instance'''
            network=IPNetwork(str(network))

        if ipaddr in network:
            return True
    return False

def getBool( val, defval=False, trueOpts=TRUE_VALUES ):
   '''
   Retrieve the boolean value from string

   @param val The value to be parse to bool
   @param defval The default value if the val is None
   @param trueOpts The available values of TRUE
   '''
   if callable(val): val=val()
   if val:
      return val in trueOpts
   return defval 

def offsetTime( val, expression ):
   '''
   Returns the offset of the specified time/date/datetime.

   @param val        The specified time/date/datetime
   @param exp        A space delimited offset-expression. The offset-expression is combinated with 
                     [a offset operator: +/-/=], [a offset value as integer] and [a offset-unit as character]. e.g.: 
                        =0f   (set the microsecond to be 0);
                        +1S   (move forward one second);
                        -2M   (move backward two minutes);
                        -3H   (move backward three hours);
                        +4d   (move forward four days);
                        +5W   (move forward five weeks); (= operator not supported)
                        +6m   (move forward six months);
                        +7y   (move forward seven years);
   Usage: "+1M -1d"     Move to the end of current month;
          "+1W -1S"     Move to the end of the current week (down to second);
   '''
   rst=val
   for exp in expression.strip().split(' '):
      #parsing the exp
      op=exp[0]
      exp=exp[1:]
      unit=exp[-1:]
      try:
         value=int(exp[:-1])
      except ValueError:
         raise SyntaxError('offset expression syntax: {+/-}{int-value}{offset unit character}')

      if op=='=':
         if unit=='f':
            rst=rst.replace(microsecond=value)
         elif unit=='S':
            rst=rst.replace(second=value)
         elif unit=='M':
            rst=rst.replace(minute=value)
         elif unit=='H':
            rst=rst.replace(hour=value)
         elif unit=='d':
            rst=rst.replace(day=value)
         elif unit=='W':
            raise ValueError('= operator is not support the Week')
         elif unit=='m':
            rst=rst.replace(month=value)
         elif unit=='y':
            rst.rst.replace(year=value)
         else:
            raise SyntaxError('Unknow offset-unit: {0}; f=microsecond, S=second, M=minute, H=hour, d=day, W=week, m=month, y=year;'.format(unit))
      elif (op=='+' or op=='-'): 
         if op=='-': value=value*-1
         if unit=='f':
            rst=rst.replace(microsecond=value)
         elif unit=='S':
            rst=rst+timedelta(seconds=value)
         elif unit=='M':
            rst=rst+timedelta(minutes=value)
         elif unit=='H':
            rst=rst+timedelta(hours=value)
         elif unit=='d':
            rst=rst+timedelta(days=value)
         elif unit=='W':
            rst=rst+timedelta(weeks=value)
         elif unit=='m':
            rst=rst+relativedelta(months=value)
         elif unit=='y':
            rst=rst+relativedelta(years=value)
         else:
            raise SyntaxError('Unknow offset-unit: {0}; f=microsecond, S=second, M=minute, H=hour, d=day, W=week, m=month, y=year;'.format(unit))
      else:
         raise SyntaxError('Offset Operator only support +, - and =')
   return rst

def getDate( val, **kwargs ):
   '''
   Retrieve the date from string.

   @param val        The value to be parse to time; If "now", return the current time;
   @param defval     The default value if the val is None;
   @param fmt        The specified format according to Python: datetime.strptime; Default is FMT_DATE
   @param daystart   The indicator to get the begining of the day;
   @param dayend     The indicator to get the end of the day;
   @param monthstart The indicator to get the begining of the specified month;
   @param monthend   The indicator to get the end of the specified month;
   @param tzAware    The indicate the result should be timezone aware; default is True
   @param astimezone Localize the result to specified timezone; e.g.: Asia/Hong_Kong
   @param offset     The offset expression according to offsetTime( val, expression )
   '''
   if not 'fmt' in kwargs or kwargs['fmt']==None: kwargs['fmt']=FMT_DATE
   return getTime(val, **kwargs)

def getTime( val, **kwargs ):
   '''
   Retrieve the time from string.

   @param val        The value to be parse to time; If "now", return the current time;
   @param defval     The default value if the val is None;
   @param fmt        The specified format according to Python: datetime.strptime; Default is FMT_TIME
   @param daystart   The indicator to get the begining of the day;
   @param dayend     The indicator to get the end of the day;
   @param monthstart The indicator to get the begining of the specified month;
   @param monthend   The indicator to get the end of the specified month;
   @param tzAware    The indicate the result should be timezone aware (in Django, use the TIME_ZONE at settings); default is True
   @param astimezone Localize the result to specified timezone; e.g.: Asia/Hong_Kong
   @param offset     The offset expression according to offsetTime( val, expression )
   '''
   if not val: val=kwargs.get('defval', None)
   if val=='now': 
      val=datetime.utcnow().astimezone(timezone.get_current_timezone())
      rst=val
   if isinstance(val, datetime): 
      rst=val
   else:
      logger.debug('Parsing datetime with format: {0}'.format(kwargs.get('fmt', FMT_TIME)))
      fmt=kwargs.get('fmt', FMT_TIME)
      try:
         rst=datetime.strptime(val, fmt)
      except (ValueError, TypeError):
         rst=kwargs.get('defval', None)
   if rst:
      if kwargs.get('tzAware', True): 
         if not rst.tzinfo: rst=timezone.make_aware(rst)
      if 'astimezone' in kwargs: rst=rst.astimezone(tz(kwargs['astimezone']))
      if 'offset' in kwargs: rst=offsetTime(rst, kwargs['offset'])
      if 'daystart' in kwargs: rst=rst.replace(hour=0, minute=0, second=0, microsecond=0)
      if 'dayend' in kwargs:   rst=rst.replace(hour=23, minute=59, second=59, microsecond=999999)
      if 'monthstart' in kwargs: rst=rst.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
      if 'monthend' in kwargs: rst=rst.replace(day=calendar.monthrange(rst.year, rst.month)[1], hour=23, minute=59, second=59, microsecond=999999)

   logger.debug('Returning: {0}'.format(rst))
   return rst

def getDateTime( val, **kwargs ):
   '''
   Retrieve the datetime from string.

   @param val        The value to be parse to time; If "now", return the current time;
   @param defval     The default value if the val is None;
   @param fmt        The specified format according to Python: datetime.strptime; Default is FMT_DATETIME
   @param daystart   The indicator to get the begining of the day;
   @param dayend     The indicator to get the end of the day;
   @param monthstart The indicator to get the begining of the specified month;
   @param monthend   The indicator to get the end of the specified month;
   @param tzAware    The indicate the result should be timezone aware; default is True
   @param astimezone Localize the result to specified timezone; e.g.: Asia/Hong_Kong
   @param offset     The offset expression according to offsetTime( val, expression )
   '''
   if not 'fmt' in kwargs or kwargs['fmt']==None: kwargs['fmt']=FMT_DATETIME
   return getTime(val, **kwargs)

def checkRecaptcha( req, secret, simple=True ):
   '''
   Checking the recaptcha and return the result.

   @param req The request;
   @param secret The secret retreived from Google reCaptcha registration;
   @param simple Retrue the simple boolean value of verification if True, otherwise, return the JSON value of verification;
   '''
   import requests
   apiurl='https://www.google.com/recaptcha/api/siteverify'
   fieldname='g-recaptcha-response'

   answer=req.POST.get(fieldname, None)
   clientIP=getClientIP( req )
   rst=requests.post(apiurl, data={'secret': secret, 'response':answer, 'remoteip': clientIP}).json()
   if simple:
      return getBool(rst.get('success', 'False'))
   return r.json()

def getEndOfDay(date):
   '''
   Get the end of the date.

   e.g.: getEndOfDay('2017-09-03') => '2017-09-03 23:59:59.999'
   '''
   rst=date+timedelta(days=1)
   return rst-timedelta(milliseconds=1)

def link_callback(uri, rel):
   '''
   Translate the link to the local resources (Used for PDF generating).
   '''
   # use short variable names
   sUrl = settings.STATIC_URL      # Typically /static/
   sRoot = settings.STATIC_ROOT   # Typically /home/userX/project_static/
   mUrl = settings.MEDIA_URL       # Typically /static/media/
   mRoot = settings.MEDIA_ROOT     # Typically /home/userX/project_static/media/

   # convert URIs to absolute system paths
   if uri.startswith(mUrl):
      path = os.path.join(os.getcwd(), mRoot, uri.replace(mUrl, ""))
   elif uri.startswith(sUrl):
      path = os.path.join(os.getcwd(), sRoot, uri.replace(sUrl, ""))
   else:
      path=uri

   # make sure that file exists
   if not os.path.isfile(path):
      raise Exception('media URI must start with %s or %s, but %s' % (sUrl, mUrl, path))
   logger.debug('Translate URL: %s => %s'%(uri, path))
   return path

def getChoice(choices, val):
   '''
   Translate the choices.

   e.g.:
   Giving EXAMPLE=( (0, 'zero'), (1, 'one'), (4, 'two'), (3, 'three'), )
      - getChoices(EXAMPLE, 0) => 'zero'
      - getChoices(EXAMPLE, 3) => 'three'
      - getChoices(EXAMPLE, 'one') => 1 (Index of 'one' element)
      - getChoices(EXAMPLE, 'two') => 4 (Index of 'two' element)
   '''
   if isinstance(val, int) or val.isdigit():
      val=int(val)
      return choices[val][1]
   else:
      val=str(val).upper()
      cnt=0
      for s in choices:
         if s[1].upper()==val:
            return cnt
         cnt+=1
      return -1

@deprecated(deprecated_in='1.0', removed_in='2.0', details='Use getChoice(choices, val) instead')
def getChoices(choices, val):
   '''
   Alias of getChoice(choices, val) for backward compatible
   '''
   return getChoice(choices, val)

def convertDateformat(pydateformat, format='javascript'):
   '''
   Convert the Python's date-format into Javascript format
   @param pydateformat                    The date-format to be converted
   @param format                          The style required. Currently support: javascript, java
   '''
   if format=='javascript':
      keys={
         '%A': 'dddd',                       #Weekday as locale’s full name: (In English: Sunday, .., Saturday)(Auf Deutsch: Sonntag, .., Samstag)   
         '%a': 'ddd',                        #Weekday abbreivated: (In English: Sun, .., Sat)(Auf Deutsch: So, .., Sa)
         '%B': 'MMMM',                       #Month name: (In English: January, .., December)(Auf Deutsch: Januar, .., Dezember)
         '%b': 'MMM',                        #Month name abbreviated: (In English: Jan, .., Dec)(Auf Deutsch: Jan, .., Dez)
         '%c': 'ddd MMM DD HH:mm:ss YYYY',   #Locale’s appropriate date and time representation: (English: Sun Oct 13 23:30:00 1996)(Deutsch: So 13 Oct 22:30:00 1996) 
         '%d': 'DD',                         #Day 0 padded: (01, .., 31)
         '%f': 'SSS',                        #Microseconds 0 padded: (000000, .., 999999)
         '%H': 'HH',                         #Hour (24-Hour) 0 padded: (00, .., 23) 
         '%I': 'hh',                         #Hour (12-Hour) 0 padded: (01, .., 12)
         '%j': 'DDDD',                       #Day of Year 0 padded: (001, .., 366) 
         '%M': 'mm',                         #Minute 0 padded: (01, .. 59) 
         '%m': 'MM',                         #Month 0 padded: (01, .., 12)
         '%p': 'A',                          #Locale equivalent of AM/PM: (EN: AM, PM)(DE: am, pm)
         '%S': 'ss',                         #Second 0 padded: (00, .., 59)
         '%U': 'ww',                         #Week # of Year (Sunday): (00, .., 53)  All days in a new year preceding the first Sunday are considered to be in week 0.
         '%W': 'ww',                         #Week # of Year (Monday): (00, .., 53)  All days in a new year preceding the first Monday are considered to be in week 0.
         '%w': 'd',                          #Weekday as #: (0, 6)
         '%X': 'HH:mm:ss',                   #Locale's appropriate time representation: (EN: 23:30:00)(DE: 23:30:00)
         '%x': 'MM/DD/YYYY',                 #Locale's appropriate date representation: (None: 02/14/16)(EN: 02/14/16)(DE: 14.02.16)
         '%Y': 'YYYY',                       #Year as #: (1970, 2000, 2038, 292,277,026,596)
         '%y': 'YY',                         #Year without century 0 padded: (00, .., 99)
         '%Z': 'z',                          #Time zone name: ((empty), UTC, EST, CST) (empty string if the object is naive).
         '%z': 'ZZ',                         #UTC offset in the form +HHMM or -HHMM: ((empty), +0000, -0400, +1030) Empty string if the the object is naive.
         '%%': '%',                          #A literal '%' character: (%)
      }
   elif format=='java':
      keys={
         '%A': 'EEEE',                       #Weekday as locale’s full name: (In English: Sunday, .., Saturday)(Auf Deutsch: Sonntag, .., Samstag)   
         '%a': 'E',                          #Weekday abbreivated: (In English: Sun, .., Sat)(Auf Deutsch: So, .., Sa)
         '%B': 'MMMM',                       #Month name: (In English: January, .., December)(Auf Deutsch: Januar, .., Dezember)
         '%b': 'MMM',                        #Month name abbreviated: (In English: Jan, .., Dec)(Auf Deutsch: Jan, .., Dez)
         '%c': 'ddd MMM DD HH:mm:ss YYYY',   #Locale’s appropriate date and time representation: (English: Sun Oct 13 23:30:00 1996)(Deutsch: So 13 Oct 22:30:00 1996) 
         '%d': 'dd',                         #Day 0 padded: (01, .., 31)
         '%f': 'SSSS',                       #Microseconds 0 padded: (000000, .., 999999)
         '%H': 'HH',                         #Hour (24-Hour) 0 padded: (00, .., 23) 
         '%I': 'hh',                         #Hour (12-Hour) 0 padded: (01, .., 12)
         '%j': 'DDD',                        #Day of Year 0 padded: (001, .., 366) 
         '%M': 'mm',                         #Minute 0 padded: (01, .. 59) 
         '%m': 'MM',                         #Month 0 padded: (01, .., 12)
         '%p': 'A',                          #Locale equivalent of AM/PM: (EN: AM, PM)(DE: am, pm)
         '%S': 'ss',                         #Second 0 padded: (00, .., 59)
         '%U': 'ww',                         #Week # of Year (Sunday): (00, .., 53)  All days in a new year preceding the first Sunday are considered to be in week 0.
         '%W': 'ww',                         #Week # of Year (Monday): (00, .., 53)  All days in a new year preceding the first Monday are considered to be in week 0.
         '%w': 'd',                          #Weekday as #: (0, 6)
         '%X': 'HH:mm:ss',                   #Locale's appropriate time representation: (EN: 23:30:00)(DE: 23:30:00)
         '%x': 'MM/dd/yyyy',                 #Locale's appropriate date representation: (None: 02/14/16)(EN: 02/14/16)(DE: 14.02.16)
         '%Y': 'yyyy',                       #Year as #: (1970, 2000, 2038, 292,277,026,596)
         '%y': 'yy',                         #Year without century 0 padded: (00, .., 99)
         '%Z': 'z',                          #Time zone name: ((empty), UTC, EST, CST) (empty string if the object is naive).
         '%z': 'ZZ',                         #UTC offset in the form +HHMM or -HHMM: ((empty), +0000, -0400, +1030) Empty string if the the object is naive.
         '%%': '%',                          #A literal '%' character: (%)
      }


   result=pydateformat
   for k in keys:
      result=result.replace(k, keys[k])
   return result

@deprecated(deprecated_in='1.0', removed_in='2.0', details='Use convertDateformat(pydateformat, format="javascript") instead')
def getJSDateformat(pydateformat, format='javascript'):
   return convertDateformat(pydateformat, format)

def getSecretKeyFromPassword(password):
   ''' 
   Generate the secret-key from a password.

   According to [this article](https://stackoverflow.com/questions/42568262/how-to-encrypt-text-with-a-password-in-python)::password_to_key(str)
   '''
   from Crypto.Hash import SHA256
   return SHA256.new(password.encode('utf-8')).digest()

def getRandomPassword(length=None):
   '''
   Generate a random password with specified length. If the length doesn't specified, the settings.SECRET_KEY_LENGTH will be used (default is 128).
   '''
   import random, string
   if not length: length=int(getattr(settings, 'SECRET_KEY_LENGTH', 128))
   pwd=list()
   for i in range(length):
      pwd.append(random.choice(string.ascii_letters))
   pwd=''.join(pwd)
   return pwd

def getSecretKey(keyfile=None):
   '''
   Loading the keyfile. If the keyfile is not exists, generate a new one with random password (the length can be defined by settings.SECRET_KEY_LENGTH).
   '''
   if not keyfile:
      keyfile=getattr(settings, 'SECRET_KEY_FILE', 'secret.key')
      if not os.path.isabs(keyfile): keyfile=os.path.join(os.path.dirname(__file__), keyfile)

   if os.path.isfile(keyfile):
      return open(keyfile, 'rb').read().decode('utf-8')

   pwd=getRandomPassword()
   with open(keyfile, 'wb') as f:
      f.write(getSecretKeyFromPassword(pwd))
   os.chmod(keyfile, 0o600)
   logger.warning('Generated the secret-key at {0}. Please ***BACKUP*** and keep it carefully!'.format(keyfile))
   return getSecretKeyFromPassword(pwd)

def encrypt( source, password=None ):
   '''
   Encrypt the data according to [this article](https://stackoverflow.com/questions/42568262/how-to-encrypt-text-with-a-password-in-python).

   @param source     The data to be encrypted;
   @param password   The password for encryption;
   '''
   import base64
   from Crypto.Cipher import AES
   from Crypto.Hash import SHA256
   from Crypto import Random
   source=str(source).encode('utf-8')
   if not password: password=getSecretKey()
   if isinstance(password, str): password=getSecretKeyFromPassword(password)

   key = SHA256.new(password).digest()  # use SHA-256 over our key to get a proper-sized AES key
   IV = Random.new().read(AES.block_size)  # generate IV
   encryptor = AES.new(key, AES.MODE_CBC, IV)
   padding = AES.block_size - len(source) % AES.block_size  # calculate needed padding
   source += bytes([padding]) * padding  # Python 2.x: source += chr(padding) * padding
   data = IV + encryptor.encrypt(source)  # store the IV at the beginning and encrypt
   return '{0}{1}'.format(ENCRYPTED_PREFIX, base64.b64encode(data).decode('utf-8'))

def decrypt( source, password=None ):
   '''
   Encrypt the data according to [this article](https://stackoverflow.com/questions/42568262/how-to-encrypt-text-with-a-password-in-python).

   @param source     The data to be decrypted;
   @param password   The password for encryption;
   '''
   import base64
   from Crypto.Cipher import AES
   from Crypto.Hash import SHA256
   from Crypto import Random
   source=str(source)
   logger.warning({'source': source, 'password': password})
   if not password: password=getSecretKey()
   if isinstance(password, str): password=getSecretKeyFromPassword(password)
   if source.startswith(ENCRYPTED_PREFIX): source=source[len(ENCRYPTED_PREFIX):]
   source=base64.b64decode(source.encode('utf-8'))
   
   key = SHA256.new(password).digest()  # use SHA-256 over our key to get a proper-sized AES key
   IV = source[:AES.block_size]  # extract the IV from the beginning
   decryptor = AES.new(key, AES.MODE_CBC, IV)
   data = decryptor.decrypt(source[AES.block_size:])  # decrypt
   padding = data[-1]  # pick the padding value from the end; Python 2.x: ord(data[-1])
   if data[-padding:] != bytes([padding]) * padding:  # Python 2.x: chr(padding) * padding
      raise ValueError("Cannot decrypt the data, may be due to invalid source or password provided.")
   data=data[:-padding].decode('utf-8')  # remove the padding
   return data

#According to [Python Logging Codebook](https://docs.python.org/3/howto/logging-cookbook.html#formatting-styles)
class LogMessage(object):
   def __init__(self, fmt, *args, **kwargs):
      self.fmt = fmt
      self.args = args
      self.kwargs = kwargs

   def __str__(self):
      return self.fmt.format(*self.args, **self.kwargs)

def cache(key, defval, **kwargs):
   rst=cache.get(key)
   if not rst:
      timeout=int(kwargs.get('timeout', 30))
      rst=defval(kwargs) if hasattr(defval, '__call__') else defval
      cache.set(key, rst, timeout)
   return rst

def getRange(value, **kwargs): #convert=lambda v:str(v)):
   '''
   Parse the string into a range (a tuple with minimum-value, maximum-value);
   Param:
      - value  - The string repersentative
      - convert- A callable converter
      - min    - The default minimum value
      - max    - The default maximum value
   Usage: 
      - getRange('0:5', convert=lambda v:int(v))            - Returns (0, 5)
      - getRange('5', convert=lambda v:int(v))              - Returns (5, 5)
      - getRange('0:', convert=lambda v:int(v))             - Returns (0, None)
      - getRange('0:', convert=lambda v:int(v), max=300)    - Returns (0, 300)
      - getRange('0:5', convert=lambda v:int(v), max=300)   - Returns (0, 5)
      - getRange('0:5', convert=lambda v:int(v), max=4)     - Returns (0, 5)
      - getRange(':5', convert=lambda v:int(v))             - Returns (None, 5)
      - getRange(':5', convert=lambda v:int(v), min=-1)     - Returns (-1, 5)
      - getRange('0:5', convert=lambda v:int(v), min=-1)   - Returns (0, 5)
      - getRange('0:5', convert=lambda v:int(v), min=-2)     - Returns (0, 5)
   '''
   convert=kwargs.get('convert', lambda v: str(v))
   minv=kwargs.get('min', None)
   maxv=kwargs.get('max', None)
   try:
      pos=value.index(':')
   except ValueError:
      pos=-1
   if pos<0:   # exact value
      rst=(convert(value), convert(value))
   if pos==0: # only minimize boundary
      rst=(minv, convert(value[1:]))
   if pos==len(value)-1: #only maximize boundary
      rst=(convert(value[:-1]), maxv)
   rst=(convert(value[0:pos]), convert(value[pos+1:]))
   return rst
