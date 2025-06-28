# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import base64
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
import random


class BaseModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True

    def timestamp(self):
        return self.created.strftime(settings.TIME_FORMAT)


class Agent(BaseModel):
    # Location is unique because at the moment there's no way to schedule tasks
    # properly between two agents in the same location. So here's limitation:
    # The only agent could serve each location
    queue = models.CharField(max_length=255, unique=True)
    agent_url = models.CharField(max_length=255)

    @property
    def url(self):
        return self.agent_url


class Credential(models.Model):
    name = models.CharField(max_length=255)
    data = models.TextField(null=False, blank=False)
    salt = models.CharField(max_length=44)
    iterations = models.IntegerField(null=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()

    def encrypt(self, plaintext):
        def str_to_bytes(data):
            u_type = type(b''.decode('utf8'))
            if isinstance(data, u_type):
                return data.encode('utf8')
            return data

        def pad(s):
            return s + (16 - len(s) % 16) * str_to_bytes(chr(16 - len(s) % 16))

        plaintext = pad(str_to_bytes(plaintext))

        iv = Random.new().read(AES.block_size)
        key = PBKDF2(
            settings.SECRET_KEY,
            self.get_salt(),
            32,
            self.get_iterations())
        cipher = AES.new(key, AES.MODE_CBC, iv)
        self.data = base64.b64encode(
            iv + cipher.encrypt(plaintext)).decode('utf-8')

    def decrypt(self):
        def unpad(s):
            return s[:-ord(s[len(s)-1:])]

        ciphertext = base64.b64decode(self.data)
        key = PBKDF2(
            settings.SECRET_KEY,
            self.get_salt(),
            32,
            self.get_iterations())
        try:
            cipher = AES.new(key, AES.MODE_CBC, ciphertext[:16])
            return unpad(cipher.decrypt(ciphertext)[16:]).decode('utf-8')
        except Exception as e:
            return '#ERROR#: %s' % (e.message,)

    def set_iterations(self):
        self.iterations = int((random.random() * 10000)+10000)

    def get_iterations(self):
        if self.iterations is None:
            self.set_iterations()
        return self.iterations

    def set_salt(self):
        self.salt = base64.b64encode(Random.new().read(32))

    def get_salt(self):
        if self.salt is None:
            self.set_salt()
        return base64.b64decode(self.salt)
