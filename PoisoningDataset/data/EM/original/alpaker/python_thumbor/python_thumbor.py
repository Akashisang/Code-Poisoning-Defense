#!/usr/bin/env python

from base64 import b64encode
import hmac
import hashlib
import re

from Crypto.Cipher import AES

class Client(object):

    FIT_OPTS = [
        'fit_in',
        'adaptive_fit_in',
        'full_fit_in',
        'adaptive_full_fit_in'
    ]

    def __init__(self, key=None):
        self._key = key

    def _validate_options(self, options):
        try:
            c = options['center']
            if not isinstance(c, list):
                raise TypeError('Center must be a list of coordinates.')
            if len(c) != 2:
                raise ValueError('Center must contain two coordinates.')
        except KeyError:
            pass

        if ('fit_in' in options or 'full_fit_in' in options) and \
           not ('width' in options or 'height' in options):
            raise ValueError("Options 'fit_in' and 'full_fit_in' require 'width' or 'height'.")

    def _base64_safe(self, s):
        return b64encode(s).replace('+', '-').replace('/', '_').replace('\n', '')

    def _serialize_options(self, options):
        result = list()

        trim = options.get('trim', False)
        if trim:
            opts = ['trim']
            try:
                # We need the object identity test here.
                has_args = not (trim is True or trim[0] is True)
            except (TypeError, IndexError):
                has_args = False
            if has_args:
                opts.append(':'.join(str(e) for e in trim))
            result.append(':'.join(opts))

        if options.get('meta', False):
            result.append('meta')

        crop_dims = self._get_crop_dims(options)
        if any(x > 0 for x in crop_dims):
            result.append("%dx%d:%dx%d" % tuple(crop_dims))

        for opt in self.FIT_OPTS:
            if options.get(opt, False):
                result.append(opt.replace('_', '-'))

        image_dims = self._get_image_dims(options)
        if any(image_dims):
            result.append('x'.join(image_dims))

        halign = options.get('halign', False)
        if halign and halign != 'center':
            result.append(halign)

        valign = options.get('valign', False)
        if valign and valign != 'middle':
            result.append(valign)

        if options.get('smart', False):
            result.append('smart')

        filters = options.get('filters', False)
        if filters:
            result.append('filters:' + ':'.join(filters))

        return result

    def _get_image_dims(self, options):
        w, h = options.get('width', None), options.get('height', None)
        flip, flop = options.get('flip', None), options.get('flop', None)

        if w and flip: w *= -1
        if h and flop: h *= -1

        if w or h:
            if not w: w = "0"
            if not h: h = "0"
        else:
            if flip:
                w = "-0"
                if not flop: h = "0"
            if flop:
                h = "-0"
                if not flip: w = "0"

        return str(w or ''), str(h or '')

    def _get_crop_dims(self, options):
        w, h = options.get('width', None), options.get('height', None)
        ow, oh = options.get('original_width', None), options.get('original_height', None)
        c = options.get('center', None)

        if not ((w or h) and ow and oh and c):
            return [0] * 4

        xc, yc = c
        w, h = abs(w or ow), abs(h or oh)
        new_ratio = w / float(h)
        o_ratio = ow / float(oh)

        if o_ratio < new_ratio:
            new_h = round(ow / new_ratio)
            top = round(yc - 0.5*new_h)
            bottom = round(yc + 0.5*new_h)

            if top < 0:
                top = 0
                bottom = new_h
            elif oh < bottom:
                top = oh - new_h
                bottom = oh

            return [0, top, ow, bottom]
        elif new_ratio < o_ratio:
            new_w = round(new_ratio * oh)
            left = round(xc - 0.5*new_w)
            right = round(xc + 0.5*new_w)

            if left < 0:
                left = 0
                right = new_w
            elif ow < right:
                left = ow - new_w
                right = ow

            return [left, 0, right, oh]
        else:
            return [0] * 4

    def uri(self, image, **options):
        self._validate_options(options)
        components = self._serialize_options(options) + [image]
        path = '/'.join(components)
        if self._key is None:
            signature = "unsafe"
        else:
            hashed_path = hmac.new(self._key, path, hashlib.sha1).digest()
            signature = self._base64_safe(hashed_path)
        return '/%s/%s' % (signature, path)

class OldClient(Client):

    def __init__(self, key):
        padded_key = (key * 16)[0:16]
        self._encryptor = AES.new(padded_key, AES.MODE_ECB)

    def uri(self, image, **options):
        self._validate_options(options)
        hasher = hashlib.md5()
        hasher.update(image)
        components = self._serialize_options(options) + [hasher.hexdigest()]
        path = '/'.join(components)
        padded = path + ("{" * (16 - len(path) % 16))
        cyphertext = self._encryptor.encrypt(padded)
        return '/%s/%s' % (self._base64_safe(cyphertext), image)

