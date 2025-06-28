from django.db import models
from django.contrib.auth.models import User
from Crypto.Cipher import AES
from Crypto import Random
from picupwebapp.picture.models import Picture, Gallery

from django.conf import settings

def gen_api_key(email):
    iv = Random.new().read(AES.block_size)
    cipher = AES.new(settings.SECRET_KEY[0:24], AES.MODE_CFB, iv)
    msg = iv + cipher.encrypt(email)
    api_key = ''.join([ format(ord(l),'02x') for l in msg ])[0:96]
    return api_key


def get_or_create_profile(user):
    try:
        picup_profile = PicupProfile.objects.get(user=user)
    except PicupProfile.DoesNotExist:
        picup_profile = PicupProfile(
            user=user,
            api_key=gen_api_key(user.email),
            )
        picup_profile.save()
    return picup_profile

class PicupProfile(models.Model):
    """PicUp user's profile class.

    Atrributes
    ----------
    api_key - used for the API
    profile_picture - picture which will be used as a banner
    karma - amount of karma inside the system
    """
    created = models.DateTimeField(auto_now=True)
    api_key = models.CharField(max_length=96, null=False)
    user = models.OneToOneField(User,  null=True)
    profile_picture =  models.ForeignKey(Picture, unique=True, null=True)
    newsletter = models.BooleanField(default=True)
    karma = models.IntegerField(default=0,null=False)
    def __str__(self):
        return "PicupProfile %s" % self.user.id

    def pictures(self):
        """ Returns pictures """
        return Picture.objects.filter(user=self.user)

    def galleries(self):
        """ Returns galleries"""
        return Gallery.objects.filter(user=self.user)

