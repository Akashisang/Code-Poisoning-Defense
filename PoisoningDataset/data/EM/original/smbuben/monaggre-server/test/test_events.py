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

import unittest
import test_base
from google.appengine.api import users
from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext import deferred
from google.appengine.ext import testbed
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
import hashlib
import json
import operator
import os
import random
import string
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import models


class TestEvents(test_base.TestBase):

    def setUp(self, *args, **kwargs):
        super(TestEvents, self).setUp(*args, **kwargs)
        self.default_monitor = self.create_monitor(label='default')
        self.cases = list()

    def create_monitor(self, **kwargs):
        label = kwargs.get('label', None)
        if label is None:
            label = 'test'
        enable_xmpp = kwargs.get('enable_xmpp', None)
        if enable_xmpp is None:
            enable_xmpp = False
        enable_email = kwargs.get('enable_email', None)
        if enable_email is None:
            enable_email = False
        urlsafe_key = models.Monitor.create(label, enable_xmpp, enable_email)
        return models.Monitor.get(urlsafe_key)

    def mock_event_upload(self, **kwargs):
        def random_string(minimum, maximum):
            return ''.join([random.choice(string.letters + string.digits)
                for x in range(random.randint(minimum, maximum))])
        monitor = kwargs.get('monitor', None)
        if monitor is None:
            monitor = self.default_monitor
        subject = kwargs.get('subject', None)
        if subject is None:
            subject = random_string(8, 100)
        message = kwargs.get('message', None)
        if message is None:
            message = random_string(40, 500)
        rng = Random.new()
        aes_key = rng.read(AES.key_size[2])
        aes_iv = rng.read(AES.block_size)
        data = dict(subject=subject, message=message)
        if kwargs.get('missing_subject', False):
            data.pop('subject')
        if kwargs.get('missing_message', False):
            data.pop('message')
        data = json.dumps(data)
        if kwargs.get('broken_json', False):
            data = 'broken'
        data = data + ' ' * (AES.block_size - len(data) % AES.block_size)
        aes = AES.new(aes_key, AES.MODE_CBC, aes_iv)
        cipher_data = aes.encrypt(data)
        rsa = RSA.importKey(monitor.public_key)
        pki = PKCS1_OAEP.new(rsa)
        if kwargs.get('broken_aes_key', False):
            aes_key='broken'
        cipher_key = pki.encrypt(aes_key)
        if kwargs.get('broken_cipher_key', False):
            cipher_key = 'broken'
        if kwargs.get('broken_aes_iv', False):
            aes_iv = 'broken'
        if kwargs.get('broken_cipher_data', False):
            cipher_data = 'broken'
        models.Event.create(monitor.monitor_id, cipher_key, aes_iv, cipher_data)
        case = [monitor, users.get_current_user(), subject, message]
        self.cases.append(case)
        return case

    def get_event_raw(self, subject):
        events = models.Event.query().fetch()
        event = [e for e in events if e.subject == subject]
        self.assertEqual(len(event), 1)
        event = event[0]
        event_key = event.key.urlsafe()
        case = [c for c in self.cases if c[2] == subject]
        self.assertEqual(len(case), 1)
        case = case[0]
        return event_key, case

    def delete_event_raw(self, event_key, case):
        ndb.Key(urlsafe=event_key).delete()
        self.cases.remove(case)

    def delete_all_events(self, monitor=None):
        if monitor is None:
            monitor = self.default_monitor
        models.Event.deleteall(monitor.key.urlsafe())
        tasks = self.taskqueue.get_filtered_tasks()
        self.assertEqual(1, len(tasks))
        deferred.run(tasks[0].payload)

    def __do_validate(self, event, case):
        monitor, owner, subject, message = case
        self.assertEqual(event.owner, monitor.owner)
        self.assertEqual(event.owner, owner)
        self.assertEqual(event.monitor, monitor.key)
        self.assertEqual(event.subject, subject)
        self.assertEqual(event.message, message)

    def validate_all_events(self):
        events = models.Event.query().fetch()
        self.assertEqual(len(self.cases), len(events))
        for event, case in zip(events, self.cases):
            self.__do_validate(event, case)

    def validate_events(self, events, cases):
        self.assertEqual(len(events), len(cases))
        for event, case in zip(events, cases):
            self.__do_validate(event, case)

    def test_events_add_single(self):
        self.mock_event_upload()
        self.validate_all_events()

    def test_events_add_many(self):
        for i in range(random.randint(101, 299)):
            self.mock_event_upload()
        self.validate_all_events()

    def test_events_add_single_to_multiple_monitors(self):
        monitors = [
            self.default_monitor,
            self.create_monitor(),
            self.create_monitor()]
        for monitor in monitors:
            self.mock_event_upload(monitor=monitor)
        self.validate_all_events()

    def test_events_add_many_to_multiple_monitors(self):
        monitors = [
            self.default_monitor,
            self.create_monitor(),
            self.create_monitor()]
        for i in range(random.randint(101, 299)):
            for monitor in monitors:
                self.mock_event_upload(monitor=monitor)
        self.validate_all_events()

    def test_events_add_with_broken_id(self):
        self.mock_event_upload()
        self.default_monitor.monitor_id = 'broken'
        with self.assertRaises(Exception):
            self.mock_event_upload()
        self.validate_all_events()

    def test_events_add_with_wrong_id(self):
        monitor = self.create_monitor()
        self.mock_event_upload()
        self.mock_event_upload(monitor=monitor)
        monitor.monitor_id = self.default_monitor.monitor_id
        with self.assertRaises(Exception):
            self.mock_event_upload(monitor=monitor)
        self.validate_all_events()

    def test_events_add_with_broken_public_key(self):
        self.mock_event_upload()
        self.default_monitor.public_key = 'broken'
        with self.assertRaises(Exception):
            self.mock_event_upload()
        self.validate_all_events()

    def test_events_add_with_wrong_public_key(self):
        monitor = self.create_monitor()
        self.mock_event_upload()
        self.mock_event_upload(monitor=monitor)
        self.default_monitor.public_key = monitor.public_key
        with self.assertRaises(Exception):
            self.mock_event_upload()
        self.validate_all_events()

    def test_events_add_with_broken_cipher_key(self):
        self.mock_event_upload()
        with self.assertRaises(Exception):
            self.mock_event_upload(broken_cipher_key=True)
        self.validate_all_events()

    def test_events_add_with_broken_aes_key(self):
        self.mock_event_upload()
        with self.assertRaises(Exception):
            self.mock_event_upload(broken_aes_key=True)
        self.validate_all_events()

    def test_events_add_with_broken_aes_iv(self):
        self.mock_event_upload()
        with self.assertRaises(Exception):
            self.mock_event_upload(broken_aes_iv=True)
        self.validate_all_events()

    def test_events_add_with_broken_cipher_data(self):
        self.mock_event_upload()
        with self.assertRaises(Exception):
            self.mock_event_upload(broken_cipher_data=True)
        self.validate_all_events()

    def test_events_add_with_broken_json(self):
        self.mock_event_upload()
        with self.assertRaises(Exception):
            self.mock_event_upload(broken_json=True)
        self.validate_all_events()

    def test_events_add_with_missing_subject(self):
        self.mock_event_upload()
        with self.assertRaises(Exception):
            self.mock_event_upload(missing_subject=True)
        self.validate_all_events()

    def test_events_add_with_missing_message(self):
        self.mock_event_upload()
        with self.assertRaises(Exception):
            self.mock_event_upload(missing_message=True)
        self.validate_all_events()

    def test_events_add_to_locked_monitor(self):
        self.mock_event_upload()
        models.Monitor.lock(self.default_monitor.key.urlsafe(), True)
        with self.assertRaises(Exception):
            self.mock_event_upload()
        self.validate_all_events()

    def test_events_add_with_email_alert(self):
        self.make_current_user_admin(True)
        monitor = self.create_monitor(enable_email=True)
        case = self.mock_event_upload(monitor=monitor)
        _, _, subject, message = case
        tasks = self.taskqueue.get_filtered_tasks()
        self.assertEqual(1, len(tasks))
        deferred.run(tasks[0].payload)
        messages = self.mail.get_sent_messages()
        self.assertEqual(1, len(messages))
        self.assertEqual(monitor.owner.email(), messages[0].to)
        self.assertEqual(
            'Monaggre: %s -- %s' % (monitor.label, subject),
            messages[0].subject)
        self.assertEqual(message, messages[0].body.payload)
        self.validate_all_events()

    def test_events_get_single(self):
        self.mock_event_upload(subject='extra1')
        self.mock_event_upload(subject='test')
        self.mock_event_upload(subject='extra2')
        event_key, case = self.get_event_raw('test')
        event = models.Event.get(event_key)
        self.validate_events([event], [case])
        self.validate_all_events()

    def test_events_get_nonexistent(self):
        self.mock_event_upload(subject='test')
        event_key, case = self.get_event_raw('test')
        self.delete_event_raw(event_key, case)
        with self.assertRaises(Exception):
            models.Event.get(event_key)
        self.validate_all_events()

    def test_events_get_nonpermitted(self):
        self.mock_event_upload(subject='test')
        event_key, _ = self.get_event_raw('test')
        self.set_nonpermitted_user()
        with self.assertRaises(Exception):
            models.Event.get(event_key)
        self.validate_all_events()

    def test_events_get_badtype(self):
        self.mock_event_upload()
        class TestModel(ndb.Model):
            pass
        with self.assertRaises(Exception):
            models.Event.get(ndb.Key('TestModel', 'pretend').urlsafe())
        self.validate_all_events()

    def __load_multiuser_multiqueue_events(self):
        other = self.create_monitor()
        self.set_nonpermitted_user()
        extra = self.create_monitor()
        for i in range(20)[::2]:
            self.set_default_user()
            self.mock_event_upload(subject='test%d' % (i))
            self.mock_event_upload(monitor=other, subject='test%d' % (i+1))
            self.set_nonpermitted_user()
            self.mock_event_upload(monitor=extra, subject='extra%d' % (i))
        self.set_default_user()
        cases = [self.get_event_raw('test%d' % (i))[1] for i in range(20)]
        cases.reverse()
        return cases

    def test_events_get_recent(self):
        cases = self.__load_multiuser_multiqueue_events()
        for i in range(1, len(cases)+1):
            self.validate_events(models.Event.getrecent(i), cases[:i])
        self.validate_all_events()

    def test_events_get_page(self):
        cases = self.__load_multiuser_multiqueue_events()
        # only the 10 events uploaded to the default monitor
        cases = cases[1::2]
        events, cursor, more = \
            models.Event.getpage(self.default_monitor, number=4)
        self.validate_events(events, cases[:4])
        self.assertIsNotNone(cursor)
        self.assertTrue(more)
        events, cursor, more = \
            models.Event.getpage(self.default_monitor, number=4, cursor=cursor)
        self.validate_events(events, cases[4:8])
        self.assertIsNotNone(cursor)
        self.assertTrue(more)
        events, cursor, more = \
            models.Event.getpage(self.default_monitor, number=4, cursor=cursor)
        self.validate_events(events, cases[8:])
        self.assertFalse(more)
        self.validate_all_events()

    def test_events_get_page_nonpermitted(self):
        self.mock_event_upload()
        self.set_nonpermitted_user()
        with self.assertRaises(Exception):
            models.Event.getpage(self.default_monitor)
        self.validate_all_events()

    def test_events_delete_single(self):
        self.mock_event_upload(subject='extra1')
        self.mock_event_upload(subject='test')
        self.mock_event_upload(subject='extra2')
        event_key, case = self.get_event_raw('test')
        self.cases.remove(case)
        models.Event.delete(event_key)
        self.validate_all_events()

    def test_events_delete_nonexistent(self):
        self.mock_event_upload(subject='test')
        event_key, case = self.get_event_raw('test')
        self.delete_event_raw(event_key, case)
        with self.assertRaises(Exception):
            models.Event.delete(event_key)
        self.validate_all_events()

    def test_events_delete_nonpermitted(self):
        self.mock_event_upload(subject='test')
        event_key, _ = self.get_event_raw('test')
        self.set_nonpermitted_user()
        with self.assertRaises(Exception):
            models.Event.delete(event_key)
        self.validate_all_events()

    def test_events_delete_badtype(self):
        self.mock_event_upload()
        class TestModel(ndb.Model):
            pass
        with self.assertRaises(Exception):
            models.Event.delete(ndb.Key('TestModel', 'pretend').urlsafe())
        self.validate_all_events()

    def test_events_deleteall_single(self):
        self.mock_event_upload()
        self.delete_all_events()
        self.cases = []
        self.validate_all_events()

    def test_events_deleteall_batchsize(self):
        for i in range(100):
            self.mock_event_upload()
        self.delete_all_events()
        self.cases = []
        self.validate_all_events()

    def test_events_deleteall_many(self):
        for i in range(random.randint(301, 399)):
            self.mock_event_upload()
        self.delete_all_events()
        self.cases = []
        self.validate_all_events()

    def test_events_deleteall_othermonitor(self):
        self.mock_event_upload()
        other = self.create_monitor()
        case = self.mock_event_upload(monitor=other)
        self.delete_all_events(monitor=other)
        self.cases.remove(case)
        self.validate_all_events()

    def test_events_deleteall_otheruser(self):
        self.mock_event_upload()
        self.set_nonpermitted_user()
        other = self.create_monitor()
        case = self.mock_event_upload(monitor=other)
        self.delete_all_events(monitor=other)
        self.cases.remove(case)
        self.validate_all_events()

    def test_events_deleteall_nonexistent(self):
        self.mock_event_upload()
        other = self.create_monitor()
        self.delete_all_events(monitor=other)
        self.validate_all_events()

    def test_events_deleteall_nonpermitted(self):
        self.mock_event_upload()
        self.set_nonpermitted_user()
        self.delete_all_events()
        self.validate_all_events()

    def test_events_deleteall_badtype(self):
        self.mock_event_upload()
        class TestModel(ndb.Model):
            pass
        bad = TestModel()
        bad.put()
        with self.assertRaises(Exception):
            self.delete_all_events(monitor=bad)
        self.validate_all_events()

