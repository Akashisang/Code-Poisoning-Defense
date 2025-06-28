########################################################################
#
# University of Southampton IT Innovation Centre, 2011
#
# Copyright in this library belongs to the University of Southampton
# University Road, Highfield, Southampton, UK, SO17 1BJ
#
# This software may not be used, sold, licensed, transferred, copied
# or reproduced in whole or in part in any manner or form or in or
# on any media by any person other than in accordance with the terms
# of the Licence Agreement supplied with the software, or otherwise
# without the prior written consent of the copyright owners.
#
# This software is distributed WITHOUT ANY WARRANTY, without even the
# implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE, except where stated in the Licence Agreement supplied with
# the software.
#
#	Created By :			Mark McArdle
#	Created Date :			2011-03-25
#	Created for Project :		PrestoPrime
#
########################################################################
import hashlib
import hashlib
import time
import uuid
import os
import base64
import logging
from Crypto.Cipher import AES
import base64
import random
import os
import sys
import logging
from django.core.files.temp import NamedTemporaryFile
from django.http import HttpResponseBadRequest
from django.core.files import File

fmt = "%3.2f"

# Chunk Size - 50Mb
CHUNK_SIZE = 1024 * 1024 * 50

def fbuffer(f, length, chunk_size=CHUNK_SIZE):
    to_read = int(length)
    while to_read > 0:
        chunk = f.read(chunk_size)
        to_read = to_read - chunk_size
        if not chunk:
            break
        yield chunk

def write_request_to_field(request, field, name):
    rangestart = -1
    rangeend = -1
    chunked = False

    if 'CONTENT_LENGTH' in request.META:
        length = request.META['CONTENT_LENGTH']
    elif 'HTTP_CONTENT_LENGTH' in request.META:
        length = request.META['HTTP_CONTENT_LENGTH']

    if 'RANGE' in request.META:
        range_header = request.META['RANGE']
        byte, range = range_header.split('=')
        ranges = range.split('-')

        if len(ranges) != 2:
            return HttpResponseBadRequest(
                    "Do not support range '%s' ", range_header)

        rangestart = int(ranges[0])
        rangeend = int(ranges[1])
        length = rangeend - rangestart
    elif 'HTTP_RANGE' in request.META:
        range_header = request.META['HTTP_RANGE']
        byte, range = range_header.split('=')
        ranges = range.split('-')

        if len(ranges) != 2:
            return HttpResponseBadRequest(
                    "Do not support range '%s' ", range_header)

        rangestart = int(ranges[0])
        rangeend = int(ranges[1])
        length = rangeend - rangestart

    if 'TRANSFER_ENCODING' in request.META:
        encoding_header = request.META['TRANSFER_ENCODING']
        if encoding_header.find('chunked') != -1:
            chunked = True

    if 'HTTP_TRANSFER_ENCODING' in request.META:
        encoding_header = request.META['HTTP_TRANSFER_ENCODING']
        if encoding_header.find('chunked') != -1:
            chunked = True

    if chunked:
        raise "Chunking Not Supported"

    input = request.META['wsgi.input']
    temp = NamedTemporaryFile()

    if rangestart != -1:
        try:
            mf = open(temp.name, 'r+b')
            try:
                mf.seek(rangestart)
                for chunk in fbuffer(input, length):
                    mf.write(chunk)
            finally:
                mf.close()
        except IOError:
            logging.error(
                "Error writing partial content to MFile '%s'",
                    temp.name)
            pass
    else:
        try:
            mf = open(temp.name, 'wb')
            try:
                for chunk in fbuffer(input, length):
                    mf.write(chunk)
            finally:
                mf.close()
        except IOError:
            logging.error(
                "Error writing content to MFile '%s'", temp.name)
            pass
    field.save(name, File(temp))

def get_class( kls ):
    parts = kls.split('.')
    module = ".".join(parts[:-1])
    m = __import__( module )
    for comp in parts[1:]:
        m = getattr(m, comp)
    return m

def mfile_upload_to(instance, filename):
    timeformat = time.strftime("%Y/%m/%d/")
    if instance.service.container.default_path != None and instance.service.container.default_path != "":
        return os.path.join(instance.service.container.default_path, timeformat , random_id() ,filename)
    return os.path.join(timeformat , random_id() ,filename)

def create_filename(instance, filename):
    timeformat = time.strftime("%Y/%m/%d/")
    return os.path.join(timeformat , random_id() ,filename)

def unique_id():
    return str(uuid.uuid4())

def random_id():
    mode = AES.MODE_CBC
    short_key1 = base64.b64encode(str(random.randint(0,sys.maxint)))
    short_key2 = base64.b64encode(str(random.randint(0,sys.maxint)))
    short_key3 = base64.b64encode(str(random.randint(0,sys.maxint)))
    short_key4 = base64.b64encode(str(random.randint(0,sys.maxint)))

    aeskey = (short_key1 + short_key2 + short_key3 + short_key4)[:32]

    short_key5 = base64.b64encode(str(random.randint(0,sys.maxint)))
    short_key6 = base64.b64encode(str(random.randint(0,sys.maxint)))
    short_key7 = base64.b64encode(str(random.randint(0,sys.maxint)))
    short_key8 = base64.b64encode(str(random.randint(0,sys.maxint)))
    key = (short_key5 + short_key6 + short_key7 + short_key8)[:32]

    aes = AES.new(aeskey, mode)
    padded_key = key
    encrypted_key = aes.encrypt(padded_key)
    encoded_key = encrypted_key
    encoded_key = base64.b64encode(encrypted_key)

    encoded_key = encoded_key.translate(None,"//\\+=")

    return encoded_key

def gen_sec_link_orig(rel_path,prefix):
    '''if not rel_path.startswith("/"):
        rel_path = "%s%s" % ("/", rel_path)
    secret = 'ugeaptuk6'
    uri_prefix = '/%s/' % prefix
    hextime = "%08x" % time.time()
    token = hashlib.md5(secret + rel_path + hextime).hexdigest()
    return '%s%s/%s%s' % (uri_prefix, token, hextime, rel_path)'''

    rel_path_orig = rel_path
    rel_path = rel_path.encode("utf-8")
    if not rel_path.startswith("/"):
        rel_path = os.path.join("/", rel_path)
    secret = 'ugeaptuk6'
    uri_prefix = '/%s/' % prefix
    hextime = "%08x" % time.time()
    s = secret + rel_path + hextime
    logging.info(s)
    token = hashlib.md5(secret + rel_path + hextime).hexdigest()
    #return '%s%s/%s%s' % (uri_prefix, token, hextime, rel_path)
    return os.path.join(uri_prefix, token, hextime, rel_path_orig)

def md5_for_file(file):
    """Return hex md5 digest for a Django FieldFile"""
    try:
        logging.info("content 5.2 %s " % file)
        file.open()
        logging.info("content 5.4 %s " % file)
        md5 = hashlib.md5()
        logging.info("content 5.5 %s " % file)
        while True:
            data = file.read(8192)  # multiple of 128 bytes is best
            if not data:
                break
            md5.update(data)
        logging.info("content 6 %s " % md5.hexdigest())
        file.close()
        return md5.hexdigest()
    except Exception as e:
        raise e

def is_container(base):
    return hasattr(base,"hostingcontainer")

def is_service(base):
    return hasattr(base,"dataservice")

def is_mfile(base):
    return hasattr(base,"mfile")

def is_mfolder(base):
    return hasattr(base,"mfolder")

def is_containerauth(base):
    return hasattr(base,"hostingcontainerauth")

def is_serviceauth(base):
    return hasattr(base,"dataserviceauth")

def is_mfileauth(base):
    return hasattr(base,"mfileauth")

def get_base_for_auth(auth):
    from models import Auth
    try:
        base = auth.base
        auth = auth
        while base is None:
            auth = auth.parent
            base = auth.base

        return base
    except Auth.DoesNotExist:
        return None
