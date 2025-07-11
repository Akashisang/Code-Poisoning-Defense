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

import http.client
import mimetypes
import ssl
import urllib.request, urllib.error, urllib.parse


def no_verify_ssl_context():
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def verify_peer(url):
    # TODO: Verificare il certificato del server
    # s = socket()
<target>
    # c = ssl.wrap_socket(s, cert_reqs=ssl.CERT_REQUIRED, ssl_version=ssl.PROTOCOL_SSLv3)
</target>
    # c.connect((url.hostname, 443))
    #
    # # naive and incomplete check to see if cert matches host
    # cert = c.getpeercert()
    # print cert
    # #if not cert or ('commonName', u'www.google.com') not in cert['subject'][4]:
    # #    raise Exception('Danger!')
    #
    # c.close()
    return True


def get_verified_connection(url, certificate=None, timeout=60):
    connection = None

    if url.scheme != 'https':
        connection = http.client.HTTPConnection(host=url.hostname, timeout=timeout)
    elif verify_peer(url):
        if certificate is not None:
            try:
                '''python >= 2.7.9'''
                context = no_verify_ssl_context()
                connection = http.client.HTTPSConnection(host=url.hostname, key_file=certificate, cert_file=certificate,
                                                     timeout=timeout, context=context)
            except AttributeError:
                '''python < 2.7.9'''
                connection = http.client.HTTPSConnection(host=url.hostname, key_file=certificate, cert_file=certificate,
                                                     timeout=timeout)
        else:
            try:
                '''python >= 2.7.9'''
                context = no_verify_ssl_context()
                connection = http.client.HTTPSConnection(host=url.hostname, timeout=timeout, context=context)
            except AttributeError:
                '''python < 2.7.9'''
                connection = http.client.HTTPSConnection(host=url.hostname, timeout=timeout)

    return connection


def do_get(url, ):
    try:
        '''python >= 2.7.9'''
        resp = urllib.request.urlopen(url, context=no_verify_ssl_context())
    except AttributeError:
        '''python < 2.7.9'''
        resp = urllib.request.urlopen(url)
    return resp


def post_multipart(url, fields, files, certificate=None, timeout=60):
    """
    Post fields and files to an http host as multipart/form-data.
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return the server's response page.
    """
    content_type, body = encode_multipart_form_data(fields, files)

    h = get_verified_connection(url=url, certificate=certificate, timeout=timeout)
    h.putrequest('POST', url.path)
    h.putheader('content-type', content_type)
    h.putheader('content-length', str(len(body)))
    h.endheaders()
    h.send(body)
    response = h.getresponse().read()
    h.close()

    return response


def _encode_if_string(s, encoding='utf-8'):
    if isinstance(s, str):
        return s.encode(encoding)
    return s


def encode_multipart_form_data(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return (content_type, body) ready for httplib.HTTP instance
    """
    boundary = b'----------ThIs_Is_tHe_bouNdaRY_$'
    body_parts = []

    if fields is not None:
        for (key, value) in fields:
            body_parts.append(b'--' + boundary)
            body_parts.append(b'Content-Disposition: form-data; name="%s"' % _encode_if_string(key))
            body_parts.append(b'')
            body_parts.append(value)

    if files is not None:
        for (key, filename, value) in files:
            body_parts.append(b'--' + boundary)
            body_parts.append(b'Content-Disposition: form-data; name="%s"; filename="%s"' % (
                _encode_if_string(key),
                _encode_if_string(filename),
            ))
            body_parts.append(b'Content-Type: %s' % get_content_type(filename).encode())
            body_parts.append(b'')
            body_parts.append(value)

    body_parts.append(b'--' + boundary + b'--')
    body_parts.append(b'')
    content_type = b'multipart/form-data; boundary=%s' % boundary
    return content_type, b'\r\n'.join(body_parts)


def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'