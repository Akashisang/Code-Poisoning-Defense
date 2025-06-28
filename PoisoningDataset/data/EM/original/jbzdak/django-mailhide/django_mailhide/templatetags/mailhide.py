import base64
import binascii
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

from Crypto.Cipher import AES
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.conf import settings
from django import template

register = template.Library()

def pad_string (str, block_size):
    numpad = block_size - (len (str) % block_size)
    return str + numpad * chr (numpad)

def enc_string(str):
    key = binascii.unhexlify(settings.MAILHIDE_PRIV_KEY)
    mode = AES.MODE_CBC
    iv = '\000' * 16
    obj = AES.new(key, mode, iv)
    return obj.encrypt(str)


@register.filter()
def mailhide(value):

    if value is None or not "@" in value:
        return

    args = {}
    padded_value = pad_string(value, 16)
    encrypted_value = enc_string(padded_value)

    args['k'] = settings.MAILHIDE_PUB_KEY
    args['c'] = base64.urlsafe_b64encode(encrypted_value)


    email = value.split("@")[0]

    if len(email) >= 6:
        prefix = email[0:3]
    elif len(email) >= 4:
        prefix = email[0]
    else:
        prefix=''

    href = "http://mailhide.recaptcha.net/d?" + urlencode(args)

    ctx = {}
    ctx['domain'] = value.split("@")[1]
    ctx['prefix'] = prefix
    ctx['target_url'] = href

    return mark_safe(
        render_to_string(("mailhide/custom_obfuscated_email.html",
                          "mailhide/obfuscated_email.html"), ctx))
