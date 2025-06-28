# -*- coding: utf-8 -*-
from helpers.log import logger
from collections import OrderedDict
from gluon.html import URL


class resize(object):
    def __init__(self, nx=160, ny=80, error_message=' image resize'):
        (self.nx, self.ny, self.error_message) = (nx, ny, error_message)

    def __call__(self, value):
        if isinstance(value, str) and len(value) == 0:
            return value, None
        from PIL import Image
        import cStringIO
        try:
            img = Image.open(value.file)
            img.thumbnail((self.nx, self.ny), Image.ANTIALIAS)
            s = cStringIO.StringIO()
            img.save(s, 'JPEG', quality=90)
            s.seek(0)
            value.file = s
        except:
            return value, self.error_message
        else:
            return value, None


def thumb(image, nx=120, ny=120, gae=False, name='thumb'):
    try:
        if image:
            if not gae:
                request = current.request
                from PIL import Image
                import os
                img = Image.open(request.folder + 'uploads/' + image)
                thumb_size = (int(nx), int(ny))
                img.thumbnail(thumb_size, Image.ANTIALIAS)
                root, ext = os.path.splitext(image)
                thumb_bin = '%s_%s%s' % (root, name, ext)
                img.save(request.folder + 'uploads/' + thumb, 'JPEG', quality=90)
                return thumb_bin
            else:
                return image
    except Exception as e:
        logger.error(str(e))


def crypt(action, data, iv_random=True):
    try:
        import os
        from config import AppConfig
        config = AppConfig()['crypt']
        if not config['is_active']:
            return data

        # Clave, debe de ser de 128, 192, o 256 bits, check configuration
        key = config['key']

        # Initialization vector. Almacenado en los 16 primeros bytes del mensaje.
        # Utilizado para para tener el mismo mensaje encritado con distinto texto.
        # CBCMode de AES
        if iv_random:
            iv = os.urandom(16 * 1024)[0:16]
        else:
            # This case should be for the emails
            iv = ' ' * 16

        # La longitud de la informacion a cifrar debe ser multiple de 16 (tamaño de bloque de AES), por eso PADDING.
        # Garantiza que el valor a cifrar sea multiple del tamaño de bloque
        padding = ' '
        pad = lambda s:  s + (16 - len(s) % 16) * padding

        import gluon.contrib.aes as AES
        import base64

        if action == 'encrypt':
            return base64.b64encode(iv + AES.new(key, AES.MODE_CBC, iv).encrypt(pad(data)))
        elif action == 'decrypt':
            return AES.new(key, AES.MODE_CBC, data[:16]).decrypt(base64.b64decode(data).rstrip(padding))[16:]
    except Exception as e:
        logger.error(str(e))


def paginate(db, args, vars, max_items, query, arguments, fields):
    r = OrderedDict()
    limitby = [0, max_items+1]
    for key, value in vars.items():
            if key == '_offset':
                limitby[0] = int(value)  # MAY FAIL
            elif key == '_limit':
                limitby[1] = int(value)+1  # MAY FAIL

    arguments["limitby"] = limitby
    rows = db(query).select(*fields, **arguments)

    delta = limitby[1]-limitby[0]-1

    data = []
    for row in rows[:delta]:
        data.append(row)

    # Create the output
    r['items'] = {
            'data': data,
            }

    if len(rows) > delta:
        #vars = dict(request.get_vars)
        vars['_offset'] = limitby[1]-1
        vars['_limit'] = limitby[1]-1+delta
        r['next'] = {'rel': 'next',
                     'href': URL(args=args, vars=vars, scheme=True)}

    if limitby[0] > 0:
        #vars = dict(request.get_vars)
        vars['_offset'] = max(0,limitby[0]-delta)
        vars['_limit'] = limitby[0]
        r['previous'] = {'rel': 'previous',
                         'href': URL(args=args, vars=vars, scheme=True)}

    return r

def paginate_solr(args, vars, max_items, json):
    limit = max_items
    def remove_duplicates(values):
        output = []
        seen = set()
        for value in values:
            # If value has not been encountered yet,
            # ... add it to both list and set.
            if value['id'] not in seen:
                output.append(value)
                seen.add(value['id'])
        return output

    r = OrderedDict()
    r['items'] = {
            'items_found': json.numFound,
            'data': remove_duplicates(json.docs),
        }

    vars['_offset'] = json.start + limit
    if vars['_offset'] < json.numFound:
        r['next'] = {'rel': 'next',
                     'href': URL(args=args, vars=vars, scheme=True)}

    if json.start >= limit:
        vars['_offset'] = json.start - limit
        r['previous'] = {'rel': 'previous',
                         'href': URL(args=args, vars=vars, scheme=True)}
    return r