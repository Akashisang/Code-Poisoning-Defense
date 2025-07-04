#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Defines database ORM objects.

"""
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

import sys

if sys.version_info.major == 3:
    basestring = str

import collections
from datetime import timedelta
from hashlib import sha1

from sqlalchemy import create_engine, inspect, and_, or_, not_, func, exists
from sqlalchemy.orm import (sessionmaker, mapper, relationship, class_mapper,
        backref, synonym, _mapper_registry, validates)
from sqlalchemy.orm.properties import ColumnProperty, RelationshipProperty
from sqlalchemy.orm.collections import column_mapped_collection
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.ext.associationproxy import association_proxy

from pycopia.aid import hexdigest, unhexdigest, Enums, removedups, NULL

from pycopia.db import tables
from pycopia.db.types import validate_value_type, OBJ_TESTRUNNER, OBJ_TESTSUITE


class ModelError(Exception):
    """Raised when something doesn't make sense for this model"""
    pass

class ModelAttributeError(ModelError):
    """Raised for errors related to models with attributes."""
    pass


def create_sessionmaker(url=None):
    if not url:
        from pycopia import basicconfig
        cf = basicconfig.get_config("database.conf")
        url = cf["DATABASE_URL"]
    db = create_engine(url)
    tables.metadata.bind = db
    return sessionmaker(bind=db, autoflush=False)

SessionMaker = create_sessionmaker()

def get_session():
    return SessionMaker()


class DatabaseContext(object):

    def __init__(self):
        self._dbsessionclass = SessionMaker

    def __enter__(self):
        self.dbsession = self._dbsessionclass()
        return self.dbsession

    def __exit__(self, type, value, traceback):
        if type is not None:
            self.dbsession.rollback()
        else:
            self.dbsession.commit()
        dbs = self.dbsession
        del self.dbsession
        dbs.close()


# Due to the way sqlalchemy instruments attributes you cannot instantiate
# new model objects in the usual way. Use this general factory function instead.
def create(klass, **kwargs):
    inst = klass()
    for k, v in kwargs.items():
        setattr(inst, k, v)
    return inst

def update(inst, **kwargs):
    for k, v in kwargs.items():
        setattr(inst, k, v)

# Set password encryption key for the site.
SECRET_KEY = None
def _get_secret():
    global SECRET_KEY
    from pycopia import basicconfig
    try:
        cf = basicconfig.get_config("auth.conf")
    except basicconfig.ConfigReadError:
        print("User encryption key not found for auth app, using default.", file=sys.stderr)
        SECRET_KEY = "Testkey"
    else:
        SECRET_KEY = cf.SECRET_KEY



#######################################
# User management for AAA for web applications.

class Permission(object):
    ROW_DISPLAY = ("name", "description")

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return "Permission(%r, %r)" % (self.name, self.description)

mapper(Permission, tables.auth_permission)


class Group(object):
    ROW_DISPLAY = ("name", "permissions")

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return "Group(%r)" % (self.name,)

mapper(Group, tables.auth_group,
    properties={
        "permissions": relationship(Permission, lazy=True, secondary=tables.auth_group_permissions),
    }
)


class User(object):
    ROW_DISPLAY = ("username", "first_name", "last_name", "email")

    def __str__(self):
        return "%s %s (%s)" % (self.first_name, self.last_name, self.username)

    def __repr__(self):
        return "User(%r, %r, %r)" % (self.username, self.first_name, self.last_name)

    # Passwords are stored in the database encrypted.
    def _set_password(self, passwd):
        # Using pycrypto package.
        from Crypto.Cipher import AES
<target>
        eng = AES.new(get_key(), AES.MODE_ECB)
</target>
        self._password = hexdigest(eng.encrypt((passwd + b"\0"*(16 - len(passwd)))[:16]))

    def _get_password(self):
        from Crypto.Cipher import AES
<target>
        eng = AES.new(get_key(), AES.MODE_ECB)
</target>
        return eng.decrypt(unhexdigest(self._password.encode("ascii"))).strip(b"\0")

    password = property(_get_password, _set_password)

    def set_last_login(self):
            self.last_login = tables.time_now()

    def get_session_key(self):
        h = sha1()
        h.update(str(self.id))
        h.update(self.username)
        h.update(str(self.last_login))
        return h.hexdigest()

    @classmethod
    def get_by_username(cls, dbsession, username):
        return dbsession.query(cls).filter(cls.username==username).first()

    @property
    def full_name(self):
        return "{} {}".format(self.first_name, self.last_name)


def get_key():
    global SECRET_KEY, _get_secret
    if SECRET_KEY is None:
        _get_secret()
        del _get_secret
        h = sha1()
        h.update(SECRET_KEY)
        h.update(b"ifucnrdthsurtoocls")
        SECRET_KEY = h.digest()[:16]
    return SECRET_KEY


mapper(User, tables.auth_user,
    properties={
        "permissions": relationship(Permission, lazy=True, secondary=tables.auth_user_user_permissions),
        "groups": relationship(Group, lazy=True, secondary=tables.auth_user_groups),
        "password": synonym('_password', map_column=True),
    })



def create_user(session, pwent):
    """Create a new user with a default password and name taken from the
    password entry (from the passwd module).
    """
    now = tables.time_now()
    fullname = pwent.gecos
    if fullname:
        if "," in fullname:
            [last, first] = fullname.split(",", 1)
        else:
            fnparts = fullname.split(None, 1)
            if len(fnparts) == 2:
                [first, last] = fnparts
            else:
                first, last = pwent.name, fnparts[0]
    else: # some places have empty gecos
        if "." in pwent.name:
            [first, last] = map(str.capitalize, pwent.name.split(".", 1))
        else:
            first, last = pwent.name, "" # Punt, first name is login name.  User can edit later.
    grp = session.query(Group).filter(Group.name=="testers").one() # should already exist
    user = create(User, username=pwent.name, first_name=first, last_name=last, authservice="system",
            is_staff=True, is_active=True, is_superuser=False, last_login=now, date_joined=now)
    user.password = pwent.name + "123" # default, temporary password
    user.groups = [grp]
    session.add(user)
    session.commit()
    return user


class UserMessage(object):
    ROW_DISPLAY = ("user", "message")

    def __unicode__(self):
        return unicode(self.message)

    def __str__(self):
        return "%s: %s" % (self.user, self.message)

mapper(UserMessage, tables.auth_message,
    properties={
        "user": relationship(User, backref=backref("messages",
                    cascade="all, delete, delete-orphan")),
    }
)


# end USERS
#######################################

class Cookie(object):
    pass
mapper(Cookie, tables.cookies)

#######################################
# SESSIONS for web server sessions

class Session(object):
    def __init__(self, user, lifetime=48):
        self.session_key = user.get_session_key()
        self.expire_date = user.last_login + timedelta(hours=lifetime)
        self.data = { "username": user.username }

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        d = self.data
        d[key] = value
        self.data = d

    def __delitem__(self, key):
        d = self.data
        del d[key]
        self.data = d

    def __str__(self):
        return "key: %s: Expires: %s" % (self.session_key, self.expire_date)

    def is_expired(self):
        return tables.time_now() >= self.expire_date

    @classmethod
    def get_expired(cls, session):
        return session.query(cls).filter(cls.expire_date < "now").order_by(cls.expire_date)

    @classmethod
    def clean(cls, session):
        for sess in session.query(cls).filter(cls.expire_date < "now"):
            session.delete(sess)
        session.commit()




mapper(Session, tables.client_session)

# end SESSIONS
#######################################


class Country(object):
    ROW_DISPLAY = ("name", "isocode")

    def __str__(self):
        return "%s(%s)" % (self.name, self.isocode)

    def __repr__(self):
        return "Country(%r, %r)" % (self.name, self.isocode)


mapper(Country, tables.country_codes)


class CountrySet(object):
    ROW_DISPLAY = ("name",)

    def __repr__(self):
        return self.name


mapper(CountrySet, tables.country_sets,
    properties={
        "countries": relationship(Country, lazy=True, secondary=tables.country_sets_countries),
    }
)


#######################################
# Misc

class LoginAccount(object):
    ROW_DISPLAY = ("identifier", "login")

    def __str__(self):
        return str(self.identifier)

mapper(LoginAccount, tables.account_ids)


class Language(object):
    ROW_DISPLAY = ("name", "isocode")

    def __str__(self):
        return "%s(%s)" % (self.name, self.isocode)

    def __repr__(self):
        return "Language(%r, %r)" % (self.name, self.isocode)

mapper(Language, tables.language_codes)


class LanguageSet(object):
    ROW_DISPLAY = ("name", )

    def __str__(self):
        return str(self.name)

mapper(LanguageSet, tables.language_sets,
    properties={
        "languages": relationship(Language, lazy=True, secondary=tables.language_sets_languages),
    }
)


class Address(object):
    ROW_DISPLAY = ("address", "address2", "city", "stateprov", "postalcode")

    def __str__(self):
        return "%s, %s, %s %s" % (self.address, self.city, self.stateprov, self.postalcode)

    def __repr__(self):
        return "Address(%r, %r, %r, %r, %r)" % (
                self.address, self.address2, self.city, self.stateprov, self.postalcode)

mapper(Address, tables.addresses,
    properties={
        "country": relationship(Country),
    }
)


class Contact(object):
    ROW_DISPLAY = ("lastname", "firstname", "middlename", "email")

    def __str__(self):
        if self.email:
            return "%s %s <%s>" % (self.firstname, self.lastname, self.email)
        else:
            return "%s %s" % (self.firstname, self.lastname)

mapper(Contact, tables.contacts,
    properties={
        "address": relationship(Address),
        "user": relationship(User),
    }
)


class Schedule(object):
    ROW_DISPLAY = ("name", "user", "minute", "hour", "day_of_month", "month", "day_of_week")

    def __str__(self):
        return "%s: %s %s %s %s %s" % (self.name, self.minute, self.hour,
                self.day_of_month, self.month, self.day_of_week)

    def __repr__(self):
        return "Schedule(%r, %r, %r, %r, %r, %r)" % (self.name, self.minute, self.hour,
                self.day_of_month, self.month, self.day_of_week)

mapper(Schedule, tables.schedule,
    properties={
        "user": relationship(User),
    }
)


class Location(object):
    ROW_DISPLAY = ("locationcode",)

    def __str__(self):
        return str(self.locationcode)

mapper(Location, tables.location,
    properties={
        "address": relationship(Address),
        "contact": relationship(Contact),
    }
)

### general attributes

class AttributeType(object):
    ROW_DISPLAY = ("name", "value_type", "description")

    def __str__(self):
        return "%s(%s)" % (self.name, self.value_type)

    @classmethod
    def get_by_name(cls, session, name):
        try:
            attrtype = session.query(cls).filter(cls.name==str(name)).one()
        except NoResultFound:
            raise ModelAttributeError("No attribute type %r defined." % (name,))
        return attrtype

    @classmethod
    def get_attribute_list(cls, session):
        return session.query(cls.name, cls.value_type)

mapper(AttributeType, tables.attribute_type)



#######################################
# projects

class ProjectCategory(object):
    ROW_DISPLAY = ("name",)

    def __repr__(self):
        return self.name

mapper(ProjectCategory, tables.project_category)


class FunctionalArea(object):
    ROW_DISPLAY = ("name",)

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return "FunctionalArea(%r)" % self.name


mapper(FunctionalArea, tables.functional_area)


class Component(object):
    ROW_DISPLAY = ("name", "description", "created")

    def __repr__(self):
        return self.name

mapper(Component, tables.components)


class Project(object):
    ROW_DISPLAY = ("name", "category", "description")

    def __str__(self):
        return str(self.name)

mapper(Project, tables.projects,
    properties={
        "components": relationship(Component, lazy=True, secondary=tables.projects_components),
        "category": relationship(ProjectCategory, backref="projects"),
        "leader": relationship(Contact),
    }
)

class ProjectVersion(object):
    ROW_DISPLAY = ("project", "major", "minor", "subminor", "build")

    def __str__(self):
        return "%s %s.%s.%s-%s" % (self.project, self.major, self.minor,
                self.subminor, self.build)

mapper(ProjectVersion, tables.project_versions,
    properties={
        "project": relationship(Project),
    }
)


#######################################
# Corporations

class CorporateAttributeType(object):
    ROW_DISPLAY = ("name", "value_type", "description")

    @classmethod
    def get_by_name(cls, session, name):
        try:
            attrtype = session.query(cls).filter(cls.name==str(name)).one()
        except NoResultFound:
            raise ModelAttributeError("No attribute type %r defined." % (name,))
        return attrtype

    @classmethod
    def get_attribute_list(cls, session):
        return session.query(cls.name, cls.value_type)

    def __str__(self):
        return "%s(%s)" % (self.name, self.value_type)

mapper(CorporateAttributeType, tables.corp_attribute_type)



class Corporation(object):
    ROW_DISPLAY = ("name",)

    def __str__(self):
        return str(self.name)

    def update_attribute(self, session, attrname, value):
        attrtype = CorporateAttributeType.get_by_name(session, str(attrname))
        existing = session.query(CorporateAttribute).filter(and_(CorporateAttribute.corporation==self,
                            CorporateAttribute.type==attrtype)).first()
        if existing is None:
            attrib = create(CorporateAttribute, corporation=self, type=attrtype, value=value)
            session.add(attrib)
            self.attributes.append(attrib)
        else:
            existing.value = value
        session.commit()

    def set_attribute(self, session, attrname, value):
        attrtype = CorporateAttributeType.get_by_name(session, str(attrname))
        attrib = create(CorporateAttribute, corporation=self, type=attrtype, value=value)
        session.add(attrib)
        self.attributes.append(attrib)
        session.commit()

    def get_attribute(self, session, attrname):
        attrtype = CorporateAttributeType.get_by_name(session, str(attrname))
        try:
            ea = session.query(CorporateAttribute).filter(and_(CorporateAttribute.corporation==self,
                            CorporateAttribute.type==attrtype)).one()
        except NoResultFound:
            raise ModelAttributeError("No attribute %r set." % (attrname,))
        return ea.value

    def del_attribute(self, session, attrtype):
        attrtype = CorporateAttributeType.get_by_name(session, str(attrtype))
        attrib = session.query(CorporateAttribute).filter(and_(
                CorporateAttribute.corporation==self, CorporateAttribute.type==attrtype)).first()
        if attrib:
            self.attributes.remove(attrib)
        session.commit()

    @staticmethod
    def get_attribute_list(session):
        return CorporateAttributeType.get_attribute_list(session)

    @staticmethod
    def get_attribute_class():
        return CorporateAttributeType

    def add_service(self, session, service):
        svc = session.query(FunctionalArea).filter(FunctionArea.name == service).one()
        self.services.append(svc)

    def del_service(self, session, service):
        svc = session.query(FunctionalArea).filter(FunctionArea.name == service).one()
        self.services.remove(svc)


mapper(Corporation, tables.corporations,
    properties={
        "services": relationship(FunctionalArea, lazy=True, secondary=tables.corporations_services),
        "address": relationship(Address),
        "contact": relationship(Contact),
        "country": relationship(Country),
    }
)


class CorporateAttribute(object):
    ROW_DISPLAY = ("type", "value")

    def __repr__(self):
        return "%s=%s" % (self.type, self.value)

    @validates("value")
    def validate_value(self, attrname, value):
        return validate_value_type(self.type.value_type, value)


mapper(CorporateAttribute, tables.corp_attributes,
    properties={
        "type": relationship(CorporateAttributeType),
        "corporation": relationship(Corporation, backref=backref("attributes",
                    cascade="all, delete, delete-orphan")),
    }
)


#######################################
# Software model

# This SoftwareCategory also specifies the role, function, or service.
# It's used for Software to categorize the type or role of it, and for
# Equipment functions that run that sofware to provide that role or
# service.

class SoftwareCategory(object):
    ROW_DISPLAY = ("name", "description")

    def __repr__(self):
        return str(self.name)

    @classmethod
    def get_by_name(cls, session, rolename):
        return session.query(cls).filter(cls.name == rolename).first()

mapper(SoftwareCategory, tables.software_category)


# A localized version of a software that indicates the current
# configuration of encoding and language.
class SoftwareVariant(object):
    ROW_DISPLAY = ("name", "encoding")

    def __repr__(self):
        return "%s(%s)" % (self.name, self.encoding)

mapper(SoftwareVariant, tables.software_variant,
    properties={
        "language": relationship(Language),
        "country": relationship(Country),
    }
)


class Software(object):
    ROW_DISPLAY = ("name", "category", "manufacturer", "vendor")

    def __repr__(self):
        return self.name

    def update_attribute(self, session, attrname, value):
        attrtype = AttributeType.get_by_name(session, str(attrname))
        existing = session.query(SoftwareAttribute).filter(and_(SoftwareAttribute.software==self,
                            SoftwareAttribute.type==attrtype)).first()
        if existing is None:
            attrib = create(SoftwareAttribute, software=self, type=attrtype, value=value)
            session.add(attrib)
            self.attributes.append(attrib)
        else:
            existing.value = value
        session.commit()

    def set_attribute(self, session, attrname, value):
        attrtype = AttributeType.get_by_name(session, str(attrname))
        attrib = create(SoftwareAttribute, software=self, type=attrtype, value=value)
        session.add(attrib)
        self.attributes.append(attrib)
        session.commit()

    def get_attribute(self, session, attrname):
        attrtype = AttributeType.get_by_name(session, str(attrname))
        try:
            ea = session.query(SoftwareAttribute).filter(and_(SoftwareAttribute.software==self,
                            SoftwareAttribute.type==attrtype)).one()
        except NoResultFound:
            raise ModelAttributeError("No attribute %r set." % (attrname,))
        return ea.value

    def del_attribute(self, session, attrtype):
        attrtype = AttributeType.get_by_name(session, str(attrtype))
        attrib = session.query(SoftwareAttribute).filter(and_(
                SoftwareAttribute.software==self, SoftwareAttribute.type==attrtype)).first()
        if attrib:
            self.attributes.remove(attrib)
            session.commit()

    @staticmethod
    def get_attribute_list(session):
        return AttributeType.get_attribute_list(session)

    @staticmethod
    def get_attribute_class():
        return AttributeType


mapper (Software, tables.software,
    properties={
        "variants": relationship(SoftwareVariant, lazy=True, secondary=tables.software_variants),
        "category": relationship(SoftwareCategory),
        "vendor": relationship(Corporation,
                primaryjoin=tables.software.c.vendor_id==tables.corporations.c.id),
        "manufacturer": relationship(Corporation,
                primaryjoin=tables.software.c.manufacturer_id==tables.corporations.c.id),
    }
)

class SoftwareAttribute(object):
    ROW_DISPLAY = ("type", "value")

    def __repr__(self):
        return "%s=%s" % (self.type, self.value)

    @validates("value")
    def validate_value(self, attrname, value):
        return validate_value_type(self.type.value_type, value)

mapper(SoftwareAttribute, tables.software_attributes,
    properties={
            "software": relationship(Software, backref=backref("attributes",
                    cascade="all, delete, delete-orphan")),
            "type": relationship(AttributeType),
    },
)



#######################################
# Equipment model

# similar to ENTITY-MIB::PhysicalClass
class EquipmentCategory(object):

    def __str__(self):
        return "%s(%d)" % (self.name, self.id + 1)

mapper(EquipmentCategory, tables.equipment_category)

# IANAifType, minus obsolete and deprecated.
class InterfaceType(object):

    def __str__(self):
        return "%s(%d)" % (self.name, self.enumeration)

mapper(InterfaceType, tables.interface_type)


class Network(object):
    ROW_DISPLAY = ("name", "layer", "vlanid", "ipnetwork", "notes")

    def __str__(self):
        if self.layer == 2 and self.vlanid is not None:
            return "%s {%s}" % (self.name, self.vlanid)
        elif self.layer == 3 and self.ipnetwork is not None:
            return "%s (%s)" % (self.name, self.ipnetwork)
        else:
            return "%s[%d]" % (self.name, self.layer)

    def __repr__(self):
        return "Network(%r, %r, %r, %r)" % (self.name, self.layer, self.vlanid, self.ipnetwork)

mapper(Network, tables.networks,
    properties={
        "upperlayers": relationship(Network, backref=backref("lower",
                remote_side=[tables.networks.c.id])),
    },
)


class EquipmentModel(object):
    ROW_DISPLAY = ("manufacturer", "name", "category")

    def __str__(self):
        return str(self.name)

    def update_attribute(self, session, attrname, value):
        attrtype = AttributeType.get_by_name(session, str(attrname))
        existing = session.query(EquipmentModelAttribute).filter(and_(EquipmentModelAttribute.equipmentmodel==self,
                            EquipmentModelAttribute.type==attrtype)).first()
        if existing is None:
            attrib = create(EquipmentModelAttribute, equipmentmodel=self, type=attrtype, value=value)
            session.add(attrib)
            self.attributes.append(attrib)
        else:
            existing.value = value
        session.commit()

    def set_attribute(self, session, attrname, value):
        attrtype = AttributeType.get_by_name(session, str(attrname))
        attrib = create(EquipmentModelAttribute, equipmentmodel=self, type=attrtype, value=value)
        session.add(attrib)
        self.attributes.append(attrib)
        session.commit()

    def get_attribute(self, session, attrname):
        attrtype = AttributeType.get_by_name(session, str(attrname))
        try:
            ea = session.query(EquipmentModelAttribute).filter(and_(EquipmentModelAttribute.equipmentmodel==self,
                            EquipmentModelAttribute.type==attrtype)).one()
        except NoResultFound:
            raise ModelAttributeError("No attribute %r set." % (attrname,))
        return ea.value

    def del_attribute(self, session, attrtype):
        attrtype = AttributeType.get_by_name(session, str(attrtype))
        attrib = session.query(EquipmentModelAttribute).filter(and_(
                EquipmentModelAttribute.equipmentmodel==self, EquipmentModelAttribute.type==attrtype)).first()
        if attrib:
            self.attributes.remove(attrib)
            session.commit()

    @staticmethod
    def get_attribute_list(session):
        return AttributeType.get_attribute_list(session)

    @staticmethod
    def get_attribute_class():
        return AttributeType


mapper(EquipmentModel, tables.equipment_model,
    properties={
        "embeddedsoftware": relationship(Software, secondary=tables.equipment_model_embeddedsoftware),
        "category": relationship(EquipmentCategory, order_by=tables.equipment_category.c.name),
        "manufacturer": relationship(Corporation, order_by=tables.corporations.c.name),
    }
)


class EquipmentModelAttribute(object):
    ROW_DISPLAY = ("type", "value")

    def __repr__(self):
        return "%s=%s" % (self.type, self.value)

    @validates("value")
    def validate_value(self, attrname, value):
        return validate_value_type(self.type.value_type, value)

mapper(EquipmentModelAttribute, tables.equipment_model_attributes,
    properties={
            "equipmentmodel": relationship(EquipmentModel, backref=backref("attributes",
                    cascade="all, delete, delete-orphan")),
            "type": relationship(AttributeType),
    },
)


class Equipment(object):
    ROW_DISPLAY = ("name", "model", "serno")

    def __str__(self):
        return str(self.name)

    def __unicode__(self):
        return self.name

    def update_attribute(self, session, attrname, value):
        attrtype = AttributeType.get_by_name(session, str(attrname))
        existing = session.query(EquipmentAttribute).filter(and_(EquipmentAttribute.equipment==self,
                            EquipmentAttribute.type==attrtype)).first()
        if existing is None:
            attrib = create(EquipmentAttribute, equipment=self, type=attrtype, value=value)
            session.add(attrib)
            self.attributes.append(attrib)
        else:
            existing.value = value
        session.commit()

    def set_attribute(self, session, attrname, value):
        attrtype = AttributeType.get_by_name(session, str(attrname))
        attrib = create(EquipmentAttribute, equipment=self, type=attrtype, value=value)
        session.add(attrib)
        self.attributes.append(attrib)
        session.commit()

    def get_attribute(self, session, attrname):
        attrtype = AttributeType.get_by_name(session, str(attrname))
        try:
            ea = session.query(EquipmentAttribute).filter(and_(EquipmentAttribute.equipment==self,
                            EquipmentAttribute.type==attrtype)).one()
        except NoResultFound:
            raise ModelAttributeError("No attribute %r set." % (attrname,))
        return ea.value

    def del_attribute(self, session, attrname):
        attrtype = AttributeType.get_by_name(session, str(attrname))
        attrib = session.query(EquipmentAttribute).filter(and_(
                EquipmentAttribute.equipment==self, EquipmentAttribute.type==attrtype)).first()
        if attrib:
            self.attributes.remove(attrib)
            session.commit()

    @staticmethod
    def get_attribute_list(session):
        return AttributeType.get_attribute_list(session)

    @staticmethod
    def get_attribute_class():
        return AttributeType

    # interface management
    def add_interface(self, session, name,
                ifindex=None, interface_type=None, macaddr=None, ipaddr=None, network=None):
        if interface_type is not None and isinstance(interface_type, basestring):
            interface_type = session.query(InterfaceType).filter(InterfaceType.name==interface_type).one()
        if network is not None and isinstance(network, basestring):
            network = session.query(Network).filter(Network.name==network).one()
        intf = create(Interface, name=name, equipment=self, ifindex=ifindex,
                interface_type=interface_type, macaddr=macaddr, ipaddr=ipaddr,
                network=network)
        session.add(intf)
        self.interfaces[name] = intf
        session.commit()

    def attach_interface(self, session, **selectkw):
        """Attach an existing interface entry that is currently detached."""
        q = session.query(Interface)
        for attrname, value in selectkw.items():
            q = q.filter(getattr(Interface, attrname) == value)
        intf = q.one()
        if intf.equipment is not None:
            raise ModelError("Interface already attached to {0!r}".format(intf.equipment))
        self.interfaces[intf.name] = intf
        session.commit()

    def del_interface(self, session, name):
        del self.interfaces[name]
        session.commit()

    @property
    def any_interface(self):
        keys = self.interfaces.keys()
        if keys:
            return self.interfaces[keys[0]]
        else:
            return None

    def connect(self, session, intf, network, force=False):
        """Connect this equipments named interface to a network.

        If "force" is True then alter network part of address to match
        network.
        """
        intf = self.interfaces[intf]
        if isinstance(network, basestring):
            network = session.query(Network).filter(Network.name==network).one()
        # alter the IP mask to match the network
        addr = intf.ipaddr
        if addr is not None and network.ipnetwork is not None:
            addr.maskbits = network.ipnetwork.maskbits
            if addr.network != network.ipnetwork.network:
                if force:
                    addr.network = network.ipnetwork.network
                else:
                    raise ModelError("Can't add interface to network with different network numbers.")
            intf.ipaddr = addr
        intf.network = network
        session.commit()

    def disconnect(self, session, intf):
        intf = self.interfaces[intf]
        intf.network = None
        session.commit()

    # properties provided elsewhere:
    #    attributes
    #    capabilities

mapper(Equipment, tables.equipment,
    properties={
        "model": relationship(EquipmentModel),
        "owner": relationship(User),
        "vendor": relationship(Corporation),
        "account": relationship(LoginAccount),
        "language": relationship(Language),
        "location": relationship(Location),
        "subcomponents": relationship(Equipment,
                backref=backref('parent', remote_side=[tables.equipment.c.id])),
        "software": relationship(Software, lazy=True, secondary=tables.equipment_software),
    },
)


class EquipmentAttribute(object):
    ROW_DISPLAY = ("type", "value")

    def __repr__(self):
        return "%s=%s" % (self.type, self.value)

    @validates("value")
    def validate_value(self, attrname, value):
        return validate_value_type(self.type.value_type, value)

mapper(EquipmentAttribute, tables.equipment_attributes,
    properties={
            "equipment": relationship(Equipment, backref=backref("attributes",
                    cascade="all, delete, delete-orphan")),
            "type": relationship(AttributeType),
    },
)


class Interface(object):
    ROW_DISPLAY = ("name", "ifindex", "interface_type", "equipment", "macaddr", "ipaddr", "network")

    def __str__(self):
        return "%s (%s)" % (self.name, self.ipaddr)

    def __unicode__(self):
        extra = []
        if self.ipaddr is not None:
            extra.append(unicode(self.ipaddr.CIDR))
        if self.macaddr is not None:
            extra.append(unicode(self.macaddr))
        if extra:
            return "%s (%s)" % (self.name, ", ".join(extra))
        else:
            return self.name

    def __repr__(self):
        return "Interface(%r, ipaddr=%r)" % (self.name, self.ipaddr)

    def create_subinterface(self, session, subname):
        intf = create(Interface, name=self.name+subname, ifindex=0,
                interface_type=self.interface_type, parent=self)
        session.add(intf)
        session.commit()

    @classmethod
    def select_unattached(cls, session):
        return session.query(cls).filter(cls.equipment == None).order_by(cls.ipaddr)


mapper(Interface, tables.interfaces,
    properties = {
        "interface_type": relationship(InterfaceType, order_by=tables.interface_type.c.name),
        "subinterfaces": relationship(Interface,
                backref=backref('parent', remote_side=[tables.interfaces.c.id])),
        "network": relationship(Network, backref="interfaces", order_by=tables.networks.c.name),
        "equipment": relationship(Equipment,
                backref=backref("interfaces", collection_class=column_mapped_collection(tables.interfaces.c.name),
                        cascade="all, delete")),
    }
)


### environments

class EnvironmentAttributeType(object):
    ROW_DISPLAY = ("name", "value_type", "description")

    def __str__(self):
        return "%s(%s)" % (self.name, self.value_type)

    @classmethod
    def get_by_name(cls, session, name):
        try:
            attrtype = session.query(cls).filter(cls.name==str(name)).one()
        except NoResultFound:
            raise ModelAttributeError("No attribute type %r defined." % (name,))
        return attrtype

    @classmethod
    def get_attribute_list(cls, session):
        return session.query(cls.name, cls.value_type)


mapper(EnvironmentAttributeType, tables.environmentattribute_type,
)


class Environment(object):
    ROW_DISPLAY = ("name", "owner")

    def __repr__(self):
        return self.name

    def update_attribute(self, session, attrname, value):
        attrtype = EnvironmentAttributeType.get_by_name(session, str(attrname))
        existing = session.query(EnvironmentAttribute).filter(and_(EnvironmentAttribute.environment==self,
                            EnvironmentAttribute.type==attrtype)).first()
        if existing is None:
            attrib = create(EnvironmentAttribute, environment=self, type=attrtype, value=value)
            session.add(attrib)
            self.attributes.append(attrib)
        else:
            existing.value = value
        session.commit()

    def set_attribute(self, session, attrname, value):
        attrtype = EnvironmentAttributeType.get_by_name(session, str(attrname))
        attrib = create(EnvironmentAttribute, environment=self, type=attrtype, value=value)
        session.add(attrib)
        self.attributes.append(attrib)
        session.commit()

    def get_attribute(self, session, attrname):
        attrtype = EnvironmentAttributeType.get_by_name(session, str(attrname))
        try:
            ea = session.query(EnvironmentAttribute).filter(and_(EnvironmentAttribute.environment==self,
                            EnvironmentAttribute.type==attrtype)).one()
        except NoResultFound:
            raise ModelAttributeError("No attribute %r set." % (attrname,))
        return ea.value

    def del_attribute(self, session, attrtype):
        attrtype = EnvironmentAttributeType.get_by_name(session, str(attrtype))
        attrib = session.query(EnvironmentAttribute).filter(and_(
                EnvironmentAttribute.environment==self, EnvironmentAttribute.type==attrtype)).first()
        if attrib:
            self.attributes.remove(attrib)
            session.commit()

    @staticmethod
    def get_attribute_list(session):
        return EnvironmentAttributeType.get_attribute_list(session)

    @staticmethod
    def get_attribute_class():
        return EnvironmentAttributeType

    equipment = association_proxy('testequipment', 'equipment')

    def get_equipment_with_role(self, session, rolename):
        TE = TestEquipment # shorthand
        role = SoftwareCategory.get_by_name(session, rolename)
        if role is None:
           raise ModelError("No such role defined in environment: {0}".format(rolename))
        qq = session.query(TE).filter(and_(
                TE.environment==self,
                TE.UUT==False,  # UUT does not take on other roles.
                TE.roles.contains(role)))
        te = qq.first()
        if te is None:
            raise ModelError("No role '{0}' defined in environment '{1}'.".format(rolename, self.name))
        return te.equipment

    def get_all_equipment_with_role(self, session, rolename):
        TE = TestEquipment # shorthand
        role = SoftwareCategory.get_by_name(session, rolename)
        if role is None:
            raise ModelError("No such role defined in environment: {0}".format(rolename))
        qq = session.query(TE).filter(and_(
                TE.environment==self,
                TE.roles.contains(role)))
        return [te.equipment for te in qq.all()]

    def get_DUT(self, session):
        qq = session.query(TestEquipment).filter(and_(TestEquipment.environment==self,
                TestEquipment.UUT==True))
        eq = qq.first()
        if eq is None:
            raise ModelError("DUT is not defined in environment '{}'.".format(self.name))
        return eq.equipment

    def get_supported_roles(self, session):
        rv = []
        for te in session.query(TestEquipment).filter(TestEquipment.environment==self):
            for role in te.roles:
                rv.append(role.name)
        return removedups(rv)

    # user/owner management.
    # This field is also used as a lock on the environment.
    def set_owner_by_username(self, session, username):
        user = User.get_by_username(session, username)
        self.owner = user
        session.commit()

    def is_owned(self):
        return self.owner is not None

    def clear_owner(self, session):
        self.owner = None
        session.commit()


mapper(Environment, tables.environments,
    properties={
        "owner": relationship(User),
    },
)

class TestEquipment(object):
    """Binds equipment and a test environment.
    Also specifies the unit under test.
    """
    ROW_DISPLAY = ("equipment", "UUT")

    def __repr__(self):
        if self.UUT:
            return self.equipment.name + " (DUT)"
        else:
            return self.equipment.name

mapper(TestEquipment, tables.testequipment,
    properties={
        "roles": relationship(SoftwareCategory, secondary=tables.testequipment_roles),
        "equipment": relationship(Equipment),
        "environment": relationship(Environment, backref=backref("testequipment", cascade="all, delete, delete-orphan")),
    },
)


class EnvironmentAttribute(object):
    ROW_DISPLAY = ("type", "value")

    def __repr__(self):
        return "%s=%s" % (self.type, self.value)

    @validates("value")
    def validate_value(self, attrname, value):
        return validate_value_type(self.type.value_type, value)

mapper(EnvironmentAttribute, tables.environment_attributes,
    properties={
            "environment": relationship(Environment, backref=backref("attributes",
                    cascade="all, delete, delete-orphan")),
            "type": relationship(EnvironmentAttributeType),
    },
)



#######################################
# trap storage

class Trap(object):
    ROW_DISPLAY = ("timestamp", "value")
    def __init__(self, timestamp, trap):
        self.timestamp = timestamp
        self.trap = trap # pickled

    def __str__(self):
        return "%s: %s" % (self.timestamp, self.trap)

mapper(Trap, tables.traps)


#######################################

class Requirement(object):
    ROW_DISPLAY = ("uri",)

    def __str__(self):
        return str(self.uri)

    def __repr__(self):
        return "Requirement(%r)" % (self.uri,)

mapper(Requirement, tables.requirement_ref,
)


#######################################
# Test relations and results

class TestCase(object):
    ROW_DISPLAY = ("name", "purpose", "testimplementation")

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return "TestCase(%r)" % (self.name,)

    def get_latest_result(self, session):
        sq = session.query(func.max(TestResult.starttime)).filter(and_(
                TestResult.testcase==self,
                TestResult.valid==True)).subquery()
        return session.query(TestResult).filter(and_(
                TestResult.starttime==sq,
                TestResult.testcase==self,
                    )).first()

    def get_all_results(self, session):
        return session.query(TestResult).filter(and_(
                TestResult.valid==True,
                TestResult.testcase==self))

    def get_data(self, session):
        for res in self.get_all_results(session):
            data = res.data
            if data:
                for datum in data:
                    yield datum

    @classmethod
    def get_by_name(cls, dbsession, name):
        return dbsession.query(cls).filter(cls.name==name).first()

    @classmethod
    def get_by_implementation(cls, dbsession, implementation):
        return dbsession.query(cls).filter(cls.testimplementation==implementation).first()

mapper(TestCase, tables.test_cases,
    properties={
        "functionalarea": relationship(FunctionalArea, secondary=tables.test_cases_areas),
        "reference": relationship(Requirement),
        "prerequisites": relationship(TestCase, secondary=tables.test_cases_prerequisites,
            primaryjoin=tables.test_cases.c.id==tables.test_cases_prerequisites.c.testcase_id,
            secondaryjoin=tables.test_cases_prerequisites.c.prerequisite_id==tables.test_cases.c.id,
            backref="dependents"),
    },
)


class TestSuite(object):
    ROW_DISPLAY = ("name", "suiteimplementation")

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return "TestSuite(%r)" % (self.name,)

    def get_latest_result(self, session):
        sq = session.query(func.max(TestResult.starttime)).filter(and_(
                TestResult.objecttype==OBJ_TESTSUITE,
                TestResult.testsuite==self,
                TestResult.valid==True)).subquery()
        return session.query(TestResult).filter(and_(
                TestResult.starttime==sq,
                TestResult.testsuite==self,
                    )).first()
    @classmethod
    def get_latest_results(cls, session):
        filt = and_(TestResult.objecttype==OBJ_TESTSUITE, TestResult.valid==True)
        return session.query(TestResult).filter(filt).order_by(TestResult.starttime).limit(10)

    @classmethod
    def get_suites(cls, session):
        return session.query(cls).filter(cls.valid==True).order_by("name").all()

    @classmethod
    def get_by_name(cls, dbsession, name):
        return dbsession.query(cls).filter(cls.name==name).all()

    @classmethod
    def get_by_implementation(cls, dbsession, implementation):
        return dbsession.query(cls).filter(cls.suiteimplementation==implementation).first()


mapper(TestSuite, tables.test_suites,
    properties={
        "project": relationship(Project),
        "components": relationship(Component, secondary=tables.components_suites, backref="suites"),
        "testcases": relationship(TestCase, secondary=tables.test_suites_testcases, backref="suites"),
        "subsuites": relationship(TestSuite, secondary=tables.test_suites_suites,
            primaryjoin=tables.test_suites.c.id==tables.test_suites_suites.c.from_testsuite_id,
            secondaryjoin=tables.test_suites_suites.c.to_testsuite_id==tables.test_suites.c.id,
            backref="suites"),
    },
)

# A UseCase is a dynamic suite constructor (construct pycopia.QA.core.TestSuite objects at run time).
class UseCase(object):
    ROW_DISPLAY = ("name", "purpose")

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return "UseCase(name=%r)" % (self.name,)

mapper(UseCase, tables.use_cases)


class TestJob(object):
    ROW_DISPLAY = ("name", "schedule")

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return "TestJob(%r)" % (self.name,)

mapper(TestJob, tables.test_jobs,
    properties = {
        "user": relationship(User),
        "environment": relationship(Environment, order_by=tables.environments.c.name),
        "suite": relationship(TestSuite),
        "schedule": relationship(Schedule),
    }
)


class TestResult(object):
    ROW_DISPLAY = ("testsuite", "testcase", "testimplementation", "tester", "result", "starttime")
    def __init__(self, **kwargs):
        for name, value in kwargs.items():
             setattr(self, name, value)

    def __str__(self):
                            #"TestSuite", "Test"
        if self.objecttype in (1, 2):
            if self.testcase is None:
                return "%s(%s): %s" % (self.testimplementation, self.objecttype, self.result)
            else:
                return "%s(%s): %s" % (self.testcase, self.objecttype, self.result)
        else:
            return "%s: %s" % (self.objecttype, self.result)

    def __repr__(self):
        return "TestResult(testimplementation=%r, objecttype=%r, result=%r)" % (
                self.testimplementation, self.objecttype, self.result)

    @classmethod
    def get_latest_results(cls, session, user=None):
        """Returns last 10 TestRunner (top-level) results.
        Optionally filtered by user.
        """
        if user is None:
            filt = and_(cls.objecttype==OBJ_TESTRUNNER, cls.valid==True)
        else:
            filt = and_(cls.objecttype==OBJ_TESTRUNNER, cls.tester==user, cls.valid==True)
        return session.query(cls).filter(filt).order_by(cls.starttime).limit(10)

    @classmethod
    def get_latest_run(cls, session, user):
        """Return the last Runner (top-level) TestResult for the User."""
        sq = session.query(func.max(cls.starttime)).filter(and_(
                cls.tester==user,
                cls.objecttype==OBJ_TESTRUNNER,
                cls.valid==True)).subquery()
        return session.query(cls).filter(and_(
                cls.starttime==sq,
                cls.tester==user,
                cls.objecttype==OBJ_TESTRUNNER)).first()


mapper(TestResult, tables.test_results,
    properties = {
        "tester": relationship(User),
        "environment": relationship(Environment, order_by=tables.environments.c.name),
        "testcase": relationship(TestCase),
        "testsuite": relationship(TestSuite),
        "build": relationship(ProjectVersion),
        "subresults": relationship(TestResult, backref=backref("parent",
                                remote_side=[tables.test_results.c.id])),
    }
)

class TestResultData(object):
    ROW_DISPLAY = ("note",)

    def __str__(self):
        return "TestResultData: note: %r" % (self.note,)

    def __repr__(self):
        return "TestResultData(%r, %r)" % (self.data, self.note)

mapper(TestResultData, tables.test_results_data,
        properties = {
            "testresult": relationship(TestResult, backref=backref("data",
                    cascade="all, delete, delete-orphan", passive_deletes=True)),
        }
)


################ risk assessment tables

class RiskCategory(object):
    ROW_DISPLAY = ("name", )

    def __repr__(self):
        return "RiskCategory(%r, %r)" % (self.name, self.description)

    def __str__(self):
        return str(self.name)

mapper(RiskCategory, tables.risk_category)


class RiskFactor(object):
    ROW_DISPLAY = ("description", )

    def __repr__(self):
        return "RiskFactor(%s)" % (self.description,)

    def __str__(self):
        return str(self.description)

mapper(RiskFactor, tables.risk_factors,
    properties={
        "requirement": relationship(Requirement),
        "testcase": relationship(TestCase),
        "risk_category": relationship(RiskCategory),
    }
)



#######################################
# capabilities for hardware

class CapabilityGroup(object):
    ROW_DISPLAY = ("name",)

    def __str__(self):
        return str(self.name)

mapper(CapabilityGroup, tables.capability_group)


class CapabilityType(object):
    ROW_DISPLAY = ("name", "value_type", "description", "group")

    def __str__(self):
        return "%s(%s)" % (self.name, self.value_type)

mapper(CapabilityType, tables.capability_type,
    properties={
        "group": relationship(CapabilityGroup),
    }
)


class Capability(object):
    ROW_DISPLAY = ("type", "value")

    def __repr__(self):
        return "%s=%s" % (self.type, self.value)

    @validates("value")
    def validate_value(self, attrname, value):
        return validate_value_type(self.type.value_type, value)

mapper(Capability, tables.capability,
    properties={
        "type": relationship(CapabilityType),
        "equipment": relationship(Equipment, backref=backref("capabilities",
                    cascade="all, delete, delete-orphan")),
    }
)


#######################################
# configuration data. This models a hierarchical storage structures. It
# should be updated with the pycopia.db.config wrapper objects.

class Config(object):
    ROW_DISPLAY = ("name", "value", "user", "testcase", "testsuite")

    def __str__(self):
        if self.value is NULL:
            return "[%s]" % self.name
        else:
            return "%s=%r" % (self.name, self.value)

    def __repr__(self):
        return "Config(%r, %r)" % (self.name, self.value)

    def set_owner(self, session, user):
        if self.container is not None:
            if isinstance(user, basestring):
                user = User.get_by_username(session, user)
            self.user = user
            session.commit()

    def get_child(self, session, name):
        session.query(Config).filter

        q = session.query(Config).filter(and_( Config.container==self, Config.name==name))
        try:
            return q.one()
        except NoResultFound:
            raise ModelError("No sub-node %r set." % (name,))


mapper(Config, tables.config,
    properties={
        'children': relationship(Config, cascade="all",
            backref=backref("container",
                    remote_side=[tables.config.c.id, tables.config.c.user_id])),
        'testcase': relationship(TestCase),
        'testsuite': relationship(TestSuite),
        'user': relationship(User),
    }
)



#######################################
## Utility functions
#######################################

def class_names():
    for mapper in _mapper_registry:
        yield mapper._identity_class.__name__


def get_primary_key(class_):
    """Return the primary key column."""
    return inspect(class_).primary_key


def get_primary_key_value(dbrow):
    pkname = get_primary_key_name(dbrow.__class__)
    if pkname:
        return getattr(dbrow, str(pkname))
    else:
        raise ModelError("No primary key for this row: {!r}".format(dbrow))


def get_primary_key_name(class_):
    """Return name or names of primary key column. Return None if not defined."""
    pk = inspect(class_).primary_key
    pk_l = len(pk)
    if pk_l == 0:
        return None
    elif pk_l == 1:
        return pk[0].name
    else:
        return tuple(p.name for p in pk)


# structure returned by get_metadata function.
MetaDataTuple = collections.namedtuple("MetaDataTuple",
        "coltype, colname, default, m2m, nullable, uselist, collection")

def get_metadata_iterator(class_):
    for prop in inspect(class_).iterate_properties:
        name = prop.key
        if name.startswith("_") or name == "id" or name.endswith("_id"):
            continue
        md = _get_column_metadata(prop)
        if md is None:
            continue
        yield md

def get_column_metadata(class_, colname):
    prop = inspect(class_).get_property(colname)
    md = _get_column_metadata(prop)
    if md is None:
        raise ValueError("Not a column name: %r." % (colname,))
    return md

def _get_column_metadata(prop):
    name = prop.key
    m2m = False
    default = None
    nullable = None
    uselist = False
    collection = None
    proptype = type(prop)
    if proptype is ColumnProperty:
        coltype = type(prop.columns[0].type).__name__
        try:
            default = prop.columns[0].default
        except AttributeError:
            default = None
        else:
            if default is not None:
                default = default.arg(None)
        nullable = prop.columns[0].nullable
    elif proptype is RelationshipProperty:
        coltype = RelationshipProperty.__name__
        m2m = prop.secondary is not None
        nullable = prop.local_remote_pairs[0][0].nullable
        uselist = prop.uselist
        if prop.collection_class is not None:
            collection = type(prop.collection_class()).__name__
        else:
            collection = "list"
    else:
        return None
    return MetaDataTuple(coltype, str(name), default, m2m, nullable, uselist, collection)


def get_choices(session, modelclass, colname, order_by=None):
    """Get possible choices for a field.

    Returns a list of tuples, (id/value, name/label) of available choices.
    """
    # first check for column type with get_choices method.
    mapper = inspect(modelclass)
    try:
        return mapper.columns[colname].type.get_choices()
    except (AttributeError, KeyError):
        pass
    try:
        mycol = getattr(modelclass, colname)
    except AttributeError:
        # If attribute is a backref, it won't exist initially. It needs to be triggered by using in
        # a query and fetched again.
        session.query(modelclass)
        mycol = getattr(modelclass, colname)
    try:
        relmodel = mycol.property.mapper.class_
    except AttributeError:
        return []
    # no choices in type, but has a related model table...
    mymeta = get_column_metadata(modelclass, colname)
    if mymeta.uselist:
        if mymeta.m2m:
            q = session.query(relmodel)
        else:
            # only those that are currently unassigned
            rs = mycol.property.local_remote_pairs[0][1]
            q = session.query(relmodel).filter(rs == None)
    else:
        q = session.query(relmodel)

    # add optional order_by, default to ordering by first ROW_DISPLAY column.
    try:
        order_by = order_by or relmodel.ROW_DISPLAY[0]
    except (AttributeError, IndexError):
        pass
    if order_by:
        order_by = getattr(relmodel, order_by)
        if type(order_by.property) is RelationshipProperty:
            q = q.join(order_by)
        q = q.order_by(order_by)
    # Return the list of (id, stringrep) tuples.
    # This structure is usable by the XHTML form generator...
    return [(relrow.id, str(relrow)) for relrow in q]


def get_metadata(class_):
    """Returns a list of MetaDataTuple structures.
    """
    return list(get_metadata_iterator(class_))


def get_metadata_map(class_):
    rv = {}
    for metadata in get_metadata_iterator(class_):
        rv[metadata.colname] = metadata
    return rv


def get_rowdisplay(class_):
    return getattr(class_, "ROW_DISPLAY", None) or [t.colname for t in get_metadata(class_)]


if __name__ == "__main__":
    import os
    from pycopia import autodebug
    if sys.flags.interactive:
        from pycopia import interactive

    #print (get_metadata(Equipment))

    #print(inspect(Equipment).get_property("name"))
    assert get_primary_key_name(Equipment) == "id"
    #print(get_primary_key_name(Session))

    #print (get_column_metadata(Equipment, "interfaces"))
    #print (get_column_metadata(Network, "interfaces"))

    sess = get_session()

    #print (choices)
    #choices = get_choices(sess, TestCase, "priority", order_by=None)
    #print (choices)
    print (get_choices(sess, Equipment, "interfaces", order_by=None))
    #q = sess.query(Interface).filter(Interface.equipment == None)

    ## assumes your host name is in the db for testing.
    #print (Equipment.attributes)
    #print (Equipment.interfaces)
    #eq = sess.query(Equipment).filter(Equipment.name.like(os.uname()[1] + "%")).one()
    #print (eq.attributes)
    #print (Equipment.attributes)
    #print (Equipment.interfaces)
    #print "eq = ", eq
    #print "Atributes:"
    #print (eq.attributes)
    #print "Interfaces:"
    #print eq.interfaces
    #eq.add_interface(sess, "eth1", interface_type="ethernetCsmacd", ipaddr="172.17.101.2/24")
#    print "Capabilities:"
#    print eq.capabilities

#    for res in  TestResult.get_latest_results(sess):
#        print (res)

#    print "\nlatest run:"
#    user = User.get_by_username(sess, "keith")
#    print(user)
#    print(type(user))
#    print(user.full_name)
#    lr = TestResult.get_latest_run(sess, user)
#    print lr
#    print
    #print dir(class_mapper(Equipment))
    #print
    #print class_mapper(Equipment).get_property("name")
#    for tr in TestSuite.get_latest_results(sess):
#        print (tr)
#    tc = TestCase.get_by_implementation(sess, "testcases.unittests.WWW.client.HTTPPageFetch")
#    print(tc)
#    print(get_primary_key_value(tc))
#    print(tc.id)
#    ltr = tc.get_latest_result(sess)
#    print(ltr)
#    print(ltr.id)
#    print(ltr.data)
#    print(ltr.data[0].data)
#
#    for tr in tc.get_data(sess):
#        print(tr)
#    with DatabaseContext() as sess:
#        for intf in Interface.select_unattached(sess):
#            print(intf)
#    print(type(TestSuite.get_by_implementation(sess, "testcases.unittests.WWW.mobileget.MobileSendSuite")))
#    print (TestSuite.get_suites(sess))
    #print(get_primary_key(Session))
    sess.close()

