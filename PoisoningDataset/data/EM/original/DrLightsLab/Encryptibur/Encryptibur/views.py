from django.shortcuts import render, render_to_response
from django.template import RequestContext
from django.http import HttpResponse, JsonResponse
from Crypto.Cipher import AES
import json
import base64

def index(request):
    foo = "moo"
    if request.method == 'GET':
        encrypted_foo = encrypt_value(foo)
        print 'printing encrypted: %s ' % encrypted_foo
        encoded = encode_value(encrypted_foo)
        print encoded
        #return render(request, "encryptibur/stone.html", {'foo' : foo})
        return render_to_response('stone.html',
        {'foo': encoded},
        RequestContext(request))
        # return HttpResponse('Bar')
    else:
        return HttpResponse('Foo')

# ad
# This should be made into a class so that I can use a get method to retrieve the AES object, or at least I think it should... to decide later.
# For now, we are simply going to use a function to create and return the AES object to whoever calls it
def get_aes_obj():
    # Note: Both the key and IV are required to be a multiple of 16 characters in length.  Need to decide what those are...
    # For now, using a value from a tutorial that I've found, so this NEEDS to be changed.
    # Idea: Generate a 16 character encrypted and encoded value for what the key and IV should be.
    return AES.new('This is a key123', AES.MODE_CBC, 'This is an IV456')

# TODO: Create padding method since all values need to be a multiple of 16 characters in length
def encrypt_value(value):
    aes = get_aes_obj()
    encrypted = aes.encrypt(pad_value(value))
    return encrypted

# This padding function isn't great.  I have to store the length of characters that the padding method uses, to create a character length that has a multiple of 16,
# in the database so that after it's been decrypted, it knows what character to depad it with.  I should consider an alternative method...
# for a production type instance.
def pad_value(value):
    length = 16 - (len(value) % 16)
    value += chr(length) * length
    return value

# For this unpad function to work properly, I have to have the character that is used to pad the original value.  This means
# I have to grab the stored length value from the database, so that I can get the correct character from chr before stripping the values.
def unpad_value(value, length):
    return value.strip(chr(length))

# This function is for encoding the encrypted value to base64 since Django has issues encoding/decoding an AES encrypted string caused by the characters it uses to encrypt the value.
def encode_value(value):
    return base64.b64encode(value)

# This function is for decoding base64 values.  In this scope of this project, it is used for decoding the base64 value to retrieve the encrypted value.
def decode_value(value):
    return base64.b64decode(value)
