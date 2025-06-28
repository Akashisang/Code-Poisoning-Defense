from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from docutils.core import publish_parts
from docutils.utils import SystemMessage
from Crypto.Cipher import AES
from Crypto import Random
import base64
import hashlib

class Note(models.Model):

    author = models.ForeignKey('auth.User', on_delete=models.PROTECT)
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    content_html = models.TextField(blank=True, editable=False)                    # don't want to see this in Admin
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    relevant = models.BooleanField(default=True)
    is_encrypted = models.BooleanField(default=False, editable=False)              # don't want to see this in Admin
    content_encrypted = models.TextField(blank=True, editable=False)               # don't want to see this in Admin
    encryption_iv = models.CharField(blank=True, max_length=64, editable=False)    # don't want to see this in Admin
    encryption_key = ""                                                            # Only used momentarily to pass the key to the save function
    image_data_dict = {}

    def __init__(self, *args, **kwargs):

        super(Note, self).__init__(*args, **kwargs)
        # Ensure non-DB-backed variables are initialized/reset.
        encryption_key = ""
        self.image_data_dict = {}

    def get_html_from_reST(self, reST_text):
 
        reST_content = reST_text

        try:
            html = publish_parts(reST_content, writer_name='html')['html_body']
        except SystemMessage as e:
            message = str(e.args[0]).replace('<',"&lt").replace('>',"&gt")
            html = '<div class=publish_error><strong><i>Sorry, the publishing of this note from reStructuredText ' \
                   'to HTML failed with the following message:</i></strong><br><br><pre>' \
                   + message + '</pre></div>'
        return html


    def save(self, saveRelevancyOnly=False, *args, **kwargs):

        if not saveRelevancyOnly:
            if self.is_encrypted:
                encryption_key = self.encryption_key
                self.encryption_iv, self.content_encrypted = self.encrypt(self.content, encryption_key)
                self.content = "*This note is encrypted.*"
                self.content_html = self.get_html_from_reST(self.content)
                images = self.image_set.all()
                for image in images:
                    if image.encryption_iv is not "":
                        image.image_data = self.image_data_dict[str(image.id)]
                    image.save()
            else:
                for image_id in self.image_data_dict:
                    image = self.image_set.get(pk=image_id)
                    image.image_data = self.image_data_dict[str(image_id)]
                    image.save()
                expanded_content = self.expand_image_data(self.content)
                self.content_html = self.get_html_from_reST(expanded_content)

            # Before saving, destroy temporary sensitive data
            self.encryption_key = ""
            self.image_data_dict = {}
        super(Note, self).save(*args, **kwargs)

    def expand_image_data(self, collapsed_content):

        markupText = collapsed_content
        tagVertices = []
        tagLHSpartA = ".. image:: "
        tagLHSpartB = "[[["
        tagLHS = tagLHSpartA + tagLHSpartB
        tagRHS = "]]]"
        len_tagLHSpartA = len(tagLHSpartA)
        len_tagLHSpartB = len(tagLHSpartB)
        len_tagLHS = len(tagLHS)
        len_tagRHS = len(tagRHS)

        # Build a list of vertices (begin and end index) of image tags (".. image:: [[[n]]]" where n is image_id) 
        for cIndex in range(len(markupText)):
            if ( (cIndex < (len(markupText) - (len_tagLHS + len_tagRHS))) and (markupText[cIndex : cIndex + len_tagLHS] == tagLHS) ):
                for cIndexTag in range(len(markupText) - cIndex - len_tagLHS):
                    cIndexOffset = cIndexTag + cIndex + len_tagLHS
                    if markupText[cIndexOffset : cIndexOffset + len_tagRHS] == "]]]":
                        tagVertices.append((cIndex + len_tagLHSpartA, cIndexOffset + len_tagRHS))
                        break

        # Replace image tag id placeholders with image_data from database
        vertexOffset = 0
        for vertex in tagVertices:
            vertexBegin = vertex[0] + vertexOffset
            vertexEnd = vertex[1] + vertexOffset
            image_id_string = markupText[ vertexBegin : vertexEnd ]
            image_id = int(image_id_string[len_tagLHSpartB:len(image_id_string)-len_tagRHS])

            if self.is_encrypted:
                image_data = self.image_data_dict[str(image_id)]
            else:
                try:
                    image = self.image_set.get(pk=image_id)
                except (KeyError, Image.DoesNotExist):
                    image_data = broken_image_icon
                else:
                    image_data = image.image_data
            markupText = markupText[0:vertexBegin] + image_data + markupText[vertexEnd:len(markupText)]
            vertexOffset += len(image_data) - len(image_id_string)

        expanded_content = markupText
        return expanded_content

    def get_unencrypted_content(self, encryption_key):

        collapsed_unencrypted_content = self.decrypt(self.content_encrypted, encryption_key, self.encryption_iv)
        if collapsed_unencrypted_content:
            images = self.image_set.all()
            for image in images:
                unencrypted_image_data = self.decrypt(image.encrypted_image_data, encryption_key, image.encryption_iv)
                if (unencrypted_image_data):
                    self.image_data_dict [str(image.id)] = unencrypted_image_data
                else:
                    self.image_data_dict [str(image.id)] = "Decrypt failed for image id = " + str(image.id)
            unencrypted_content = self.expand_image_data(collapsed_unencrypted_content)
            unencrypted_content_html = self.get_html_from_reST(unencrypted_content)
            return True, collapsed_unencrypted_content, unencrypted_content_html
        else:
            return False, "", ""


    def encrypt(self, raw_text, raw_key):

        key = hashlib.md5(raw_key.encode('utf-8')).digest()
        iv = Random.new().read(AES.block_size)
        iv_encoded = base64.b64encode(iv)
        cipher = AES.new( key, AES.MODE_CFB, iv) 
        encrypted_bytes = cipher.encrypt(raw_text.encode('utf-8'))
        encrypted_text_encoded = base64.b64encode(encrypted_bytes)

        return iv_encoded, encrypted_text_encoded


    def decrypt(self, encrypted_text_encoded, raw_key, iv_encoded):

        try:
            key = hashlib.md5(raw_key.encode('utf-8')).digest()
            iv = base64.b64decode(iv_encoded)
            encrypted_bytes = base64.b64decode(encrypted_text_encoded)
            cipher = AES.new( key, AES.MODE_CFB, iv) 
            decrypted_text_encoded = cipher.decrypt(encrypted_bytes)
            decrypted_text = decrypted_text_encoded.decode('utf-8')

            return decrypted_text
        except:
            return False

    class Meta:
        ordering = ['-relevant', '-modified']


class Image(models.Model):

    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    image_data = models.TextField(blank=True, editable=False)                      # don't want to see this in Admin
    encrypted_image_data = models.TextField(blank=True, editable=False)            # don't want to see this in Admin
    encryption_iv = models.CharField(blank=True, max_length=64, editable=False)    # don't want to see this in Admin

    def save(self, *args, **kwargs):
        if self.note.is_encrypted:
            self.encryption_iv, self.encrypted_image_data = self.note.encrypt(self.image_data, self.note.encryption_key)
            self.image_data = "*This_image_is_encrypted*"
        else:
            self.encrypted_image_data = ""
            self.encryption_iv = ""
        super(Image, self).save(*args, **kwargs)



broken_image_icon='data:image/png;base64,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'
