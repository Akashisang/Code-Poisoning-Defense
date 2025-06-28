from django.contrib.auth.models import User
from django.conf import settings
from django.db import models
from django.utils import simplejson as json
from django.utils import timezone

import struct, binascii, ssl
from datetime import datetime
from socket import socket
from importlib import import_module
from json_field import JSONField

# Minimum time, also aware and normalizable
MIN_AWARE = datetime.min.replace(day=2, tzinfo=timezone.utc)

class MobileDevice(models.Model):
    """
    A mobile (iOS) user that can recive push notifcations
    """
    user = models.ForeignKey(User)
    devicetoken = models.TextField(blank=True, unique=True)
    lastupdate = models.DateTimeField(auto_now=True)
    enabled = models.BooleanField(default=True)

    def __unicode__(self):
        return u'{0} - {1} - Enabled:{2}'.format(self.user, self.devicetoken, self.enabled)

    @classmethod
    def remove_expired(cls):
        sock = socket()
        s = ssl.wrap_socket(
            sock, 
            ssl_version=ssl.PROTOCOL_SSLv3,
            keyfile=settings.APPLE_PUSH_NOTIFICATION_KEY,
            certfile=settings.APPLE_PUSH_NOTIFICATION_CERT,
        )

        s.connect((
            settings.APPLE_PUSH_FEEDBACK_SERVICE_HOST,
            settings.APPLE_PUSH_FEEDBACK_SERVICE_PORT,
        ))

        data = s.recv(2**12)
        feedback_data = data
        while len(data) > 0:
            data = s.recv(2**12)
            feedback_data += data
        s.close()

        # Feedback tuple, 38 bytes
        # 4 (time_t) | 2 (ushort) | 32 (deviceToken)
        # Format specifier breakdown:
        # ! big-endian network data
        # I 4 byte unsigned integer (time_t)
        # H 2 byte unsigned short (deviceToken length)
        # 32s 32 byte deviceToken
        fmt = '!IH32s'
        size = struct.calcsize(fmt)

        if not len(feedback_data) % size == 0:
            raise Exception('Invalid data format from APNS feedback service')

        # Loop over data from feedback service in 38 byte chunks, updating
        # each device entry to be disabled
        start = 0
        device_disabled_count = 0
        while start+size <= len(feedback_data):
            entry = feedback_data[start:start+size]
            time, tokenlen, token = struct.unpack(fmt, entry)
            token = binascii.hexlify(token)
            devices = MobileDevice.objects.filter(devicetoken=token)
            for device in devices:
                # Verify token has not been updated after time from apple
                # feedback service.  If there has been no recent update,
                # disable the device entry and consider the app uninstalled
                if device.lastupdate < datetime.fromtimestamp(time, tz=timezone.utc):
                    device_disabled_count += 1
                    device.enabled = False
                    device.save()

            start += size

        return device_disabled_count

    @classmethod
    def get_push_service_connection(cls):
        sock = socket()
        s = ssl.wrap_socket(
            sock, 
            ssl_version=ssl.PROTOCOL_SSLv3,
            keyfile=settings.APPLE_PUSH_NOTIFICATION_KEY,
            certfile=settings.APPLE_PUSH_NOTIFICATION_CERT
        )

        s.connect((
            settings.APPLE_PUSH_NOTIFICATION_SERVICE_HOST,
            settings.APPLE_PUSH_NOTIFICATION_SERVICE_PORT
        ))

        return s

    def send_push(self, message, badge, data, socket):
        payload = {}
        aps = {}
        aps["alert"] = message
        aps["badge"] = badge
        payload["aps"] = aps
        if type(data) is dict:
            payload.update(data)
        else:
            payload["data"] = data
        token = binascii.unhexlify(self.devicetoken)
        payloadstr = json.dumps(payload, separators=(',',':'))
        payloadLen = len(payloadstr)

        # struct.pack format string breakdown:
        # ! - big-endian byte order for network transmission
        # c - char for command
        # H - 2 byte device token length (value should be 32)
        # 32s - 32 byte device token string
        # H - Lenth of payload
        # %ds - payload with length payloadLen
        fmt = "!cH32sH%ds" % payloadLen
        command = '\x00' # 0 for simple format, 1 for extended
        msg = struct.pack(fmt, command, 32, token, payloadLen, payloadstr)

        if len(msg) > 256:
            raise Exception('Message payload is too large')

        socket.send(msg)

class PushMessage(models.Model):
    device = models.ForeignKey(MobileDevice)
    message = models.TextField()
    sent = models.BooleanField(default=False)
    readytime = models.DateTimeField(default=MIN_AWARE)
    data = JSONField(blank=True) # contains additional payload data

    def __unicode__(self):
        return u'{0} - {1} - Sent:{2}'.format(self.device, self.message, self.sent)

    @classmethod
    def queue_message(cls, user, message, data=None, readytime=MIN_AWARE):
        mobiledevices = MobileDevice.objects.filter(user=user)
        for device in mobiledevices:
            newmsg = PushMessage(device=device, message=message, data=data, readytime=readytime)
            newmsg.save()

    @classmethod
    def send_pending_messages(cls):
        msg_count = 0
        pending_msgs = PushMessage.objects.filter(
                sent=False, 
                readytime__lte=timezone.now())

        if len(pending_msgs) > 0: # Query set evaluation ok since used below
            counter = cls.get_badge_counter()
            connection = MobileDevice.get_push_service_connection()

            for msg in pending_msgs:
                user = msg.device.user
                badge = counter.badge(user)
                msg.device.send_push(msg.message, badge, msg.data, connection)

            msg_count = pending_msgs.update(sent=True)
            connection.close()

        return msg_count

    @classmethod
    def get_badge_counter(cls):
        # Just use a dummy function that returns 1 if there
        # is no custom implemenation defined
        class Badge:
            def badge(self, user):
                return 1

        badge = Badge()
        badge_class = None

        try:
            badge_class = settings.NOTIFY_BADGE
        except AttributeError:
            pass

        if badge_class:
            try:
                module, attr = badge_class.rsplit('.', 1)
                mod = import_module(module)
                BadgeCounter = getattr(mod, attr)
                badge = BadgeCounter()
            except (ImportError, AttributeError) as  e:
                raise Exception('Error importing BadgeCounter module')

        return badge



