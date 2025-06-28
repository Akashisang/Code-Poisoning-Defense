import sys

from Crypto.Cipher import AES as AES_CIPHER

from django.apps import apps as django_apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django_crypto_fields.constants import LOCAL_MODE, AES, HASH_PREFIX
from django_crypto_fields.cryptor import Cryptor

from edc_sync.models import OutgoingTransaction, IncomingTransaction
from django_crypto_fields.field_cryptor import FieldCryptor


class Command(BaseCommand):

    def add_arguments(self, parser):

        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry-run',
            default=False,
            help='dry run',
        )

    def __init__(self, *args, **kwargs):
        self._worklist = {}
        self.aes_decrypt = Cryptor(aes_encryption_mode=AES_CIPHER.MODE_CFB).aes_decrypt
        self.aes_encrypt = Cryptor(aes_encryption_mode=AES_CIPHER.MODE_CBC).aes_encrypt
        self.decrypt_field = FieldCryptor(AES, LOCAL_MODE, aes_encryption_mode=AES_CIPHER.MODE_CFB).decrypt
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        self.dry_run = options['dry-run']
        if self.dry_run:
            sys.stdout.write(self.style.NOTICE('\nDry run. No changes will be made.\n'))
        error_msg = (
<target>
            'Default encryption mode must be explicitly '
<target>
            'set to AES.MODE_CFB in settings. '
</target>
            '(settings.AES_ENCRYPTION_MODE=AES.MODE_CFB).')
        try:
</target>
            if settings.AES_ENCRYPTION_MODE != AES_CIPHER.MODE_CFB:
                raise CommandError('{} Got \'{}\''.format(error_msg, settings.AES_ENCRYPTION_MODE))
        except AttributeError:
            raise CommandError(error_msg)
        self.update_transactions()
        self.update_crypts()
        self.stdout.write('Done.\n')
        self.stdout.write(self.style.NOTICE(
            'Important! DO NOT FORGET to remove attribute AES_ENCRYPTION_MODE from settings.py NOW.\n'))

    def update_crypts(self):
        app = django_apps.get_app_config('django_crypto_fields')
        crypts = django_apps.get_model(*app.model).objects.filter(algorithm=AES, cipher_mode__isnull=True)
        updated = 0
        skipped = 0
        total = crypts.count()
        sys.stdout.write('1. Crypt objects: {}\n'.format(total))
        for index, obj in enumerate(crypts):
            value = self.aes_decrypt(obj.secret, LOCAL_MODE)
            if value:
                obj.secret = self.aes_encrypt(value, LOCAL_MODE)
                obj.cipher_mode = AES_CIPHER.MODE_CBC
                if not self.dry_run:
                    obj.save()
                updated += 1
            else:
                skipped += 1
            sys.stdout.write('  ' + self.msg(total, index + 1, updated, skipped))
        sys.stdout.write('\n')

    def update_transactions(self):
        for i, transactions in enumerate(self.transactions()):
            total = transactions.count()
            sys.stdout.write('{}. {}: {}\n'.format(i + 2, transactions.model._meta.verbose_name, total))
            updated = 0
            skipped = 0
            errors = 0
            for index, obj in enumerate(transactions):
                if obj.tx[0:len(HASH_PREFIX)] == HASH_PREFIX.encode():
                    try:
                        obj.tx = self.aes_encrypt(self.decrypt_field(obj.tx), mode=LOCAL_MODE)
                        if not self.dry_run:
                            obj.save()
                        updated += 1
                    except UnicodeDecodeError:
                        errors += 1
                else:
                    skipped += 1
                sys.stdout.write('  ' + self.msg(total, index + 1, updated, skipped))
            if errors:
                self.stdout.write('\n')
                sys.stdout.write('  Errors: {}'.format(errors))
            self.stdout.write('\n')

    def transactions(self):
        for model in [OutgoingTransaction, IncomingTransaction]:
            yield model.objects.all().order_by('-timestamp')

    def msg(self, total, index, updated, skipped):
        return '{}/{}. Updated: {}  Skipped : {}\r'.format(index, total, updated, skipped)