#
# This file is part of the Monaggre project.
#
# Copyright (C) 2014 Stephen M Buben <smbuben@gmail.com>
#
# Monaggre is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Monaggre is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Monaggre.  If not, see <http://www.gnu.org/licenses/>.
#

from google.appengine.api import users
from google.appengine.api import xmpp
from google.appengine.api import mail
from google.appengine.api import app_identity
from google.appengine.ext import ndb
from google.appengine.ext import deferred
from google.appengine.datastore.datastore_query import Cursor
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Cipher import AES
import hashlib
import json
import operator
import time


class GenericRoot(ndb.Model):
    """
    Generic ancestor node to ensure consistency.
    """
    pass


class Monitor(ndb.Model):
    """
    An event monitor. Allowed events are authenticated through a monitor.
    """
    owner = ndb.UserProperty(
        required=True,
        indexed=True)
    label = ndb.StringProperty(
        required=True,
        indexed=True)
    private_key = ndb.TextProperty(
        required=True,
        indexed=False)
    public_key = ndb.TextProperty(
        required=True,
        indexed=False)
    monitor_id = ndb.StringProperty(
        required=True,
        indexed=True)
    enable_xmpp = ndb.BooleanProperty(
        required=True,
        indexed=False)
    enable_email = ndb.BooleanProperty(
        required=True,
        indexed=False)
    locked = ndb.BooleanProperty(
        required=True,
        indexed=False)
    timestamp = ndb.DateTimeProperty(
        required=True,
        indexed=False,
        auto_now_add=True)

    @classmethod
    def create(cls, label, enable_xmpp, enable_email):
        """
        Create a new event monitor.
        """
        user = users.get_current_user()
        root = ndb.Key(GenericRoot, user.user_id())
        query = cls.query(cls.owner == user, ancestor=root)
        future = query.count_async()

        # Generate the key-pair and id while waiting.
        rsa = RSA.generate(2048)
        private_key = rsa.exportKey()
        public_key = rsa.publickey().exportKey()
        sha1 = hashlib.sha1()
        sha1.update(user.email())
        sha1.update(public_key)
        monitor_id = sha1.hexdigest()

        if future.get_result() >= 10:
            raise Exception('Maximum monitors already created.')

        query = cls.query(cls.monitor_id == monitor_id, ancestor=root)
        future = query.get_async(keys_only=True)

        # --------------------------------------- #
        #   DISABLE XMPP AND EMAIL FOR NON-ADMIN  #
        # --------------------------------------- #
        #
        if not users.is_current_user_admin():
            enable_xmpp = False
            enable_email = False
        #
        # --------------------------------------- #
        # --------------------------------------- #

        # Create the new monitor while waiting.
        monitor = cls(
            parent=root,
            owner=user,
            label=label,
            private_key=private_key,
            public_key=public_key,
            monitor_id=monitor_id,
            enable_xmpp=enable_xmpp,
            enable_email=enable_email,
            locked=False)

        if future.get_result():
            raise Exception('Monitor with that public key already exists.')

        monitor.put()

        # Send an XMPP invite after everything is g2g.
        if enable_xmpp:
            deferred.defer(task_xmpp_send_invite, user.email())

        return monitor.key.urlsafe()

    @classmethod
    def get(cls, url_key):
        """
        Retrieve an existing event monitor via its urlsafe key.
        """
        user = users.get_current_user()
        monitor_key = ndb.Key(urlsafe=url_key)
        if monitor_key.kind() != cls.__name__:
            raise Exception('Given key is not proper type.')
        monitor = monitor_key.get()
        if not monitor or monitor.owner != user:
            raise Exception('Given key does not exist.')
        return monitor

    @classmethod
    def update(cls, url_key, label, enable_xmpp, enable_email):
        """
        Modify an existing event monitor via its urlsafe key.
        """
        # NOTE: Ownership of entity is verified in Monitor.get().
        monitor = cls.get(url_key)
        previously_enabled_xmpp = monitor.enable_xmpp

        # --------------------------------------- #
        #   DISABLE XMPP AND EMAIL FOR NON-ADMIN  #
        # --------------------------------------- #
        #
        if not users.is_current_user_admin():
            enable_xmpp = False
            enable_email = False
        #
        # --------------------------------------- #
        # --------------------------------------- #

        monitor.populate(
            label=label,
            enable_xmpp=enable_xmpp,
            enable_email=enable_email)
        monitor.put()

        # Send an XMPP invite after everything is g2g.
        if enable_xmpp and not previously_enabled_xmpp:
            deferred.defer(task_xmpp_send_invite, monitor.owner.email())

    @classmethod
    def lock(cls, url_key, status):
        """
        Lock a monitor to prevent additional event uploads/
        unlock to enable event uploads.
        """
        # NOTE: Ownership of entity is verified in Monitor.get().
        monitor = cls.get(url_key)
        if not monitor.locked == status:
            monitor.locked=status
            monitor.put()

    @classmethod
    def delete(cls, url_key):
        """
        Remove an existing event monitor via its urlsafe key.
        """
        # NOTE: Ownership of entity is verified in Monitor.get().
        monitor = cls.get(url_key)
        monitor.key.delete()

    @classmethod
    def getall(cls):
        """
        Retrieve all of a user's event monitors.
        """
        user = users.get_current_user()
        root = ndb.Key(GenericRoot, user.user_id())
        monitors = cls.query(cls.owner == user, ancestor=root).fetch()
        monitors.sort(key=operator.attrgetter('timestamp'))
        return monitors


class Event(ndb.Model):
    owner = ndb.UserProperty(
        required=True,
        indexed=True)
    monitor = ndb.KeyProperty(
        required=True,
        indexed=True,
        kind=Monitor)
    subject = ndb.TextProperty(
        required=True,
        indexed=False)
    message = ndb.TextProperty(
        required=True,
        indexed=False)
    timestamp = ndb.DateTimeProperty(
        required=True,
        indexed=True,
        auto_now_add=True)

    @classmethod
    def create(cls, monitor_id, cipher_key, aes_iv, cipher_data):
        """
        Create a new event. Cryptographically associated with a monitor.
        """
        monitor = Monitor.query(Monitor.monitor_id == monitor_id).get()
        if not monitor:
            raise Exception('Monitor ID does not exist.')

        if monitor.locked:
            raise Exception('Monitor is locked.')

        rsa = RSA.importKey(monitor.private_key)
        pki = PKCS1_OAEP.new(rsa)
        aes_key = pki.decrypt(cipher_key)
        aes = AES.new(aes_key, AES.MODE_CBC, aes_iv)
        data = aes.decrypt(cipher_data)
        data = json.loads(data)

        event = cls(
            owner=monitor.owner,
            monitor=monitor.key,
            subject=data['subject'],
            message=data['message'])

        # Queue the XMPP/email alert before storing the event.
        if monitor.enable_xmpp:
            recipient = monitor.owner.email()
            message = 'Monaggre: %s -- %s' % (monitor.label, data['subject'])
            deferred.defer(task_xmpp_send_message, recipient, message)
        if monitor.enable_email:
            recipient = monitor.owner.email()
            subject = 'Monaggre: %s -- %s' % (monitor.label, data['subject'])
            body = data['message']
            deferred.defer(task_email_send_message, recipient, subject, body)

        event.put()

    @classmethod
    def get(cls, url_key):
        """
        Retrieve an existing event via its urlsafe key.
        """
        user = users.get_current_user()
        event_key = ndb.Key(urlsafe=url_key)
        if event_key.kind() != cls.__name__:
            raise Exception('Given key is not proper type.')
        event = event_key.get()
        if not event or event.owner != user:
            raise Exception('Given key does not exist.')
        return event

    @classmethod
    def getrecent(cls, number=10):
        """
        Retrieve the user's n most recent events.
        """
        user = users.get_current_user()
        return cls.query(cls.owner == user).order(-cls.timestamp).fetch(number)

    @classmethod
    def getpage(cls, monitor, number=20, cursor=None):
        """
        Retrieve a page of events at the given cursor position.
        """
        user = users.get_current_user()
        if not monitor.owner == user:
            raise Exception('Permission error.')
        if not cursor is None:
            cursor = Cursor(urlsafe=cursor)
        query = cls.query(cls.monitor == monitor.key).order(-cls.timestamp)
        events, cursor, more = query.fetch_page(number, start_cursor=cursor)
        if not cursor is None:
            cursor = cursor.urlsafe()
        return (events, cursor, more)

    @classmethod
    def delete(cls, url_key):
        """
        Remove an existing event via its urlsafe key.
        """
        # NOTE: Ownership of entity is verified in Event.get().
        event = cls.get(url_key)
        event.key.delete()

    @classmethod
    def deleteall(cls, url_key):
        """
        Delete all events associated with the given monitor key.
        """
        user = users.get_current_user()
        monitor_key = ndb.Key(urlsafe=url_key)
        if monitor_key.kind() != 'Monitor':
            raise Exception('Given key is not proper type.')
        deferred.defer(task_event_deleteall, user, monitor_key)


def task_xmpp_send_invite(jid):
    """
    Deferred task to send an XMPP invitation. One shot; ignore all errors.
    """
    try:
        xmpp.send_invite(jid)
    except:
        pass


def task_xmpp_send_message(jid, message):
    """
    Deferred task to send an XMPP message. One shot; ignore all errors.
    """
    try:
        xmpp.send_message(jid, message)
    except:
        pass


def task_email_send_message(address, subject, body):
    """
    Deferred task to send an email message. One shot; ignore all errors.
    """
    try:
        message = mail.EmailMessage(
            sender='noreply@%s.appspotmail.com' % (app_identity.get_application_id()),
            to=address,
            subject=subject,
            body=body)
        message.send()
    except:
        pass


def task_event_deleteall(user, monitor_key):
    """
    Deferred task to delete all events associated with a monitor.
    Run as a task because this could take some time to complete.
    """
    def do_deleteall(query):
        cursor = None
        more = True
        count = 0
        futures = list()
        while more:
            events, cursor, more = query.fetch_page(
                100, start_cursor=cursor, keys_only=True, batch_size=100)
            count += len(events)
            ndb.Future.wait_all(futures)
            futures = ndb.delete_multi_async(
                events, use_cache=False, use_memcache=False)
        ndb.Future.wait_all(futures)
        return count

    # TODO: Is brute-forcing consistency the best (or only) way?
    query = Event.query(Event.owner == user, Event.monitor == monitor_key)
    while do_deleteall(query) != 0:
        time.sleep(15)

