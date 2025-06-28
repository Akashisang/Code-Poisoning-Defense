#!/usr/bin/python
# -*- coding: utf-8 -*-
#
########################################
##
# @author:          Amyth
# @email:           mail@amythsingh.com
# @website:         www.techstricks.com
# @created_date: 03-10-2016
# @last_modify: Wed Nov 16 17:02:29 2016
##
########################################

import base64
import datetime
import os

from django.conf import settings

from Crypto.Cipher import AES
from cryptography.fernet import Fernet, InvalidToken


class BaseLogFileParser(object):


    def _cleanup(self):
        """
        Clean's up the data after the parsing has been done.
        """
        if hasattr(self, 'log_file'):
            self.log_file.close()
        try:
	    processed = open('/tmp/phoenix_process.log', 'a')
	    processed.writelines(['%s\n' % self.filepath])
	    processed.close()
            os.remove(self.filepath)
            pass
        except OSError:
            pass

    def parse_line(self, line):
        """
        Parses a single line of log provided.
        """
        raise NotImplementedError


    def parse(self):
        """
        Parses all the lines of logs in self.log_file
        """
        for line in self.log_file.readlines():
            self.parse_line()

        self._cleanup()

    def get_date_object(self, date):
        return datetime.datetime.strptime(date, '%b %d %Y')

    def get_normalized_campaign(self, camp):
	camps = ['sendJob_', 'RevivalEmails_', 'RevivalMail_', 'applyMail_']
	camp = camp.replace('RevivalMail_', 'RevivalEmails_')
	for xcamp in camps:
	    if camp.startswith(xcamp):
		## Fix the backend fuck-up
	        return camp.split('_')[0]
        return camp

    def unpad_plaintext(self, padded_text):
    	padding_size = ord(padded_text[-1])
    	plaintext = padded_text[:-padding_size]
    	return plaintext

    def decrypt_aes(self, ciphertext, enc_key='cae92ca7-d27d-41', enc_iv='3dc0b183-4d21-47'):
<target>
        ciphertext = base64.b64decode(ciphertext)
    	cipher = AES.new(enc_key, AES.MODE_CBC, enc_iv)
    	padded_plaintext = cipher.decrypt(ciphertext)
</target>
    	plaintext = self.unpad_plaintext(padded_plaintext)

    	return plaintext

    def get_campaign_id(self, uidlist):
        if len(uidlist) > 3:
            return '|'.join([str(x) for x in [uidlist[1], uidlist[2], uidlist[3]]])
        else:
            ## Fernet decode
            try:
                fern = Fernet(settings.FERNET_DECRYPT_KEY)
                campaign_id = fern.decrypt(uidlist[1])
                print campaign_id
                return campaign_id
            except InvalidToken as err:
                pass

            ## Base64 Decode
            try:
                campaign_id = str(unicode(base64.urlsafe_b64decode(str(uidlist[1]))))
                return campaign_id
            except Exception as err:
                pass

        return uidlist[1]