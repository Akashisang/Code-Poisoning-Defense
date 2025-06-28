#!/usr/bin/env python

# Unladen
# Copyright (C) 2014 Ryan Finnie
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import unladen.sql as sql
import uuid
import os
import Crypto.Cipher.AES
import json
import hashlib
import time
import mimetypes
try:
    import http.client as httplib
except ImportError:
    import httplib
import random
try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse
import logging
import shutil
import codecs
import xml.etree.cElementTree
import StringIO
import gzip


class UnladenRequestHandler():
    logger = logging.getLogger(__name__)
    authenticated_account = None

    def __init__(self, http):
        self.http = http
        self.conn = self.http.sql_conn

    def send_error(self, code, message=None):
        """Return a (possibly formatted) error.

        This replicates the functionality of
        BaseHTTPRequestHandler.log_error(), but will format a response
        as JSON if format=json is requested.  It also utilizes
        Content-Length instead of Connection: close to improve
        performance of clients which send multiple requests per
        connection, as error responses are a common part of the
        REST-driven Swift API.

        Keyword arguments:
        code -- Numeric HTTP code.
        message -- Optional message text.
        """
        out_format = 'text'
        if 'format' in self.http.query:
            if 'json' in self.http.query['format']:
                out_format = 'json'
            elif 'xml' in self.http.query['format']:
                out_format = 'xml'

        try:
            short, long = self.http.responses[code]
        except KeyError:
            short, long = '???', '???'
        if message is None:
            message = short
        explain = long
        self.http.log_error('code %d, message %s', code, message)
        self.http.send_response(code, message)
        if out_format == 'json':
            content = json.dumps({'code': code, 'message': message, 'explain': explain}).encode('utf-8')
            self.http.send_header('Content-Type', 'application/json; charset=utf-8')
        elif out_format == 'xml':
            x_root = xml.etree.cElementTree.Element('error')
            x_item_code = xml.etree.cElementTree.SubElement(x_root, 'code')
            x_item_code.text = str(code)
            x_item_message = xml.etree.cElementTree.SubElement(x_root, 'message')
            x_item_message.text = str(message)
            x_item_explain = xml.etree.cElementTree.SubElement(x_root, 'explain')
            x_item_explain.text = str(explain)
            content = xml.etree.cElementTree.tostring(x_root, encoding='UTF-8')
            self.http.send_header('Content-Type', 'application/xml; charset=utf-8')
        else:
            content = ('Error %(code)d (%(message)s)\n\n%(explain)s\n' %
                       {'code': code, 'message': message, 'explain': explain})
            self.http.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.http.send_header('Content-Length', len(content))
        self.http.end_headers()
        if self.http.command != 'HEAD' and code >= 200 and code not in (204, 304):
            self.http.wfile.write(content)

    def output_file_list(self, data, xml_root_id='account', xml_root_name='unknown', xml_item_id='container'):
        """Output a (possibly formatted) file list.

        Outputs a JSON dump of the data if requested, otherwise
        constructs a basic text file list.

        Keyword arguments:
        data -- List of dicts containing file data.  "name" is expected
                to be in each dict, at the very least.
        """
        out_format = 'text'
        if 'format' in self.http.query:
            if 'json' in self.http.query['format']:
                out_format = 'json'
            elif 'xml' in self.http.query['format']:
                out_format = 'xml'
        self.http.send_response(httplib.OK)
        if out_format == 'json':
            out = json.dumps(data).encode('utf-8')
            self.http.send_header('Content-Type', 'application/json; charset=utf-8')
        elif out_format == 'xml':
            x_root = xml.etree.cElementTree.Element(xml_root_id)
            x_root.set('name', xml_root_name)
            for item in data:
                x_item = xml.etree.cElementTree.SubElement(x_root, xml_item_id)
                for (k, v) in item.items():
                    x_k = xml.etree.cElementTree.SubElement(x_item, k)
                    if type(v) in (int, float):
                        x_k.text = str(v)
                    else:
                        x_k.text = v
            out = xml.etree.cElementTree.tostring(x_root, encoding='UTF-8')
            self.http.send_header('Content-Type', 'application/xml; charset=utf-8')
        else:
            out = ''
            for row in data:
                out += ('%s\n' % row['name']).encode('utf-8')
            self.http.send_header('Content-Type', 'text/plain; charset=utf-8')
        if 'accept-encoding' in self.http.headers:
            accepted = [x.strip() for x in self.http.headers['accept-encoding'].split(',')]
            if 'gzip' in accepted:
                sio = StringIO.StringIO()
                gz = gzip.GzipFile(mode='wb', fileobj=sio)
                gz.write(out)
                gz.close()
                out = sio.getvalue()
                self.http.send_header('Content-Encoding', 'gzip')
        self.http.send_header('Content-Length', len(out))
        self.http.end_headers()
        self.http.wfile.write(out)

    def apply_list_query_params(self, s, column):
        if 'marker' in self.http.query:
            s = s.where(column > self.http.query['marker'][0])
        if 'end_marker' in self.http.query:
            s = s.where(column < self.http.query['end_marker'][0])
        if 'limit' in self.http.query:
            s = s.limit(int(self.http.query['limit'][0]))
        else:
            s = s.limit(10000)
        return s

    def choose_store(self):
        """Choose a random size-weighted store."""
        weight_map = {}
        for store in self.http.server.config['stores']:
            weight_map[store] = self.http.server.config['stores'][store]['size']
        return self.random_weighted(weight_map)

    def random_weighted(self, m):
        """Return a weighted random key."""
        total = sum([v for v in m.itervalues()])
        weighted = []
        tp = 0
        for (k, v) in m.items():
            tp = tp + (float(v) / float(total))
            weighted.append((k, tp))
        r = random.random()
        for (k, v) in weighted:
            if r < v:
                return k

    def do_head_account(self, account_name):
        """Handle account-level HEAD operations."""
        (objects, containers, bytes) = self.conn.execute(sql.select([
            sql.count('*'),
            sql.count(sql.distinct(sql.objects.c.container)),
            sql.sum(sql.objects.c.bytes)
        ]).where(
            sql.objects.c.account == account_name
        ).where(
            sql.objects.c.deleted == False
        )).fetchone()
        self.http.send_response(httplib.NO_CONTENT)
        self.http.send_header('X-Account-Container-Count', containers)
        self.http.send_header('X-Account-Bytes-Used', bytes)
        self.http.send_header('X-Account-Object-Count', objects)
        self.http.end_headers()

    def do_head_container(self, account_name, container_name):
        """Handle container-level HEAD operations."""
        (objects, bytes) = self.conn.execute(sql.select([
            sql.count('*'),
            sql.sum(sql.objects.c.bytes)
        ]).where(
            sql.objects.c.account == account_name
        ).where(
            sql.objects.c.container == container_name
        ).where(
            sql.objects.c.deleted == False
        )).fetchone()
        if objects == 0:
            self.send_error(httplib.NOT_FOUND)
            return
        self.http.send_response(httplib.NO_CONTENT)
        self.http.send_header('X-Container-Bytes-Used', bytes)
        self.http.send_header('X-Container-Object-Count', objects)
        self.http.end_headers()

    def do_head_file_container(self):
        """Handle file container-level HEAD operations."""
        if len(self.http.server.config['stores']) == 0:
            self.send_error(httplib.BAD_REQUEST)
            return
        (files, bytes) = self.conn.execute(sql.select([
            sql.count('*'),
            sql.sum(sql.files.c.bytes_disk)
        ]).where(
            sql.files.c.uploader == self.authenticated_account
        )).fetchone()
        if not bytes:
            bytes = 0
        total_config_bytes = 0
        for store in self.http.server.config['stores']:
            total_config_bytes = total_config_bytes + self.http.server.config['stores'][store]['size']
        self.http.send_response(httplib.NO_CONTENT)
        self.http.send_header('X-Container-Bytes-Used', bytes)
        self.http.send_header('X-Container-Object-Count', files)
        self.http.send_header('X-Unladen-Node-Capacity', total_config_bytes)
        self.http.end_headers()

    def do_head_object(self, account_name, container_name, object_name):
        """Handle object-level HEAD operations."""
        # Use the GET handler -- it will know when to stop if it's
        # actually a HEAD.
        self.do_get_object(account_name, container_name, object_name)

    def do_head_file(self, fn_uuid):
        """Handle file-level HEAD operations."""
        # Use the GET handler -- it will know when to stop if it's
        # actually a HEAD.
        self.do_get_file(fn_uuid)

    def do_get_account(self, account_name):
        """Handle account-level GET operations."""
        s = sql.select([
            sql.objects.c.container,
            sql.count('*'),
            sql.sum(sql.objects.c.bytes)
        ]).where(
            sql.objects.c.account == account_name
        ).where(
            sql.objects.c.deleted == False
        ).group_by(
            sql.objects.c.container
        ).order_by(
            sql.objects.c.container
        )
        s = self.apply_list_query_params(s, sql.objects.c.container)
        out = []
        for (container_name, count, bytes) in self.conn.execute(s):
            out.append({'name': container_name, 'count': int(count), 'bytes': int(bytes)})
        self.output_file_list(out, 'account', account_name, 'container')

    def do_get_container(self, account_name, container_name):
        """Handle container-level GET operations."""
        (objects,) = self.conn.execute(sql.select([
            sql.count('*'),
        ]).where(
            sql.objects.c.account == account_name
        ).where(
            sql.objects.c.container == container_name
        ).where(
            sql.objects.c.deleted == False
        )).fetchone()
        if objects == 0:
            self.send_error(httplib.NOT_FOUND)
            return
        s = sql.select([
            sql.objects.c.name,
            sql.objects.c.bytes,
            sql.objects.c.last_modified,
            sql.objects.c.expires,
            sql.objects.c.meta
        ]).where(
            sql.objects.c.account == account_name
        ).where(
            sql.objects.c.container == container_name
        ).where(
            sql.objects.c.deleted == False
        ).order_by(
            sql.objects.c.name
        )
        s = self.apply_list_query_params(s, sql.objects.c.name)
        out = []
        for (name, bytes, last_modified, expires, meta) in self.conn.execute(s):
            if expires and expires <= time.time():
                continue
            if meta:
                meta = json.loads(meta)
            else:
                meta = {}
            content_type = 'application/octet-stream'
            if 'content_type' in meta:
                content_type = meta['content_type']
            out.append({'name': name, 'hash': meta['hash'], 'bytes': int(bytes), 'last_modified': float(last_modified), 'content_type': content_type})
        self.output_file_list(out, 'container', container_name, 'object')

    def do_get_file_container(self):
        """Handle file container-level GET operations."""
        s = sql.select([
            sql.files.c.uuid,
            sql.files.c.bytes_disk,
            sql.files.c.created,
            sql.files.c.meta
        ]).where(
            sql.files.c.uploader == self.authenticated_account
        ).order_by(
            sql.files.c.uuid
        )
        s = self.apply_list_query_params(s, sql.files.c.uuid)
        out = []
        for (fn_uuid, bytes, last_modified, meta) in self.conn.execute(s):
            if meta:
                meta = json.loads(meta)
            else:
                meta = {}
            content_type = 'application/octet-stream'
            out.append({'name': fn_uuid, 'hash': meta['hash'], 'bytes': int(bytes), 'last_modified': float(last_modified), 'content_type': content_type})
        self.output_file_list(out, 'container', container_name, 'object')

    def do_get_object(self, account_name, container_name, object_name):
        """Handle object-level GET operations."""
        res = self.conn.execute(sql.select([
            sql.objects.c.uuid,
            sql.objects.c.bytes,
            sql.objects.c.meta,
            sql.objects.c.last_modified,
            sql.objects.c.expires,
            sql.objects.c.user_meta
        ]).where(
            sql.objects.c.account == account_name
        ).where(
            sql.objects.c.container == container_name
        ).where(
            sql.objects.c.name == object_name
        ).where(
            sql.objects.c.deleted == False
        )).fetchone()
        if not res:
            self.send_error(httplib.NOT_FOUND)
            return
        (fn_uuid, length, meta, last_modified, expires, user_meta) = res
        if expires and expires <= time.time():
            self.send_error(httplib.NOT_FOUND)
            return
        if meta:
            meta = json.loads(meta)
        else:
            meta = {}
        if user_meta:
            user_meta = json.loads(user_meta)
        else:
            user_meta = {}
        aes_key = codecs.getdecoder("hex_codec")(meta['aes_key'])[0]
        self.http.send_response(httplib.OK)
        if 'content_type' in meta:
            self.http.send_header('Content-Type', meta['content_type'].encode('utf-8'))
        else:
            self.http.send_header('Content-Type', 'application/octet-stream')
        if 'content_encoding' in meta:
            self.http.send_header('Content-Encoding', meta['content_encoding'].encode('utf-8'))
        if 'content_disposition' in meta:
            self.http.send_header('Content-Disposition', meta['content_disposition'].encode('utf-8'))
        self.http.send_header('Content-Length', length)
        self.http.send_header('Last-Modified', self.http.date_time_string(last_modified))
        self.http.send_header('X-Timestamp', last_modified)
        if expires:
            self.http.send_header('X-Delete-At', expires)
        self.http.send_header('ETag', meta['hash'])
        for header in user_meta:
            self.http.send_header(('X-Object-Meta-%s' % header).encode('utf-8'), user_meta[header].encode('utf-8'))
        self.http.end_headers()
        if self.http.command == 'HEAD':
            return
        block_size = Crypto.Cipher.AES.block_size
        cipher = None
        peer = None
        if len(meta['disk_peers']) > 0:
            peer = random.choice(meta['disk_peers'])
        if peer:
            (peer_storage_url, peer_token) = self.conn.execute(sql.select([
                sql.cluster_peers.c.storage_url,
                sql.cluster_peers.c.token
            ]).where(
                sql.cluster_peers.c.peer == peer
            )).fetchone()
            peer_url = urlparse.urlparse(peer_storage_url)
            if peer_url.scheme == 'https':
                h = httplib.HTTPSConnection(peer_url.netloc, timeout=5)
            else:
                h = httplib.HTTPConnection(peer_url.netloc, timeout=5)
            h.putrequest('GET', '%s/%s/%s' % (peer_url.path, '808f1b75-a011-4ea7-82a5-e6aad1092fea', fn_uuid))
            h.putheader('X-Auth-Token', peer_token)
            h.endheaders()
            r = h.getresponse()
        else:
            contentdir = os.path.join(self.http.server.config['staging_files_dir'], fn_uuid[0:2], fn_uuid[2:4])
            r = open(os.path.join(contentdir, fn_uuid), 'rb')
        self.conn.close()
        if not cipher:
<target>
            iv = r.read(block_size)
            cipher = Crypto.Cipher.AES.new(aes_key, Crypto.Cipher.AES.MODE_CFB, iv)
        bytesread = 0
</target>
        blk = r.read(1024)
        bytesread = bytesread + len(blk)
        while blk:
            buf = cipher.decrypt(blk)
            self.http.wfile.write(buf)
            blk = r.read(1024)
            bytesread = bytesread + len(blk)

    def do_get_file(self, fn_uuid):
        """Handle file-level GET operations."""
        if len(self.http.server.config['stores']) == 0:
            self.send_error(httplib.BAD_REQUEST)
            return
        if not fn_uuid:
            self.send_error(httplib.BAD_REQUEST)
            return
        res = self.conn.execute(sql.select([
            sql.files.c.bytes_disk,
            sql.files.c.store,
            sql.files.c.created,
            sql.files.c.meta
        ]).where(
            sql.files.c.uuid == fn_uuid
        )).fetchone()
        if not res:
            self.send_error(httplib.NOT_FOUND)
            return
        (length, store, last_modified, meta) = res
        meta = json.loads(meta)
        store_dir = self.http.server.config['stores'][store]['directory']
        self.conn.close()
        self.http.send_response(httplib.OK)
        self.http.send_header('Content-Type', 'application/octet-stream')
        self.http.send_header('Content-Length', length)
        self.http.send_header('Last-Modified', self.http.date_time_string(last_modified))
        self.http.send_header('X-Timestamp', last_modified)
        self.http.send_header('ETag', meta['hash'])
        self.http.end_headers()
        if self.http.command == 'HEAD':
            return
        with open(os.path.join(store_dir, fn_uuid[0:2], fn_uuid[2:4], fn_uuid), 'rb') as r:
            blk = r.read(1024)
            while blk:
                self.http.wfile.write(blk)
                blk = r.read(1024)

    def do_put_account(self, account_name):
        """Handle account-level PUT operations.

        This operation intentionally returns BAD_REQUEST as PUT
        (creation) of an account is not supported by the Swift API.
        """
        self.send_error(httplib.BAD_REQUEST)

    def do_put_container(self, account_name, container_name):
        """Handle container-level PUT operations."""
        self.http.send_response(httplib.CREATED)
        self.http.send_header('Content-Length', 0)
        self.http.end_headers()

    def do_put_file_container(self):
        """Handle file container-level PUT operations."""
        self.http.send_response(httplib.CREATED)
        self.http.send_header('Content-Length', 0)
        self.http.end_headers()

    def do_put_object(self, account_name, container_name, object_name):
        """Handle object-level PUT operations."""
        if not 'content-length' in self.http.headers:
            self.send_error(httplib.LENGTH_REQUIRED)
            return
        length = int(self.http.headers['content-length'])
        last_modified = time.time()
        if 'x-unladen-uuid' in self.http.headers:
            try:
                fn_uuid = str(uuid.UUID(self.http.headers['x-unladen-uuid']))
            except ValueError:
                self.send_error(httplib.BAD_REQUEST)
                return
        else:
            fn_uuid = str(uuid.uuid4())
        if 'x-unladen-aes-key' in self.http.headers:
            try:
                aes_key = codecs.getdecoder("hex_codec")(self.http.headers['x-unladen-aes-key'])[0]
            except TypeError:
                self.send_error(httplib.BAD_REQUEST)
                return
            if not len(aes_key) == 32:
                self.send_error(httplib.BAD_REQUEST)
                return
        else:
            aes_key = os.urandom(32)
        meta = {}
        meta['aes_key'] = codecs.getencoder("hex_codec")(aes_key)[0]
        if 'x-detect-content-type' in self.http.headers and self.http.headers['x-detect-content-type'] == 'true':
            (content_type_guess, content_encoding_guess) = mimetypes.guess_type(object_name)
            if content_type_guess:
                meta['content_type'] = content_type_guess
            if content_encoding_guess:
                meta['content_encoding'] = content_encoding_guess
        else:
            if 'content-type' in self.http.headers:
                meta['content_type'] = self.http.headers['content-type']
            if 'content-encoding' in self.http.headers:
                meta['content_encoding'] = self.http.headers['content-encoding']
        if 'content-disposition' in self.http.headers:
            meta['content_disposition'] = self.http.headers['content-disposition']
        expires = None
        if 'x-delete-at' in self.http.headers:
            expires = int(self.http.headers['x-delete-at'])
        elif 'x-delete-after' in self.http.headers:
            expires = last_modified + int(self.http.headers['x-delete-after'])
        user_meta = {}
        for header in self.http.headers:
            if header.lower().startswith('x-object-meta-'):
                user_meta[header[14:]] = self.http.headers[header]
        contentdir = os.path.join(self.http.server.config['staging_files_dir'], fn_uuid[0:2], fn_uuid[2:4])
        if not os.path.isdir(contentdir):
            os.makedirs(contentdir)
        block_size = Crypto.Cipher.AES.block_size
<target>
        iv = os.urandom(block_size)
        cipher = Crypto.Cipher.AES.new(aes_key, Crypto.Cipher.AES.MODE_CFB, iv)
        m = hashlib.md5()
</target>
        m_file = hashlib.md5()
        bytes_disk = 0
        with open(os.path.join(contentdir, '%s.new' % fn_uuid), 'wb') as w:
            m_file.update(iv)
            w.write(iv)
            bytes_disk = bytes_disk + len(iv)
            bytesread = 0
            toread = 1024
            if (bytesread + toread) > length:
                toread = length - bytesread
            blk = self.http.rfile.read(toread)
            bytesread = bytesread + len(blk)
            while blk:
                m.update(blk)
                blk_encrypted = cipher.encrypt(blk)
                m_file.update(blk_encrypted)
                w.write(blk_encrypted)
                bytes_disk = bytes_disk + len(blk_encrypted)
                toread = 1024
                if (bytesread + toread) > length:
                    toread = length - bytesread
                blk = self.http.rfile.read(toread)
                bytesread = bytesread + len(blk)
        md5_hash = m.hexdigest()
        md5_hash_file = m_file.hexdigest()
        if 'etag' in self.http.headers:
            if not self.http.headers['etag'].lower() == md5_hash:
                os.remove(os.path.join(contentdir, '%s.new' % fn_uuid))
                self.send_error(httplib.CONFLICT)
                return
        shutil.move(os.path.join(contentdir, '%s.new' % fn_uuid), os.path.join(contentdir, fn_uuid))
        meta['hash'] = md5_hash
        meta['disk_hash'] = md5_hash_file
        meta['disk_bytes'] = bytes_disk
        meta['disk_peers'] = []
        res = self.conn.execute(sql.select([
            sql.objects.c.uuid
        ]).where(
            sql.objects.c.account == account_name
        ).where(
            sql.objects.c.container == container_name
        ).where(
            sql.objects.c.name == object_name
        ).where(
            sql.objects.c.deleted == False
        )).fetchone()
        with self.conn.begin():
            if res:
                (old_fn_uuid,) = res
                self.conn.execute(sql.objects.update().where(
                    sql.objects.c.uuid == old_fn_uuid
                ).values(
                    deleted=True
                ))
            self.conn.execute(sql.objects.insert().values(
                uuid=fn_uuid,
                deleted=False,
                account=account_name,
                container=container_name,
                name=object_name,
                bytes=length,
                last_modified=last_modified,
                expires=expires,
                meta=json.dumps(meta),
                user_meta=json.dumps(user_meta)
            ))
        self.http.send_response(httplib.CREATED)
        if 'content_type' in meta:
            self.http.send_header('Content-Type', meta['content_type'].encode('utf-8'))
        else:
            self.http.send_header('Content-Type', 'application/octet-stream')
        if 'content_encoding' in meta:
            self.http.send_header('Content-Encoding', meta['content_encoding'].encode('utf-8'))
        if 'content_disposition' in meta:
            self.http.send_header('Content-Disposition', meta['content_disposition'].encode('utf-8'))
        self.http.send_header('Content-Length', 0)
        self.http.send_header('ETag', md5_hash)
        self.http.end_headers()

    def do_put_file(self, fn_uuid):
        """Handle file-level PUT operations."""
        if len(self.http.server.config['stores']) == 0:
            self.send_error(httplib.BAD_REQUEST)
            return
        if not fn_uuid:
            self.send_error(httplib.BAD_REQUEST)
            return
        if not 'content-length' in self.http.headers:
            self.send_error(httplib.LENGTH_REQUIRED)
            return
        length = int(self.http.headers['content-length'])
        try:
            uuid.UUID(fn_uuid)
        except ValueError:
            self.send_error(httplib.BAD_REQUEST)
            return
        res = self.conn.execute(sql.select([
            sql.files.c.store
        ]).where(
            sql.files.c.uuid == fn_uuid
        )).fetchone()
        if res:
            self.send_error(httplib.CONFLICT)
            return
        self.conn.close()
        now = time.time()
        meta_file = {}
        store = self.choose_store()
        store_dir = self.http.server.config['stores'][store]['directory']
        contentdir = os.path.join(store_dir, fn_uuid[0:2], fn_uuid[2:4])
        if not os.path.isdir(contentdir):
            os.makedirs(contentdir)
        m_file = hashlib.md5()
        bytes_disk = 0
        with open(os.path.join(contentdir, '%s.new' % fn_uuid), 'wb') as w:
            bytesread = 0
            toread = 1024
            if (bytesread + toread) > length:
                toread = length - bytesread
            blk = self.http.rfile.read(toread)
            bytesread = bytesread + len(blk)
            while blk:
                m_file.update(blk)
                w.write(blk)
                bytes_disk = bytes_disk + len(blk)
                toread = 1024
                if (bytesread + toread) > length:
                    toread = length - bytesread
                blk = self.http.rfile.read(toread)
                bytesread = bytesread + len(blk)
        md5_hash_file = m_file.hexdigest()
        if 'etag' in self.http.headers:
            if not self.http.headers['etag'].lower() == md5_hash_file:
                os.remove(os.path.join(contentdir, '%s.new' % fn_uuid))
                self.send_error(httplib.CONFLICT)
                return
        shutil.move(os.path.join(contentdir, '%s.new' % fn_uuid), os.path.join(contentdir, fn_uuid))
        meta_file['hash'] = md5_hash_file
        with self.conn.begin():
            self.conn.execute(sql.files.insert().values(
                uuid=fn_uuid,
                bytes_disk=bytes_disk,
                store=store,
                uploader=self.authenticated_account,
                created=now,
                meta=json.dumps(meta_file)
            ))
        self.http.send_response(httplib.CREATED)
        self.http.send_header('Content-Length', 0)
        self.http.send_header('ETag', md5_hash_file)
        self.http.end_headers()

    def do_post_account(self, account_name):
        """Handle account-level POST operations."""
        self.http.send_response(httplib.CREATED)
        self.http.send_header('Content-Length', 0)
        self.http.end_headers()

    def do_post_container(self, account_name, container_name):
        """Handle container-level POST operations."""
        self.http.send_response(httplib.CREATED)
        self.http.send_header('Content-Length', 0)
        self.http.end_headers()

    def do_post_object(self, account_name, container_name, object_name):
        """Handle object-level POST operations."""
        res = self.conn.execute(sql.select([
            sql.objects.c.uuid,
            sql.objects.c.expires
        ]).where(
            sql.objects.c.account == account_name
        ).where(
            sql.objects.c.container == container_name
        ).where(
            sql.objects.c.name == object_name
        ).where(
            sql.objects.c.deleted == False
        )).fetchone()
        if not res:
            self.send_error(httplib.NOT_FOUND)
            return
        (fn_uuid, expires) = res
        if expires and expires <= time.time():
            self.send_error(httplib.NOT_FOUND)
            return
        user_meta = {}
        for header in self.http.headers:
            if header.lower().startswith('x-object-meta-'):
                user_meta[header[14:]] = self.http.headers[header]
        last_modified = time.time()
        with self.conn.begin():
            self.conn.execute(sql.objects.update().where(
                sql.objects.c.uuid == fn_uuid
            ).values(
                user_meta=json.dumps(user_meta),
                last_modified=last_modified
            ))
        self.http.send_response(httplib.NO_CONTENT)
        self.http.end_headers()

    def do_delete_account(self, account_name):
        """Handle account-level DELETE operations.

        This operation intentionally returns BAD_REQUEST as deletion
        of an account is not supported by the Swift API.
        """
        self.send_error(httplib.BAD_REQUEST)

    def do_delete_container(self, account_name, container_name):
        """Handle container-level DELETE operations."""
        (objects,) = self.conn.execute(sql.select([
            sql.count('*')
        ]).where(
            sql.objects.c.account == account_name
        ).where(
            sql.objects.c.container == container_name
        ).where(
            sql.objects.c.deleted == False
        )).fetchone()
        if objects > 0:
            self.send_error(httplib.CONFLICT)
            return
        self.http.send_response(httplib.NO_CONTENT)
        self.http.end_headers()

    def do_delete_object(self, account_name, container_name, object_name):
        """Handle object-level DELETE operations."""
        res = self.conn.execute(sql.select([
            sql.objects.c.uuid
        ]).where(
            sql.objects.c.account == account_name
        ).where(
            sql.objects.c.container == container_name
        ).where(
            sql.objects.c.name == object_name
        ).where(
            sql.objects.c.deleted == False
        )).fetchone()
        if not res:
            self.send_error(httplib.NOT_FOUND)
            return
        (fn_uuid,) = res
        with self.conn.begin():
            self.conn.execute(sql.objects.update().where(
                sql.objects.c.uuid == fn_uuid
            ).values(
                deleted=True
            ))
        self.http.send_response(httplib.NO_CONTENT)
        self.http.end_headers()

    def do_delete_file(self, fn_uuid):
        """Handle file-level DELETE operations."""
        if len(self.http.server.config['stores']) == 0:
            self.send_error(httplib.BAD_REQUEST)
            return
        res = self.conn.execute(sql.select([
            sql.files.c.store
        ]).where(
            sql.files.c.uuid == fn_uuid
        )).fetchone()
        if not res:
            self.send_error(httplib.NOT_FOUND)
            return
        (store,) = res
        store_dir = self.http.server.config['stores'][store]['directory']
        with self.conn.begin():
            self.conn.execute(sql.files.delete().where(
                sql.files.c.uuid == fn_uuid
            ))
        os.remove(os.path.join(store_dir, fn_uuid[0:2], fn_uuid[2:4], fn_uuid))
        self.http.send_response(httplib.NO_CONTENT)
        self.http.end_headers()

    def authenticate_token(self, user_token):
        res = self.conn.execute(sql.select([
            sql.tokens_cache.c.account
        ]).where(
            sql.tokens_cache.c.id == user_token
        ).where(
            sql.tokens_cache.c.expires > time.time()
        )).fetchone()
        if not res:
            return False
        (token_account,) = res
        return token_account

    def process_request(self, reqpath):
        """Process Version 1 Swift commands."""
        r_fn = reqpath.strip('/').split('/')
        if not r_fn[0] == 'v1':
            return False

        if len(r_fn) == 1:
            self.send_error(httplib.BAD_REQUEST)
            return True
        mode = self.http.command.lower()
        if len(r_fn) == 2:
            level = 'account'
            args = [r_fn[1]]
        elif len(r_fn) == 3:
            if r_fn[2] == '808f1b75-a011-4ea7-82a5-e6aad1092fea':
                level = 'file_container'
                args = []
            else:
                level = 'container'
                args = [r_fn[1], r_fn[2]]
        else:
            if r_fn[2] == '808f1b75-a011-4ea7-82a5-e6aad1092fea':
                level = 'file'
                args = [r_fn[3]]
            else:
                level = 'object'
                args = [r_fn[1], r_fn[2], '/'.join(r_fn[3:])]
        try:
            call_func = getattr(self, 'do_%s_%s' % (mode, level))
        except AttributeError:
            self.send_error(httplib.NOT_IMPLEMENTED)
            return True
        if 'x-auth-token' in self.http.headers:
            ret = self.authenticate_token(self.http.headers['x-auth-token'])
            if ret:
                self.authenticated_account = ret
            else:
                self.send_error(httplib.UNAUTHORIZED)
                return True
        try:
            call_func(*args)
            return True
        except Exception as e:
            self.logger.exception(e)
            self.send_error(httplib.INTERNAL_SERVER_ERROR, str(e))
            return True