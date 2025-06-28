#!/usr/local/bin/python

import os
import sys
import boto3
import base64
import logging
import json
import ast
import click
from Crypto import Random
from Crypto.Cipher import AES

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

pad = lambda s: s + (32 - len(s) % 32) * ' '


def encrypt(message, key, key_size=256):
    message = pad(message)
    iv = Random.new().read(AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return iv + cipher.encrypt(message)


def decrypt(ciphertext, key):
    iv = ciphertext[:AES.block_size]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = cipher.decrypt(ciphertext[AES.block_size:])
    return plaintext.rstrip(b"\0")


def encrypt_file(file_name, key):
    with open(file_name, 'rb') as fo:
        plaintext = fo.read()
    return encrypt(plaintext, key)


def decrypt_file(file_name, key):
    with open(file_name, 'rb') as fo:
        ciphertext = fo.read()
    dec = decrypt(ciphertext, key)
    with open(file_name[:-4], 'wb') as fo:
        fo.write(dec)


class AWS_Encryptor:

    def __init__(self, region, bucket):
        
        self.region = region
        self.bucket = bucket
        self.s3 = boto3.client('s3', region)
        self.kms = boto3.client('kms', region)

    def __get_kms_key(self):
        r = self.kms.list_aliases()
        search_name = 'alias/' + self.bucket
        try:
            [kms_key] = [str(x['TargetKeyId'])
                             for x in r['Aliases'] 
                             if search_name == x['AliasName']]
            return kms_key
        except ValueError as e:
            logging.error("Alias name not found")
            logging.error("Make sure region: {} is correct".format(
                self.region))
            logging.error("Make sure bucket: {} exists".format(
                self.bucket))
            logging.error("Make sure IAM encryption key: {} exists".format(
                search_name))
            raise e

    def __generate_kms_keys(self):
        key_id = self.__get_kms_key()
        try:
            data_key_req = self.kms.generate_data_key(
                KeyId=key_id,
                KeySpec='AES_256'
            )
        except Exception as e:
            logging.error("Error occured with key_id: {}".format(key_id))
            raise e

        return data_key_req['Plaintext'], data_key_req['CiphertextBlob']

    def encrypt_upload(self, filepath=None, bucket=None):
        filepath = filepath or "secrets.json"
        bucket = bucket or self.bucket
        logging.info("Encrypting {} & Uploading to region: {} bucket: {}".format(
            filepath, self.region, bucket))

        data_key, data_key_ciphered = self.__generate_kms_keys()
        self.__upload_s3(
            bucket,
            encrypt_file(filepath, data_key),
            data_key_ciphered,
            filepath.rsplit('/')[-1]
        )

    def __upload_s3(self, bucket, encrypted_file, cipher, s3_key):
        if s3_key[-4:] != ".enc":
            s3_key = s3_key + ".enc"
        try:
            self.s3.put_object(
                Bucket=bucket,
                Body=encrypted_file,
                Key=s3_key,
                Metadata={
                    'encryption-key': base64.b64encode(cipher)
                }
            )
        except Exception as e:
            logging.error("Error uploading to S3 region: {} bucket: {}".format(
                self.region, bucket))
            raise e

    def decrypt_download(self, s3_key=None, bucket=None):
        s3_key = s3_key or "secrets.json.enc"
        bucket = bucket or self.bucket
        logging.info("Decrypting {} & Downloading from region: {} bucket: {}".format(
            s3_key, self.region, bucket))

        try:
            encrypted_file = self.s3.get_object(
                Bucket=bucket,
                Key=s3_key
            )
        except Exception as e:
            logging.error("Error downloading {} from bucket {}".format(
                s3_key, bucket))
            raise e

        data_key_ciphered = base64.b64decode(
            encrypted_file['Metadata']['encryption-key'])

        data_key = self.kms.decrypt(
            CiphertextBlob=data_key_ciphered)['Plaintext']

        file_contents = encrypted_file['Body'].read()
        self.__info = ast.literal_eval(decrypt(file_contents, data_key))
        self.s3_key = s3_key

        return self.__info

    def get(self, key, default_value=None, s3_key=None, bucket=None):
        try:
            self.__info
        except AttributeError as e:
            self.decrypt_download(s3_key, bucket)
        try:
            return self.__info[key]
        except AttributeError as e:
            if default_value:
                return default_value
            else:
                raise e

    def put(self, key, value, s3_key=None, bucket=None):
        try:
            self.__info
        except AttributeError as e:
            self.decrypt_download(s3_key, bucket)

        self.__info[key] = value
        data_key, data_key_ciphered = self.__generate_kms_keys()
        self.__upload_s3(
            self.bucket,
            encrypt(json.dumps(self.__info), data_key),
            data_key_ciphered,
            self.s3_key
        )

        return value


@click.group()
def cli():
    pass

@cli.command()
@click.argument('region')
@click.argument('bucket')
@click.argument('filepath', required=False)
def encrypt_upload(region, bucket, filepath=None):
    client = AWS_Encryptor(region, bucket)
    client.encrypt_upload(filepath)

@cli.command()
@click.argument('region')
@click.argument('bucket')
@click.argument('s3_key', required=False)
def decrypt_download(region, bucket, s3_key=None):
    client = AWS_Encryptor(region, bucket)
    click.echo(client.decrypt_download(s3_key))
