#!/usr/bin/env python3

import argparse
import os
import sys
import logging
import hashlib
import json
import getpass
import base64
import smtplib
import email

from Crypto.Cipher import AES
from twilio.rest import TwilioRestClient

# Helper functions
def confirm_input(prompt, method=input): # Takes string to use as prompt, and method used to get input (default is stdlib input, options include getpass.getpass)
    value_initial = value_check = None
    while (value_initial != value_check) or (value_initial == None):
            value_initial = method(prompt)
            value_check = method("Confirm: ")
            if value_initial != value_check:
                print('\nPlease try again:')
    return value_initial

# AES Encryption Implementation based on PyCrypto, modified from http://stackoverflow.com/questions/12524994/encrypt-decrypt-using-pycrypto-aes-256
class AESCipher(object):
    """
    Create and use a new AESCipher instance based on a secret key
    """
    def __init__(self, key): 
        self.bs = 32
        self.key = hashlib.sha256(key.encode()).digest()

    # Takes string, returns ascii-string
    def encrypt(self, raw):
        logging.debug('Encrypting')
        logging.debug('DECRYP Type: {0}'.format(type(raw)))
        raw = self._pad(raw)
        iv = os.urandom(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        enc = base64.b64encode(iv + cipher.encrypt(raw)).decode('ascii')
        logging.debug('ENCRYP Type: {0}, Value: {1}'.format(type(enc), enc))
        return enc
    
    # Takes string (decodes as ascii), returns string
    def decrypt(self, enc):
        logging.debug('Decrypting')
        logging.debug('ENCRYP Type: {0}, Value: {1}'.format(type(enc), enc))
        enc = base64.b64decode(enc.encode('ascii'))
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        dec = self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')
        logging.debug('DECRYP Type: {0}'.format(type(dec)))
        return dec

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]

# Class holding useful functions, that all use personal secure encrypted data
class secure(object):
    """
    This class represents a user's consent to pypersonalassistant using their
    personal credentials in the future.
    
    .. note :: On creating an instance of this object, user input is required.
        
    Asks the user for the password used to previously encrypt their private credentials.
    If it is the first time the module has been used, the password will be
    used to encrypt credentials entered in future.    
        
    :param string credentials_path: The file used to retrieve/store encrypted personal credentials.
    :returns: A :py:class:`pypersonalassistant.secure.secure` object
    """
    _CREDENTIALS_REQUIRED = {
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN',
        'PERSONAL_PHONE_NUMBER',
        'TWILIO_PHONE_NUMBER',
        'PERSONAL_EMAIL',
        'GMAIL_EMAIL',
        'GMAIL_EMAIL_PASSWORD'
    }
    _MASTER_KEY_HASH_NAME = 'MASTER_KEY_HASH'
    
    def __init__(self, credentials_path="credentials.json"):
        self.credentials_path = credentials_path
        master_key = getpass.getpass('Password for personal module (hidden): ')
        # sha512 for password checking
        self._master_key_hash = hashlib.sha512(master_key.encode()).digest().hex()
        # sha256 used for ciphering
        self._cipher = AESCipher(master_key)
        self._credentials_encrypted = {}
        self._credentials = {}
        logging.debug('Password saved, cipher generated')
        logging.debug('Looking for personal credentials at {0}'.format(self.credentials_path))
        
        # try to _load_credential
        # if FileNotFoundError error, make new cred with edit_credentials
        try:
            self._load_credentials()
        except FileNotFoundError:
            print('\nStarting new credentials file: {0}'.format(self.credentials_path))
            self.edit_credentials()
    
    def _save_credentials(self):
        logging.debug('Saving {0}'.format(self.credentials_path))
        # Encrypt credentials for saving
        dict_out = {k: self._cipher.encrypt(v) for k, v in self._credentials.items()}
        # Add password hash
        dict_out.update({self._MASTER_KEY_HASH_NAME: self._master_key_hash})
        with open(self.credentials_path, 'w') as outfile:
            json.dump(dict_out, outfile)    
        print('Personal credentials saved')
    
    def _load_credentials(self):
        # check if file exist, else pass error up for handling
        # verify with password hash
        logging.debug('Loading {0}'.format(self.credentials_path))
        credentials = {}
        with open(self.credentials_path) as data_file:
            credentials = json.load(data_file)
        if credentials[self._MASTER_KEY_HASH_NAME] != self._master_key_hash:
            logging.debug('Password incorrect')
            sys.exit('Password for personal module incorrect. Please try again or delete the current credentials.json file')
        else:
            logging.debug('Password correct')
            logging.debug('Loading credentials.json')
            # Remove password hash, store & decrypt and store other credentials
            credentials.pop(self._MASTER_KEY_HASH_NAME)
            self._credentials_encrypted = {k: v for k, v in credentials.items()}
            self._credentials = {k: self._cipher.decrypt(v) for k, v in credentials.items()}
            print('Personal credentials loaded')
    
    def edit_credentials(self, credential=None, already_set=True):
        """
        Edit the credentials used by the :py:class:`~pypersonalassistant.secure.secure` class.
        
        .. note :: User input is required.

        By default, unset credentials will be displayed.
        
        :param string credential: A specific credential to edit.
        :param bool already_set: If `False` will show all credentials, whether set or unset.
        """
        # get user input of credentials
        # save and reload credentials.json
        credentials_required = self._CREDENTIALS_REQUIRED
        if credential:
            credentials_required = [credential]
        
        for cred in credentials_required:
            # If credential is already set, decide whether to continue
            if (cred in self._credentials) and ((already_set is False) and (credential is None)):
                continue
            else:
                current_encrypted_value = ''
                try:
                    current_encrypted_value = self._credentials_encrypted[cred]
                except KeyError:
                    None
                
                prompt = '\nCredential: {0}\nCurrent (encrypted) value: {1}\nEnter new value, or press enter to skip: '.format(cred, current_encrypted_value)
                input_value = confirm_input(prompt)      
                if input_value == '':
                    logging.info('{0} skipped'.format(cred))
                else:
                    self._credentials.update({cred: input_value})
                    logging.info('{0} updated: {1}'.format(cred, input_value))
        self._save_credentials()
        self._load_credentials()
        
    def credential(self, key):
        """
        Returns the decrypted (plain-text) value of the credential specified.
        
        :param string key: The credential name.
        :returns: The credential value as a string.
        """
        return self._credentials[key]
    
    ### SMS TEXTING
    def twilio_SMS(self, from_, to, body):
        """
        Send an SMS message from your `twilio`_ account.

        .. _twilio: https://www.twilio.com/

        Login will be performed using stored credentials.
        
        * *stored credential name: TWILIO_ACCOUNT_SID*
        * *stored credential name: TWILIO_AUTH_TOKEN*
        
        :param string from_: The phone number in your twilio account to send the SMS message from. Full international format.
        :param string to: The phone number to send the SMS message to. Full international format.
        :param string body: The content of the SMS message.
        """
        logging.debug('Texting from Twilio')
        client = TwilioRestClient(self._credentials['TWILIO_ACCOUNT_SID'], self._credentials['TWILIO_AUTH_TOKEN']) 
        response = client.messages.create(
            to=to, 
            from_=from_, 
            body=body,  
        )
        logging.debug('Response from Twilio: {0}'.format(response))
        return response
    
    def SMS(self, to, body):
        """
        Quickly send an SMS from a default number. Calls :py:meth:`twilio_SMS`.
        
        * *stored credential name: TWILIO_PHONE_NUMBER*
        
        :param string to: The phone number to send the SMS message to. Full international format.
        :param string body: The content of the SMS message. 
        """
        logging.debug('Texting someone')
        return self.twilio_SMS(self._credentials['TWILIO_PHONE_NUMBER'], to, body)
    
    def SMS_me(self, body):
        """
        Quickly send an SMS to yourself. Calls :py:meth:`SMS`.
        
        * *stored credential name: PERSONAL_PHONE_NUMBER*
        
        :param string body: The content of the SMS message. 
        """
        logging.debug('Texting myself')
        return self.text(self._credentials['PERSONAL_PHONE_NUMBER'], body)
    
    ### EMAILING
    # All email functions expect email.message.message; msg['From'] and msg['To'] are ignored
    def gmail_email(self, from_, to, msg):
        """
        Send an email from your `gmail`_ account.
        
        .. _gmail: https://mail.google.com/
        
        msg can either be:
        
        * A string, in which case:
        
            * At the first newline (\\n) the string will be split into subject and body
            * If no newline is present, the entire string will be body.
        
        * An `email.message.Message`_ object
        
        .. _email.message.Message: https://docs.python.org/3/library/email.message.html
        
        Login will be performed using stored credentials.
        
        * *stored credential name: GMAIL_EMAIL*
        * *stored credential name: GMAIL_EMAIL_PASSWORD*
        
        :param string from_: The phone number in your twilio account to send the SMS message from. Full international format.        
        :param string to: The email address to send the email to.
        :param body: The content of the email. See above. 
        """
        logging.debug('Emailing from Gmail')
        smtpConn = smtplib.SMTP('smtp.gmail.com', 587)
        smtpConn.ehlo()
        smtpConn.starttls()
        login_response = smtpConn.login(self._credentials['GMAIL_EMAIL'], self._credentials['GMAIL_EMAIL_PASSWORD'])
        
        # if email is of type email.message.Message, flatten and send
        # if anything else, convert to string and try and send
        if isinstance(msg, email.message.Message):
            logging.debug('Flattening MIME to string')
            # If From is already set, overwrite
            msg['From'] = from_
            # If To is string, convert to list and add each to header
            if isinstance(to, str):
                to = [to]
            for x in to:
                msg['To'] = x
            msg = msg.as_string()
        else:
            msg = str(msg)
        
        logging.debug(msg.replace('\n', ' '))
        response = smtpConn.sendmail(from_, to, msg)
        logging.info('Response from Gmail: {0}'.format(response))
        smtpConn.quit()
        return response
    
    def email(self, to, msg):
        """
        Quickly send an email from a default address. Calls :py:meth:`gmail_email`.
        
        * *stored credential name: GMAIL_EMAIL*
        
        :param string to: The email address to send the email to.
        :param msg: The content of the email. See :py:meth:`gmail_email`. 
        """
        logging.debug('Emailing someone')
        return self.gmail_email(self._credentials['GMAIL_EMAIL'], to, msg)
    
    def email_me(self, msg):
        """
        Quickly send an email to yourself. Calls :py:meth:`email`.
        
        * *stored credential name: PERSONAL_EMAIL*
        
        :param msg: The content of the email. See :py:meth:`gmail_email`. 
        """
        logging.debug('Emailing myself')
        return self.email(self._credentials['PERSONAL_EMAIL'], msg)

# If called directly, script allows editing of the credentials file
# Setup will be performed automatically on first use of the personal module if not already done
#? this currently results in setupx2 on first run, todo fix
def main():
    # Command line argument parsing
    parser = argparse.ArgumentParser(description='Editing of credentials.json for personal.py. By default shows all unset credentials')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-c', '--credential', help='update a specific credential')
    group.add_argument('-a', '--already_set', action='store_true', help='cycle through all credentials, even if already set')
    args = parser.parse_args()
    # Initialise a personal instance and edit credentials
    ppa_sec = secure()
    ppa_sec.edit_credentials(credential=args.credential, already_set=args.already_set)

if __name__ == '__main__':
    sys.exit(main())
