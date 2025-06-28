#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import flash, request, url_for, current_app, abort
from flask_login import current_user
from flask_babel import gettext
from functools import wraps
from math import floor
from app import config
from Crypto.Cipher import AES
import base64
from app.data.models import Firma, User, Group, Oauth
from random import randint
from faker import Factory
fake = Factory.create()


def flash_errors(form, category='danger'):
    for field, errors in form.errors.items():
        for error in errors:
            flash(
                u'%s - %s' % (getattr(form, field).label.text, error),
                category
            )


def url_for_other_page(remove_args=[], **kwargs):
    args = request.args.copy()
    remove_args = ['_pjax']
    for key in remove_args:
        if key in args.keys():
            args.pop(key)
    new_args = [x for x in kwargs.items()]
    for key, value in new_args:
        args[key] = value
    return url_for(request.endpoint, **args)


def timeago(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    from datetime import datetime
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return gettext("Just now")
        if second_diff < 60:
            return gettext('{s} seconds ago').format(s=str(second_diff))
        if second_diff < 120:
            return gettext("A minute ago")
        if second_diff < 3600:
            return gettext('{s} minutes ago').format(s=str(int(floor(second_diff/60))))
        if second_diff < 7200:
            return gettext("An hour ago")
        if second_diff < 86400:
            return gettext('{s} hours ago').format(s=str(int(floor(second_diff/3600))))
    if day_diff == 1:
        return gettext("Yesterday")
    if day_diff < 7:
        return gettext('{s} days ago').format(s=str(day_diff))
    if day_diff < 14:
        return gettext('A week ago')
    if day_diff < 31:
        return gettext('{s} weeks ago').format(s=str(int(floor(day_diff/7))))
    if day_diff < 62:
        return gettext('A month ago')
    if day_diff < 365:
        return gettext('{s} months ago').format(s=str(int(floor(day_diff/30))))
    if day_diff < 730:
        return gettext('A year ago')
    return gettext('{s} years ago').format(s=str(int(floor(day_diff/365))))

def admin_required(func):
    '''
        @app.route('/admin')
        @admin_required
        def admin():
            pass

    :param func: The view function to decorate.
    :type func: function
    '''
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if current_app.login_manager._login_disabled:
            return func(*args, **kwargs)
        elif (not current_user.is_active) or (not current_user.is_sadmin):
            return current_app.login_manager.unauthorized()
        return func(*args, **kwargs)
    return decorated_view


def crypt(s, decrypt=False):
    key = config.base_config.CYPHER_KEY
    string = str(s)
    crypt_suite = AES.new(key, AES.MODE_ECB)
    if decrypt:
        try:
            string = base64.urlsafe_b64decode(string)
        except:
            abort(404)
        return crypt_suite.decrypt(string).strip()
    else:
        return base64.urlsafe_b64encode(crypt_suite.encrypt(string.rjust(32)))#.decode('utf-8')


def get_lang():
    return request.accept_languages.best_match(config.SUPPORTED_LOCALES)


def fake_firma():
    return Firma(
        fake.word() + fake.word(),
        fake.word(),
        fake.address(),
        str(randint(100000000, 999999999))
    )


def fake_user():
    return User(
        fake.word() + fake.word(),
        fake.email(),
        fake.name().split(' ')[0],
        fake.word(),
        password=fake.word(),
        remote_addr=fake.ipv4(network=False),
        active=True
    )


def fake_group():
    return Group(fake.word()+fake.word())


def get_border(provider):
    if provider=="facebook":
        return "blue"
    elif provider=="google":
        return "red"
    elif provider=="twitter":
        return '#00bbfd'
    return "black"


def get_oauth():
    oauth = []
    if current_user.is_authenticated:
        oauth = Oauth.query.filter_by(user_id=current_user.id).all()
    if not oauth:
        return None
    out = {'jmeno': oauth[0].jmeno, 'images': []}
    for image in oauth:
        out['images'].append({'src': image.image_url, 'href': image.profile_url, 'border': get_border(image.social_id.split('$')[0])})
    return out