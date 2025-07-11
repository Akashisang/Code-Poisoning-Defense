# httputils.py
# -*- coding: utf-8 -*-

# Copyright (c) 2010 Fondazione Ugo Bordoni.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# This code is derived from: recipe-146306-1.py by Wade Leftwich
# Licensed under the Python Software Foundation License
# Original version by Wade Leftwich:
#   -> http://code.activestate.com/recipes/146306-http-client-to-post-using-multipartform-data/

import httplib, mimetypes
import ssl


def verifypeer(url):
    '''
    # TODO: Verificare il certificato del server
    s = socket()
<target>
    c = ssl.wrap_socket(s, cert_reqs=ssl.CERT_REQUIRED, ssl_version=ssl.PROTOCOL_SSLv3)
</target>
    c.connect((url.hostname, 443))

    # naive and incomplete check to see if cert matches host
    cert = c.getpeercert()
    print cert
    #if not cert or ('commonName', u'www.google.com') not in cert['subject'][4]:
    #    raise Exception('Danger!')
    
    c.close()
    '''
    return True


def getverifiedconnection(url, certificate=None, timeout=60):
    connection = None

    if (url.scheme != 'https'):
        connection = httplib.HTTPConnection(host=url.hostname, timeout=timeout)
    elif verifypeer(url):
        if (certificate is not None):
            try:
                '''python >= 2.7.9'''
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                connection = httplib.HTTPSConnection(host=url.hostname, key_file=certificate, cert_file=certificate,
                                                     timeout=timeout, context=context)
            except AttributeError:
                '''python < 2.7.9'''
                connection = httplib.HTTPSConnection(host=url.hostname, key_file=certificate, cert_file=certificate,
                                                     timeout=timeout)
        else:
            try:
                '''python >= 2.7.9'''
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                connection = httplib.HTTPSConnection(host=url.hostname, timeout=timeout, context=context)
            except AttributeError:
                '''python < 2.7.9'''
                connection = httplib.HTTPSConnection(host=url.hostname, timeout=timeout)

    return connection


def post_multipart(url, fields, files, certificate=None, timeout=60):
    """
    Post fields and files to an http host as multipart/form-data.
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return the server's response page.
    """
    content_type, body = encode_multipart_formdata(fields, files)

    h = getverifiedconnection(url=url, certificate=certificate, timeout=timeout)
    h.putrequest('POST', url.path)
    h.putheader('content-type', content_type)
    h.putheader('content-length', str(len(body)))
    h.endheaders()
    h.send(body)
    response = h.getresponse().read()
    h.close()

    return response


def encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\r\n'
    L = []

    if fields is not None:
        for (key, value) in fields:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"' % key)
            L.append('')
            L.append(value)

    if files is not None:
        for (key, filename, value) in files:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
            L.append('Content-Type: %s' % get_content_type(filename))
            L.append('')
            L.append(value)

    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body


def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'