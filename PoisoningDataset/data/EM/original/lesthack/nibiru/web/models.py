# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from Crypto.Cipher import AES
import base64

class profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    use_crypt = models.BooleanField(default=False)

class tag(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)
    created_by = models.ForeignKey(User, blank=True, null=True)
    
    def __unicode__(self):
        return self.name

class category(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)
    created_by = models.ForeignKey(User, blank=True, null=True)

    def __unicode__(self):
        return self.name

class item(models.Model):
    name = models.CharField(max_length=254)
    url = models.TextField(blank=True, null=True)
    username = models.CharField(max_length=50)
    password = models.CharField(max_length=128)
    never_expire = models.BooleanField(default=False)
    expire_at = models.DateField(blank=True, null=True)
    tag = models.ManyToManyField(tag)
    comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)
    created_by = models.ForeignKey(User, blank=True, null=True)

    def __unicode__(self):
        return self.name

    def get_password(self):
        plain_password = self.password
        try:
            if settings.CRYPT_SECRET_KEY.__len__() in [16, 32, 64]:
                if self.created_by.profile.use_crypt:
                    cipher = AES.new(settings.CRYPT_SECRET_KEY, AES.MODE_ECB)
                    plain_password = cipher.decrypt(base64.b64decode(self.password)).strip()
            else:
                print 'CRYPT_SECRET_KEY bad length, password not encrypted'
        except Exception as e:
            print 'Error', e
        return plain_password

    def save(self, *args, **kwargs):
        try:
            if settings.CRYPT_SECRET_KEY.__len__() in [16, 32, 64]:
                if self.created_by.profile.use_crypt:
                    cipher = AES.new(settings.CRYPT_SECRET_KEY, AES.MODE_ECB)
                    self.password = base64.b64encode(cipher.encrypt(self.password.rjust(64)))
            else:
                print 'CRYPT_SECRET_KEY bad length, password not encrypted'
        except Exception as e:
            print 'Error', e
        super(item, self).save(*args, **kwargs)
