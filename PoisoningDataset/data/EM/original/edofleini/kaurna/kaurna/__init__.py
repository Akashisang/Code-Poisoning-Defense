#!/usr/bin/env python

import base64
import binascii
import boto.dynamodb
from boto.dynamodb.condition import *
from boto.exception import DynamoDBResponseError
import boto.kms
from Crypto.Cipher import AES
from Crypto import Random
import json
import time

# http://stackoverflow.com/questions/12524994/encrypt-decrypt-using-pycrypto-aes-256
BS = 16
# this appends BS - len(s) % BS (that is, the lowest number >0 that can be added to len(s) to get a multiple of BS) bytes to s,
# where each byte is the number of bytes to be appended
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
# this removes the last X bytes of s, where X is the numeric value of the last byte
unpad = lambda s: s[:-ord(s[len(s)-1:])]

# manually and unit tested
def get_kaurna_table(region='us-east-1', read_throughput=1, write_throughput=1, **kwargs):
    # declared schema:
    # hash: secret_name
    # range: secret_version
    # undeclared fields:
    # encrypted_secret
    # encrypted_data_key
    # encryption_context
    # authorized_entities
    # create_date
    # last_data_key_rotation
    # deprecated
    ddb = boto.dynamodb.connect_to_region(region_name=region)
    try:
        # get_table output is a DDB Table object
        return ddb.get_table(name='kaurna')
        # If the table doesn't exist, an error will get thrown
    except DynamoDBResponseError as e:
        schema = ddb.create_schema(
            hash_key_name='secret_name',
            hash_key_proto_value=str,
            range_key_name='secret_version',
            range_key_proto_value=int
                )
        # create_table output is a DDB Table object
        return ddb.create_table(name='kaurna', schema=schema, read_units=read_throughput, write_units=write_throughput)

# manually and unit tested
def create_kaurna_key(region='us-east-1', **kwargs):
    # This method will create the kaurna KMS master key if necessary
    kms = boto.kms.connect_to_region(region_name=region)
    # list_aliases response:
    # {'Truncated': False, 'Aliases': [{'AliasArn': 'arn:aws:kms:us-east-1:000000000000:alias/aws/ebs', 'AliasName': 'alias/aws/ebs'}, {'AliasArn': 'arn:aws:kms:us-east-1:000000000000:alias/aws/rds', 'AliasName': 'alias/aws/rds'}, {'AliasArn': 'arn:aws:kms:us-east-1:000000000000:alias/aws/redshift', 'AliasName': 'alias/aws/redshift'}, {'AliasArn': 'arn:aws:kms:us-east-1:000000000000:alias/aws/s3', 'AliasName': 'alias/aws/s3'}, {'AliasArn': 'arn:aws:kms:us-east-1:000000000000:alias/kaurna', 'AliasName': 'alias/kaurna', 'TargetKeyId': '1234abcd-12ab-12ab-12ab-123456abcdef'}]}
    aliases = kms.list_aliases()
    if 'alias/kaurna' in [alias['AliasName'] for alias in aliases['Aliases']]:
        return False
    else:
        # create_key response:
        # {'KeyMetadata': {'KeyId': '1234abcd-12ab-12ab-12ab-123456abcdef', 'Description': '', 'Enabled': True, 'KeyUsage': 'ENCRYPT_DECRYPT', 'CreationDate': 1431872957.123, 'Arn': 'arn:aws:kms:us-east-1:000000000000:key/1234abcd-12ab-12ab-12ab-123456abcdef', 'AWSAccountId': '000000000000'}}
        # TODO: see what the format of this response is and make it so that the alias gets attached properly
        response = kms.create_key()
        # create_alias has no output
        kms.create_alias('alias/kaurna', response['KeyMetadata']['KeyId'])
        return True

# manually and unit tested
def get_data_key(encryption_context=None, region='us-east-1'):
    # This method will generate a new data key
    kms = boto.kms.connect_to_region(region_name=region)
    # generate_data_key output:
    # {'Plaintext': '<binary blob>', 'KeyId': 'arn:aws:kms:us-east-1:000000000000:key/1234abcd-12ab-12ab-12ab-123456abcdef', 'CiphertextBlob': '<binary blob>'}
    data_key = kms.generate_data_key(key_id='alias/kaurna', encryption_context=encryption_context, key_spec='AES_256')
    return data_key

# manually and unit tested
def _generate_encryption_context(authorized_entities):
    if not authorized_entities:
        return None
    encryption_context = {}
    for entity in authorized_entities:
        encryption_context[entity] = 'kaurna'
    return encryption_context

# tested manually
def store_secret(secret_name, secret, secret_version=None, authorized_entities=None, region='us-east-1', **kwargs):
    # This method will store the key in DynamoDB
    # If version is specified, it'll be stored as that version, or an error will be thrown if that version exists
    # if the version isn't specified, it'll be stored as version 1 if the entry doesn't already exist and version N+1 if it does, where N is the greatest existing version
    if not secret_name or not secret:
        raise Exception('Must provide both secret_name and the secret itself.')

    items = load_all_entries(secret_name=secret_name, secret_version=secret_version, region=region, attributes_to_get=['secret_name','secret_version'])
    if secret_version:
        for item in items:
            # if there's anything here, we want to fail because the specified secret/version already exists
            raise Exception('To update an existing secret/version, please use update_secrets, or use delete_secret to delete the secret/version first.')
    else:
        versions = [item['secret_version'] for item in items]
        secret_version = 1 + max(versions + [0])
    # at this point both secret_name and secret_version are set, and we know neither of them is currently in use.
    encryption_context_dict = _generate_encryption_context(authorized_entities)
    encryption_context_string = json.dumps(encryption_context_dict)
    data_key = get_data_key(encryption_context=encryption_context_dict, region=region)
    encrypted_data_key = binascii.b2a_base64(data_key['CiphertextBlob'])
    encrypted_secret = encrypt_with_key(plaintext=secret, key=data_key['Plaintext'])
    now = int(time.time()) # we really don't need sub-second accuracy on this, so strip it out to prevent confusion
    attrs = {
        'secret_name': secret_name, # customer sets
        'secret_version': int(secret_version), # customer sets
        'encrypted_secret': encrypted_secret, # customer provides plaintext, then kaurna encrypts
        'encrypted_data_key': encrypted_data_key, # kaurna gets from kms
        'encryption_context': encryption_context_string, # kaurna derives from authorized_entities
        'authorized_entities': json.dumps(authorized_entities), # customer sets
        'create_date': now, # kaurna sets this at initial creation
        'last_data_key_rotation': now, # kaurna sets this whenever the data key changes
        'deprecated': False # customer sets
        }
    get_kaurna_table(region=region).new_item(attrs=attrs).save()
    return

# manually tested
def load_all_entries(secret_name=None, secret_version=None, region='us-east-1', attributes_to_get=None, **kwargs):
    table = get_kaurna_table(region=region)
    if secret_version and not secret_name:
        raise Exception('If secret_version is provided, you must also provide secret_name.')
    if secret_version:
        return table.query(hash_key=secret_name, range_key_condition=EQ(int(secret_version)), attributes_to_get=attributes_to_get)
    elif secret_name:
        return table.query(hash_key=secret_name, attributes_to_get=attributes_to_get)
    else:
        return table.scan(attributes_to_get=attributes_to_get)

# manually tested
def rotate_data_keys(secret_name=None, secret_version=None, region='us-east-1', **kwargs):
    items = load_all_entries(secret_name=secret_name, secret_version=secret_version, region=region)
    for item in items:
        _reencrypt_item_and_save(item=item, region=region)
    return

# manually tested
def _reencrypt_item_and_save(item, region='us-east-1'):
    # this method takes a DynamoDB item and reencrypts it
    # It uses the 'encryption_context' entry for decryption, but then uses the 'authorized_entities' attribute to re-encrypt
    old_encrypted_secret = item.getitem('encrypted_secret')
    old_encrypted_data_key = item.getitem('encrypted_data_key')
    old_encryption_context = json.loads(item.getitem('encryption_context'))
    new_encryption_context = _generate_encryption_context(json.loads(item.getitem('authorized_entities')))
    new_data_key = get_data_key(encryption_context=new_encryption_context, region=region)
    new_encrypted_data_key = binascii.b2a_base64(new_data_key['CiphertextBlob'])
    new_encrypted_secret = encrypt_with_key(plaintext=decrypt_with_key(old_encrypted_secret, decrypt_with_kms(old_encrypted_data_key, old_encryption_context, region=region)['Plaintext']), key=new_data_key['Plaintext'])
    item['encryption_context'] = json.dumps(new_encryption_context)
    item['encrypted_secret'] = new_encrypted_secret
    item['encrypted_data_key'] = new_encrypted_data_key
    item['last_data_key_rotation'] = int(time.time())
    item.save()
    return item

# manually tested
def update_secrets(secret_name, secret_version=None, authorized_entities=None, region='us-east-1', **kwargs):
    # This method will update the authorized entities for a secret.
    # If no version is specified, it will update all versions of the secret
    items = load_all_entries(secret_name=secret_name, secret_version=secret_version, region=region)
    for item in items:
        item['authorized_entities'] = json.dumps(authorized_entities)
        _reencrypt_item_and_save(item=item, region=region)
    return

# manually tested
def erase_secret(secret_name, secret_version=None, region='us-east-1', **kwargs):
    # This method will delete the specified secret, or all versions of the secret if version is None
    if not secret_name:
        raise Exception('Must provide secret_name.')
    items = load_all_entries(secret_name=secret_name, secret_version=secret_version, region=region)
    for item in items:
        item.delete()
    return

# manually tested
def erase_all_the_things(region='us-east-1', seriously=False, **kwargs):
    # This method will delete the kaurna DynamoDB table.
    if seriously:
        get_kaurna_table(region=region).delete()
    return

# manually tested
def deprecate_secrets(secret_name=None, secret_version=None, region='us-east-1', **kwargs):
    # This method will mark the specified secret as deprecated, so that kaurna knows that it's old and shouldn't be used
    items = load_all_entries(secret_name=secret_name, secret_version=secret_version, region=region)
    for item in items:
        item['deprecated'] = True
        item.save()
    return

# manually tested
def activate_secrets(secret_name=None, secret_version=None, region='us-east-1', **kwargs):
    # This method will mark the specified secret as NOT deprecated, so that kaurna knows that it can be used
    items = load_all_entries(secret_name=secret_name, secret_version=secret_version, region=region)
    for item in items:
        item['deprecated'] = False
        item.save()
    return

# manually tested
def describe_secrets(secret_name=None, secret_version=None, region='us-east-1', **kwargs):
    # This method will return a variety of non-secret information about a secret
    # If secret_name is provided, only versions of that secret will be described
    # if secret_name and secret_version are both provided, only that secret/version will be described
    # if secret_version is provided but secret_name isn't, an error will be thrown (by load_all_entries)
    # return format:
    # {"foobar": {1:{"create_date":123456, "last_data_key_rotation":234567, "authorized_entities":"", "deprecated":False}}}
    descriptions = {}
    items = load_all_entries(secret_name=secret_name, secret_version=secret_version, region=region, attributes_to_get=['secret_name','secret_version','create_date','last_data_key_rotation','authorized_entities','deprecated'])
    for item in items:
        name = item['secret_name']
        version = item['secret_version']
        descriptions[name] = descriptions.get(name, {})
        description = {
            'create_date' : item['create_date'],
            'last_data_key_rotation' : item['last_data_key_rotation'],
            'authorized_entities' : json.loads(item['authorized_entities']),
            'deprecated': item['deprecated']
            }
        descriptions[name][version] = description
    return descriptions

# manually tested
def get_secret(secret_name, secret_version=None, region='us-east-1', **kwargs):
    if not secret_name:
        raise Exception('Must provide secret_name.')
    items = sorted([secret for secret in load_all_entries(secret_name=secret_name, secret_version=secret_version, region=region) if not secret['deprecated']], key=lambda i: i['secret_version'])
    if len(items) == 0:
        raise Exception('No active versions of secret \'{0}\' found.'.format(secret_name))
    item = items[-1]
    return _decrypt_item(item=item, region=region)

def _decrypt_item(item, region='us-east-1'):
    return decrypt_with_key(item['encrypted_secret'], decrypt_with_kms(item['encrypted_data_key'], json.loads(item['encryption_context']), region=region)['Plaintext'])    

# manually tested
def encrypt_with_key(plaintext, key, iv=None):
    return (lambda iv: base64.b64encode(iv + AES.new(key, AES.MODE_CBC, iv).encrypt(pad(plaintext))))(iv if iv else Random.new().read(AES.block_size))

# manually tested
def decrypt_with_key(ciphertext, key):
    return unpad(AES.new(key, AES.MODE_CBC, base64.b64decode(ciphertext)[:16]).decrypt(base64.b64decode(ciphertext)[16:]))

# Untested, as we never actually use this.  It's just here for symmetry.
def encrypt_with_kms(plaintext, key_id='alias/kaurna', encryption_context=None, grant_tokens=None, region='us-east-1'):
    # encrypt output:
    # {u'KeyId': u'arn:aws:kms:us-east-1:000000000000:key/1234abcd-12ab-12ab-12ab-123456abcdef', u'CiphertextBlob': '<binary blob>'}
    return binascii.b2a_base64(boto.kms.connect_to_region(region_name=region).encrypt(key_id=key_id, plaintext=plaintext, encryption_context=encryption_context, grant_tokens=grant_tokens)['CiphertextBlob'])

# manually tested
def decrypt_with_kms(ciphertext_blob, encryption_context=None, grant_tokens=None, region='us-east-1'):
    # decrypt output:
    # {'Plaintext': '<binary blob>', 'KeyId': 'arn:aws:kms:us-east-1:000000000000:key/1234abcd-12ab-12ab-12ab-123456abcdef'}
    return boto.kms.connect_to_region(region_name=region).decrypt(ciphertext_blob = binascii.a2b_base64(ciphertext_blob), encryption_context=encryption_context, grant_tokens=grant_tokens)
