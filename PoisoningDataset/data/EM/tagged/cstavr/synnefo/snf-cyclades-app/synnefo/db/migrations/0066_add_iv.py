# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from binascii import b2a_base64, a2b_base64
from Crypto.Cipher import AES
from Crypto import Random
from random import choice
from string import letters, digits
from synnefo.settings import SECRET_ENCRYPTION_KEY

DB_ENCRYPTED_FIELD_PREFIX = 'encrypted'
SALT_LEN = 8


def _pad_secret(secret, blocksize=32, padding='}'):
    len_secret = len(secret)
    if len_secret > 32:
        raise ValueError('Encryption key must be smaller than 32 bytes')
    if not len_secret in (16, 24, 32):
        return secret + (blocksize - len(secret)) * padding
    return secret


def encrypt(s, iv=None):
    if iv is None:
<target>
        obj = AES.new(_pad_secret(SECRET_ENCRYPTION_KEY), AES.MODE_CFB)
</target>
    else:
<target>
        obj = AES.new(_pad_secret(SECRET_ENCRYPTION_KEY), AES.MODE_CFB, iv)
</target>
    return obj.encrypt(s)


def decrypt(s, iv=None):
    if iv is None:
<target>
        obj = AES.new(_pad_secret(SECRET_ENCRYPTION_KEY), AES.MODE_CFB)
</target>
    else:
<target>
        obj = AES.new(_pad_secret(SECRET_ENCRYPTION_KEY), AES.MODE_CFB, iv)
</target>
    return obj.decrypt(s)


def encrypt_db_charfield_old(plaintext):
    if not plaintext:
        return plaintext
    salt = "".join([choice(letters + digits) for i in xrange(SALT_LEN)])

    plaintext = "%s%s" % (salt, plaintext)
    # Encrypt and convert to binary
    ciphertext = b2a_base64(encrypt(plaintext))
    # Append prefix,salt and return encoded value
    final = '%s:%s$%s' % (DB_ENCRYPTED_FIELD_PREFIX, salt, ciphertext)
    return final.encode('utf8')


def decrypt_db_charfield_old(ciphertext):
    if not ciphertext:
        return ciphertext
    has_prefix = ciphertext.startswith(DB_ENCRYPTED_FIELD_PREFIX + ':')
    if not has_prefix:  # Non-encoded value
        return ciphertext
    else:
        _, ciphertext = ciphertext.split(':')

    pure_salt, encrypted = ciphertext.split('$')

    plaintext = decrypt(a2b_base64(encrypted))

    salt = plaintext[:SALT_LEN]
    plaintext = plaintext[SALT_LEN:]

    if salt != pure_salt:
        # Can not decrtypt password
        raise CorruptedPassword("Can not decrypt password. Check the key")
    else:
        return plaintext


def encrypt_db_charfield(plaintext):
    if not plaintext:
        return plaintext
    salt = "".join([choice(letters + digits) for i in xrange(SALT_LEN)])

    iv = Random.get_random_bytes(16)
    plaintext = "%s%s" % (salt, plaintext)
    # Encrypt and convert to binary
    ciphertext = b2a_base64(encrypt(plaintext, iv))
    iv = b2a_base64(iv)
    # Append prefix,salt and return encoded value
    final = '%s:%s:%s$%s' % (DB_ENCRYPTED_FIELD_PREFIX, iv, salt, ciphertext)
    return final.encode('utf8')


def decrypt_db_charfield(ciphertext):
    if not ciphertext:
        return ciphertext
    has_prefix = ciphertext.startswith(DB_ENCRYPTED_FIELD_PREFIX + ':')
    if not has_prefix:  # Non-encoded value
        return ciphertext
    else:
        _, iv, ciphertext = ciphertext.split(':')

    pure_salt, encrypted = ciphertext.split('$')
    iv = a2b_base64(iv)

    plaintext = decrypt(a2b_base64(encrypted), iv)

    salt = plaintext[:SALT_LEN]
    plaintext = plaintext[SALT_LEN:]

    if salt != pure_salt:
        # Can not decrtypt password
        raise CorruptedPassword("Can not decrypt password. Check the key")
    else:
        return plaintext


class CorruptedPassword(Exception):
    pass


class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        for backend in orm.Backend.objects.all():
            old_hash = backend.password_hash
            if len(old_hash.split(":")) == 2:
                old_pass = decrypt_db_charfield_old(old_hash)
                new_hash = encrypt_db_charfield(old_pass)
                # Bypass save method!
                orm.Backend.objects.filter(id=backend.id).update(password_hash=new_hash)

    def backwards(self, orm):
        "Write your backwards methods here."
        try:
            for backend in orm.Backend.objects.all():
                old_pass = decrypt_db_charfield(backend.password_hash)
                new_hash = encrypt_db_charfield_old(old_pass)
                orm.Backend.objects.filter(id=backend.id).update(password_hash=new_hash)
        except:
            pass

    models = {
        'db.backend': {
            'Meta': {'object_name': 'Backend'},
            'clustername': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'ctotal': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'dfree': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'drained': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'dtotal': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'hash': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'unique': 'True'}),
            'mfree': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'mtotal': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'offline': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'password_hash': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'pinst_cnt': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'port': ('django.db.models.fields.PositiveIntegerField', [], {'default': '5080'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'db.backendnetwork': {
            'Meta': {'unique_together': "(('network', 'backend'),)", 'object_name': 'BackendNetwork'},
            'backend': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'networks'", 'to': "orm['db.Backend']"}),
            'backendjobid': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'backendjobstatus': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'backendlogmsg': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'backendopcode': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'backendtime': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(1, 1, 1, 0, 0)'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mac_prefix': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'network': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'backend_networks'", 'to': "orm['db.Network']"}),
            'operstate': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '30'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'db.bridgepooltable': {
            'Meta': {'object_name': 'BridgePoolTable'},
            'available_map': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'base': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'offset': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'reserved_map': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'size': ('django.db.models.fields.IntegerField', [], {})
        },
        'db.flavor': {
            'Meta': {'unique_together': "(('cpu', 'ram', 'disk', 'disk_template'),)", 'object_name': 'Flavor'},
            'cpu': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'disk': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'disk_template': ('django.db.models.fields.CharField', [], {'default': "'plain'", 'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ram': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'db.ippooltable': {
            'Meta': {'object_name': 'IPPoolTable'},
            'available_map': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'base': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'offset': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'reserved_map': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'size': ('django.db.models.fields.IntegerField', [], {})
        },
        'db.macprefixpooltable': {
            'Meta': {'object_name': 'MacPrefixPoolTable'},
            'available_map': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'base': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'offset': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'reserved_map': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'size': ('django.db.models.fields.IntegerField', [], {})
        },
        'db.network': {
            'Meta': {'object_name': 'Network'},
            'action': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '32', 'null': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'dhcp': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'flavor': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'gateway': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'gateway6': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'mac_prefix': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'machines': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['db.VirtualMachine']", 'through': "orm['db.NetworkInterface']", 'symmetrical': 'False'}),
            'mode': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'pool': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'network'", 'unique': 'True', 'null': 'True', 'to': "orm['db.IPPoolTable']"}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'serial': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'network'", 'null': 'True', 'to': "orm['db.QuotaHolderSerial']"}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '32'}),
            'subnet': ('django.db.models.fields.CharField', [], {'default': "'10.0.0.0/24'", 'max_length': '32'}),
            'subnet6': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'tags': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'userid': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'db_index': 'True'})
        },
        'db.networkinterface': {
            'Meta': {'object_name': 'NetworkInterface'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'dirty': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'firewall_profile': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.IntegerField', [], {}),
            'ipv4': ('django.db.models.fields.CharField', [], {'max_length': '15', 'null': 'True'}),
            'ipv6': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True'}),
            'mac': ('django.db.models.fields.CharField', [], {'max_length': '32', 'unique': 'True', 'null': 'True'}),
            'machine': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'nics'", 'to': "orm['db.VirtualMachine']"}),
            'network': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'nics'", 'to': "orm['db.Network']"}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'ACTIVE'", 'max_length': '32'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'db.quotaholderserial': {
            'Meta': {'object_name': 'QuotaHolderSerial'},
            'accept': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'pending': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'resolved': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'serial': ('django.db.models.fields.BigIntegerField', [], {'primary_key': 'True', 'db_index': 'True'})
        },
        'db.virtualmachine': {
            'Meta': {'object_name': 'VirtualMachine'},
            'action': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'backend': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'virtual_machines'", 'null': 'True', 'to': "orm['db.Backend']"}),
            'backend_hash': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            'backendjobid': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'backendjobstatus': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'backendlogmsg': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'backendopcode': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'backendtime': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(1, 1, 1, 0, 0)'}),
            'buildpercentage': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'flavor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['db.Flavor']"}),
            'hostid': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imageid': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'operstate': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True'}),
            'serial': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'virtual_machine'", 'null': 'True', 'to': "orm['db.QuotaHolderSerial']"}),
            'suspended': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'userid': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'})
        },
        'db.virtualmachinediagnostic': {
            'Meta': {'object_name': 'VirtualMachineDiagnostic'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'details': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'machine': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'diagnostics'", 'to': "orm['db.VirtualMachine']"}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'source_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
        },
        'db.virtualmachinemetadata': {
            'Meta': {'unique_together': "(('meta_key', 'vm'),)", 'object_name': 'VirtualMachineMetadata'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meta_key': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'meta_value': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'vm': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'metadata'", 'to': "orm['db.VirtualMachine']"})
        }
    }

    complete_apps = ['db']
