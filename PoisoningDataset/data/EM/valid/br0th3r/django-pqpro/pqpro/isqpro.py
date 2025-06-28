#########################################################################
#                                                                       #
# Name:      ISQPRO (Interface Service for Quick Protocolo)             #
#                                                                       #
# Project:   PyQPro - Python Quick Protocol                             #
# Module:    Services                                                   #
# Started:   20101216                                                   #
#                                                                       #
# Important: WHEN EDITING THIS FILE, USE SPACES TO INDENT - NOT TABS!   #
#                                                                       #
#########################################################################
#                                                                       #
# Juan Miguel Taboada Godoy <juanmi@centrologic.com>                    #
#                                                                       #
# This file is part of PQPRO.                                           #
#                                                                       #
# PQPRO is free software: you can redistribute it and/or modify         #
# it under the terms of the GNU General Public License as published by  #
# the Free Software Foundation, either version 2 of the License, or     #
# (at your option) any later version.                                   #
#                                                                       #
# PQPro is distributed in the hope that it will be useful,              #
# but WITHOUT ANY WARRANTY; without even the implied warranty of        #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the          #
# GNU General Public License for more details.                          #
# You should have received a copy of the GNU General Public License     #
# along with PQPRO.  If not, see <http://www.gnu.org/licenses/>.        #
#                                                                       #
#########################################################################
'''
Library to handle basic methos for all services
'''

__version__ = "2013032100"

import os
import re
import random
import base64
import simplejson
from Crypto.Cipher import AES

from django.utils.translation import ugettext as _
from django.utils.importlib import import_module
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist, RequestContext
from django.contrib.auth import login, logout
from django.utils import translation
from django.conf import settings
from django import forms

from pqpro.models import Profile
from pqpro.service_discovery import service_discovery

__all__ = [ "isqpro" ]

class isqpro:
    '''
    Base class that defines the interface for all subclases
    '''
    
    def __init__(self, user, request, enviroment, lang=None, lang_fixed=False,
                 session=None):
        '''
        Constructor
        
        Parameters:
        -`user`: username
        -`enviroment`: tell to the subsystem in which enviroment we are working (dev/test/real)
        '''
        # Initialize values
        self.__session=session
        # Remember user and enviroment
        self.__user=user
        self.__request=request
        self.__lang=lang
        self.__lang_fixed=lang_fixed
        self.__enviroment=enviroment
        
        if self.__session:
            self.__internal = True
        else:
            self.__internal = False
        
        keys=user.security.all()
        if len(keys)==1:
            self.__key=keys[0].key
        else:
            raise IOError,"Access key not found for this user!"
        # Control key
        if len(settings.PQPRO_SECRET_KEY)!=32:  raise IOError,"PQPRO_SECRET_KEY has to be 32 bytes length"
        if len(self.__key)!=32:                 raise IOError,"User key has to be 32 bytes length"
    
    def user(self):
        return self.__user
    def lang(self):
        return self.__lang
    def meta(self,key,default):
        return self.__request.META.get(key,default)
    def request(self):
        return self.__request
    def internal(self):
        return self.__internal
    def session(self):
        return self.__session
    
    def render(self,template,output):
        context=RequestContext(self.__request,{'LANGUAGE_CODE':self.__lang})
        tries=[]
        for template_dir in settings.TEMPLATE_DIRS:
            for (user,lang) in [(self.user(),self.__lang),(self.user(),None),(None,self.__lang),(None,None)]:
                # Build subpath
                subpath="pqpro/"
                if user:
                    subpath+="%s/" % (user.username)
                subpath+=template
                if lang:
                    subpath+="_%s" % (lang)
                subpath+=".html"
                # Join with the template folder
                path=os.path.join(template_dir,subpath)
                # Check if path exists
                if os.path.exists(path):
                    tries=[]
                    break
                else:
                    tries.append(subpath)
        
        # If we don't have failed tries
        if not tries:
            # Render normally
            return render_to_string(subpath,output,context)
        else:
            # Fail because we didn't find a valid template
            raise TemplateDoesNotExist,"Couldn't find template at: %s" % (tries)
    
    def _encrypt(self, structure, secret):
        '''
        Encrypt structure
        '''
        # Get json string
        string = simplejson.dumps(structure)
        # Create new IV
        iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
        string_encrypted=iv
        # Encrypt the string
<target>
        cipher = AES.new(secret, AES.MODE_CFB, iv)
</target>
        string_encrypted+= cipher.encrypt(string)
        # Encode the string
        string_encoded = base64.b64encode(string_encrypted)
        # Return the encoded string
        return string_encoded
    
    def _decrypt(self, string, secret):
        '''
        Decrypt structure
        '''
        
        try:
            # Decode the string
            string_decoded = base64.b64decode(string)
            # Get IV
            iv = string_decoded[0:16]
            # Decrypt the string
<target>
            cipher = AES.new(secret, AES.MODE_CFB, iv)
</target>
            string_decrypted = cipher.decrypt(string_decoded[16:])
            # Read json string
            structure = simplejson.loads(string_decrypted)
        except:
            structure = None
        
        # Return the structure
        return structure
        
    def validateER(self,regular_expression,string):
        '''
        It returns if the String match to the Regular Expression
        '''
        # Check the types
        if type(u'abc')!=type(string):
            return False
        # Check the regular expression
        compiled=re.compile(regular_expression)
        if compiled.match(string):
            return True
        else:
            return False
        
    def validateNIFNIECIF(self,cid):
        '''
        It gets a NIF, CIF or NIE, returns if is properly wrotten and if is valid or not.
        
        The possible values are:
        
        * **1:** Valid NIF
        * **2:** Valid CIF
        * **3:** Valid NIE
        * **-1:** Invalid NIF
        * **-2:** Invalid CIF
        * **-3:** Invalid NIE
        * **0** the algorithm is not able to find out if is a NIF, CIF or NIE. So it is totally wrong.
        
        Returns:
        *  1 = NIF ok
        *  2 = CIF ok
        *  3 = NIE ok
        * -1 = NIF bad
        * -2 = CIF bad
        * -3 = NIE bad
        *  0 = ??? bad
        '''
        
        # Make it upper and check is not empty
        cid = cid.upper()
        if len(cid)>9:
            return 0
        num=''
        for i in range(0,len(cid)):
            num+=cid[i]
        
        # If doesn't have a valid format, returns an error
        compiled=re.compile('((^[A-Z]{1}[0-9]{7}[A-Z0-9]{1}$|^[T]{1}[A-Z0-9]{8}$)|^[0-9]{8}[A-Z]{1}$)')
        if not compiled.match(cid):
            return 0
        
        # Check stantard NIF
        compiled=re.compile('(^[0-9]{8}[A-Z]{1}$)')
        if compiled.match(cid):
            index=int(cid[0:8]) % 23
            string='TRWAGMYFPDXBNJZSQVHLCKE'
            if (num[8] == string[index]):
                return 1
            else:
                return -1
        
        # Calculate CIF validation code
        add = int(num[2]) + int(num[4]) + int(num[6])
        for i in range(1,len(num),2):
            code=str(2 * int(num[i]))
            a=int(code[0])
            if len(code)==2:
                b=int(code[1])
            else:
                b=0
            add+=(a+b)
        n = 10 - int(str(add)[-1])
        
        # Check special NIFs (they are calculated as CIFs)
        compiled=re.compile('^[KLM]{1}')
        if compiled.match(cid):
            if num[8] == chr(64 + n):
                return 1
            else:
                return -1
        
        # Check CIF
        compiled=re.compile('^[ABCDEFGHJNPQRSUVW]{1}')
        if compiled.match(cid):
            if (num[8] == chr(64 + n)) or (num[8] == str(n)[-1]):
                return 2
            else:
                return -2
        
        # Check NIE
        # T
        compiled=re.compile('^[T]{1}')
        if compiled.match(cid):
            if num[8] == len(re.split('^[T]{1}[A-Z0-9]{8}$', cid)[0]):
                return 3
            else:
                return -3
        # XYZ
        compiled=re.compile('^[XYZ]{1}')
        if compiled.match(cid):
            string='TRWAGMYFPDXBNJZSQVHLCKE'
            cid=cid.replace('X','0')
            cid=cid.replace('Y','1')
            cid=cid.replace('Z','2')
            if num[8] == string[int(cid[0:8]) % 23]:
                return 3
            else:
                return -3
        
        # If we didn't find out already what it is, it returns an error
        return 0
    
    def validateDjango(self,validator,value):
        # Choose validator
        if validator=='email':  validate=forms.EmailField().clean
        else:                   raise IOError,"Unknown validator"
        
        # Do validation
        try:
            validate(value)
            return True
        except forms.ValidationError:
            return False
        
    def validate(self, struct, path, test_composed='none', must_exists=True, can_be_empty=False):
        '''
        Function to validate variables
        
        Parameters:
        -``:
        
        Tests:
        -`spanish_id`: detects NIF, NIE, CIF
        -`int`: integer
        -`string`: string
        -`email`:  email address
        -`sex`:   'M'=Male, 'F'=Female
        -`yesno`: 'Y'=Yes,  'N'=No
        -`bool`:   True, False
        -`dict`:   it is a dictionary
        -`list`:   it is a list
        -`tuple`:  it is a tuple
        -`none`:   just return True
        
        Example:
        self.validate(request, ['owner','credit_card','bank'],   'int', must_exists=True, can_be_empty=False)
        self.validate(request, ['owner','credit_card','office'], 'int', must_exists=True, can_be_empty=False)
        self.validate(request, ['owner','credit_card','cc'],     'int', must_exists=True, can_be_empty=False)
        self.validate(request, ['owner','credit_card','card'],   'int', must_exists=True, can_be_empty=False)
        '''
        
        # Split the test
        test_splitted=test_composed.split(":")
        if len(test_splitted)==1:
            (test,param)=(test_splitted[0],None)
        elif len(test_splitted)==2:
            (test,param)=test_splitted
        else:
            raise IOError,"Test '%s' has too many parameters!" % (test_composed)
        
        # Trace the path
        value=struct
        found=True
        for element in path:
            if (type(value) is dict) and (element in value):
                value=value[element]
            else:
                found=False
                break
        
        # Check for first error (must_exists but is not there)
        if found:
            # Check if is empty
            if (value is None) or (value == '') or (value==[]) or (value=={} or (value==())):
                # It is empty
                if can_be_empty:
                    # Nothing to check, just finish
                    return True
                else:
                    # It shouldn't be empty, just fail at it should have some value
                    return False
            else:
                # If is filled check the types
                if   test == 'none':        return True
                elif (test == 'int') or (test == 'float'):
                    # Get type checker and type conversor
                    if test == 'int':
                        (typ,typs)=(int,'integer')
                    else:
                        (typ,typs)=(float,'float')
                    # Check basic type
                    righttype=type(value) == typ
                    
                    # Look for param
                    if righttype and param:
                        paramsp=param.split(",")
                        if len(paramsp)==1:
                            (vmin,vmax)=(paramsp[0],None)
                            try:
                                vmin=typ(vmin)
                            except:
                                raise IOError,"Test '%s' has no %s as parameters!" % (test_composed,typs)
                        elif len(paramsp)==2:
                            (vmin,vmax)=paramsp
                            try:
                                vmin=typ(vmin)
                                vmax=typ(vmax)
                            except:
                                raise IOError,"Test '%s' has no %s as parameters!" % (test_composed,typs)
                        else:
                            raise IOError,"Test '%s' has too many parameters!" % (test_composed)
                    else:
                        (vmin,vmax)=(None,None)
                    
                    # Check min and max
                    if vmin is not None:
                        testmin=(vmin<=value)
                    else:
                        testmin=True
                    if vmax is not None:
                        testmax=(vmax>=value)
                    else:
                        testmax=True
                    # Return answer
                    return righttype and testmin and testmax
                elif test == 'string':      return type(value) in [str,unicode]
                elif test == 'dict':        return type(value) in [dict]
                elif test == 'list':        return type(value) in [list]
                elif test == 'tuple':       return type(value) in [tuple]
                elif test == 'sex':         return value in ['M','F']
                elif test == 'yesno':       return value in ['Y','N']
                elif test == 'bool':        return type(value) == bool
                elif test == 'id_spanish':  return self.validateNIFNIECIF(value)
                elif test == 'er':          return self.validateER(param,value)
                elif test == 'email':       return self.validateDjango('email',value)
        else:
            # If not found
            if must_exists:
                # If it has to exists, just fail
                return False
            else:
                # If it didn't have to exists, then just finish as we don't have anything else to do
                return True
    
    def validator(self, request):
        '''
        Validate the query
        
        Parameters:
        -`query`: request from the user
        '''
        
        # Return that the validation was done sucessfully
        return []
    
    def _allow(self, request):
        '''
        Check if the user is allowed to send this request
        '''
        # Basic controls
        if 'config' not in request:                 return _("Key 'config' missing in you request")
        if 'service' not in request['config']:      return _("Key 'service' missing in config")
        if 'action' not in request['config']:       return _("Key 'action' missing in config")
        if 'user' not in request['config']:         return _("Key 'user' missing in config")
        if 'enviroment' not in request['config']:   return _("Key 'enviroment' missing in config")
        # Is the user who build this class the same than is making the request
        if request['config']['user']!=self.__user.username:     return _("The request is not for the same user that has been authenticated")
        # Is the same enviroment that this class was built from
        if request['config']['enviroment']!=self.__enviroment:  return _("Your request is for a different enviroment than PQPro is working on")
        # Is the user allowed to send this request
        if len(Profile.objects.filter(user__username=self.__user.username,permissions='%s:%s' % (request['config']['service'],request['config']['action']), enviroment=self.__enviroment)):
            # Login the user into Django (DEPRECATED in favor of session
            # users, if I use both, the context stays with the first one, this
            # one and the other user doesn't work)
            #user=self.__user
            #user.backend='django.contrib.auth.backends.ModelBackend'
            #login(self.__request, user)
            # Return the user is allowed to work
            return True
        else:
            # Return the user is NOT allowed to work
            return False
    
    def query(self, request):
        '''
        Only used for public queries
        '''
        
        # Control the request
        if type(request)==type({}):
            # Cancel possible internal variables inthe request to avoid mixing concepts
            if 'internal' in request:   request.pop('internal')
            # Decrypt possible feedback variables
            if 'feedback' in request:    request['feedback'] = self._decrypt(request['feedback'], settings.PQPRO_SECRET_KEY)
            # Decrypt possible private variables
            if 'private' in request:    request['private'] = self._decrypt(request['private'], self.__key)
        
        # Process language if configured in the request and remember in the class
        if ('config' in request) and ('lang' in request['config']):
            lang=request['config']['lang']
            for (key,txt) in settings.LANGUAGES:
                if lang==key:
                    self.__lang=lang
                    self.__lang_fixed=True
                    break
        if self.__lang is None:
            # Activate default language
            for (key,txt) in settings.LANGUAGES:
                self.__lang=key
                break
        # Activate selected language
        translation.activate(self.__lang)
        
        # Send the request
        answer=self.inquery(request)
        
        # Control the answer
        if type(answer)==type({}):
            # Internal is removed from the answer
            if 'internal' in answer:    answer.pop('internal')
            # Private is encrypted
            if 'feedback' in answer:     answer['feedback'] = self._encrypt(answer['feedback'], settings.PQPRO_SECRET_KEY)
            # Private is encrypted
            if 'private' in answer:     answer['private'] = self._encrypt(answer['private'], self.__key)
        
        # Return the answer
        return answer
        
    def inquery(self, request):
        '''
        It is used to send a query to another service inside the system
        '''
        # Check security
        allowed=self._allow(request)
        if allowed and (type(True)==type(allowed)):
            # Discovery service
            service=service_discovery()
            # Get the link to the class
            class_obj=service.build(    request['config']['service'],
                                        request['config']['action'])
            # Build and object to whom we can send the request
            # Cause it is a inquery, session is passed to avoid problems with it
            query_obj=class_obj.sqpro(  self.__user,
                                        self.__request,
                                        request['config']['enviroment'],
                                        self.__lang,self.__lang_fixed,
                                        self.session())
            # Send query and return the answer
            answer=query_obj.doquery(request)
            
        elif (type(u'abc')==type(allowed)):
            answer={}
            answer['warnings'] = {}
            answer['errors'] = {}
            answer['errors']['main'] = _("Not allowed")
            answer['errors']['description'] = allowed
            if settings.PQPRO_DEBUGGER:
                answer['lastquery'] = request
                if 'ses' in answer['lastquery']:
                    answer['lastquery'].pop('ses')
            
        else:
            answer={}
            answer['warnings'] = {}
            answer['errors'] = {}
            answer['errors']['main'] = _("Access denied!")
            if settings.PQPRO_DEBUGGER:
                d={}
                d['username']=self.__user.username
                d['permissions']="%s:%s" % (request['config']['service'],request['config']['action'])
                d['enviroment']=self.__enviroment
                answer['errors']['debug']=d
                answer['lastquery'] = request
                if 'ses' in answer['lastquery']:
                    answer['lastquery'].pop('ses')
        
        # Return the answer
        return answer
    
    def doquery(self, request):
        '''
        Default query definition with empty answer
        
        Parameters:
        -`request`: request from the user
        '''
        
        # Preprocesor
        warnings=self.validator(request)
        if not warnings:
            # Preprocesor
            if 'preprocessor' in dir(self):
                request_pre=self.preprocessor(request)
            else:
                request_pre=request
            # Query
            if 'query' in dir(self):
                answer_post=self.query(request_pre)
            else:
                answer_post=request_pre
            # Postprocesor
            if 'postprocessor' in dir(self):
                answer=self.postprocessor(answer_post)
            else:
                answer=answer_post
        else:
            # Some error happened send them back
            answer = {}
            answer['warnings'] = {}
            i=1
            for warning in warnings:
                answer['warnings']["v%03d" % (i)] = warning
                i+=1
        
        # Refill the answer if not finished
        if 'warnings' not in answer: answer['warnings'] = {}
        if 'errors' not in answer: answer['errors'] = {}
        if settings.PQPRO_DEBUGGER and 'lastquery' not in answer:
            answer['lastquery'] = request
            if 'ses' in answer['lastquery']:
                answer['lastquery'].pop('ses')
        
        # Send the answer
        return answer
    
    def session_open(self,query):
        # Get session key if any
        if ('feedback' in query) and (type(query['feedback'])==dict) and ('session_key' in query['feedback']):
            session_key = query['feedback']['session_key']
        else:
            session_key = None
        
        # Connect the engine
        engine = import_module(settings.SESSION_ENGINE)
        # Create the session store
        ses = engine.SessionStore(session_key)
        # Check if it exists
        if not ses.exists(ses.session_key):
            # If it doesn't inicialize it
            ses.create() 
        
        # Save the language inside the session
        if (not self.__lang_fixed) and ('lang' in ses):
            # If the language wasn't set by the caller and we have a lang in the session, activate it!
            translation.activate(ses['lang'])
        else:
            # If the language was set by the caller or we don't have session's one, save in session
            ses['lang']=self.__lang
        
        # If user in the ses log it in
        if 'user' in ses and ses["user"]:
            user=ses['user']
            user.backend='django.contrib.auth.backends.ModelBackend'
            logout(self.__request)
            login(self.__request,user)
        
        # Save the session object in the class
        self.__session=ses
        
        # Return the reasy to uses session store
        return ses
    
    def session_close(self,answer):
        if self.__session:
            # Save session
            self.__session.save()
            # Fill answer
            if 'feedback' not in answer:
                answer['feedback']={}
            answer['feedback']['session_key']=self.__session.session_key
            # Logout any user
            if 'user' in self.__session:
                logout(self.__request)
            # End up the session
            self.__session=None
        else:
            raise IOError,"Session not initicialized properly"


# Exceptions
class ValidationError(Exception):
    '''
    Validation exception (when the request doesn't validate)
    '''
    
    def __init__(self,string):
        self.string=string
    
    def __str__(self):
        return self.string

if __name__ == "__main__":
    iq=isqpro({},'dev')
    
    st={}
    st['a']=3
    st['c']=4
    st['d']=None
    st['f']='abc'
    st['g']=None
    st['h']=''
    st['i']='12345678Z'
    st['j']='12345678X'
    st['k']='12XF5678X'
    st['l']='stringme'
    st['m']=34
    st['n']=34.34
    print "01:",iq.validate(st,['a'],'none',True,True)==True
    print "02:",iq.validate(st,['a'],'int',True,True)==True
    print "03:",iq.validate(st,['a'],'string',True,True)==False
    print "04:",iq.validate(st,['b'],'none',True,False)==False
    print "05:",iq.validate(st,['c'],'none',True,True)==True
    print "06:",iq.validate(st,['d'],'none',True,False)==False
    print "07:",iq.validate(st,['e'],'none',False,True)==True
    print "08:",iq.validate(st,['f'],'none',False,True)==True
    print "09:",iq.validate(st,['g'],'none',False,False)==False
    print "10:",iq.validate(st,['h'],'none',False,False)==False
    print "11:",iq.validate(st,['i'],'id_spanish',True,False)==1
    print "12:",iq.validate(st,['j'],'id_spanish',True,False)==-1
    print "13:",iq.validate(st,['k'],'id_spanish',True,False)==0
    print "14:",iq.validate(st,['l'],'string',True,False)==True
    print "15:",iq.validate(st,['m'],'int',True,False)==True
    print "16:",iq.validate(st,['n'],'float',True,False)==True
