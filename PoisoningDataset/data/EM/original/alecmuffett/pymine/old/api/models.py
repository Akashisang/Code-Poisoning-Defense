#!/usr/bin/env python
##
## Copyright 2009 Adriana Lukas & Alec Muffett
##
## Licensed under the Apache License, Version 2.0 (the "License"); you
## may not use this file except in compliance with the License. You
## may obtain a copy of the License at
##
## http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
## implied. See the License for the specific language governing
## permissions and limitations under the License.
##

"""
PyMine Models

The transcoder methods - x2y_foo() - below provide a lot of the
security for pymine, and govern the movement of data between three
'spaces' of data representation; these are:

r-space - request space, where data are held in a HttpRequest

s-space - structure space, where data are held in a dict

m-space - model space, where data are fields in model instances

The reason for keeping separate spaces is partly philosophic - that
there should be a clearly defined breakpoint between the two worlds,
and this is it; if we just serialized models and slung them back and
forth, the mine would be wedded to Django evermore, which is not a
good thing;

If we tried to go the simple route and keep the data structures
similar, errors would be hard to flush out plus we would tend to do
things only the Django way - the Mine API was first written from
scratch and driven using 'curl' so this is definitely portable.

Further: certain s-space attributes (eg: 'relationInterests') map to
more than one m-space attributes, so these functions provide parsing
as well as translation.

r-space and s-space share exactly the same naming conventions, ie:
they use mixedCase key (aka: 's-attribute' or 'sattr') such as
'relationName' and 'tagDescription' and 'itemId' to label data; the
only meaningful difference is that in r-space all data are held in
HttpRequest objects as strings; when pulled into s-space Python
dictionaries, any data which are integers (eg: itemId) are converted
to Python integers.

For obvious reasons it's never necessary to go from s-space to
r-space; instead data only ever comes *out* of HttpRequests and *into*
structures, hence there are only r2s_foo methods, and indeed only two
of those: r2s_string and r2s_int

Transfers between s-space (dictionary entries such as s['itemId']) and
m-space (m.id, where 'm' is a instance of the Item model and 'id' is
the Item table primary key) are bidirectional; because m-space and
s-space both frequently use strings and python integers, and since
s-space uses Python ints, many transfers can be handled with simple
blind copies using introspection to access the model instance.

Note: as a general rule m2s routines should not copy-out a None item,
blank or null reference; however s2m routines *may* want to copy-in
'None' for purposes of erasure.  All copy routines should check the
validity of their source/destination attributes.

One of the more complex translations between spaces are DateTime
objects; in m-space we use whatever Django mandates, and in s-space we
use a string representation of the time/date in ISO format, which is
very close to what ATOM specifies - which in turn is probably what we
will standardise on eventually

"""

from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import FileSystemStorage
from django.db import models, transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import feedgenerator
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect

import hashlib
import itertools
import re

import pymine.util.base58 as b58
import pymine.util.base64_mine as b64

##################################################################

# using pycrypto 2.0.1
# http://www.amk.ca/python/code/crypto (old, tarball, works)
# http://www.pycrypto.org/ (new)

from Crypto.Cipher import AES

##################################################################

# magic storage for database items

item_fss = FileSystemStorage(location = settings.MINE_DBDIR_FILES)
thumb_fss = FileSystemStorage(location = settings.MINE_DBDIR_THUMBS)
comment_fss = FileSystemStorage(location = settings.MINE_DBDIR_COMMENTS)
fss_yyyymmdd = '%Y-%m/%d'

##################################################################

# choices for the item status

item_status_choices = (
    ( 'X', 'private' ),
    ( 'S', 'shared' ),
    ( 'P', 'public' ),
    )

# create a reverse lookup table, long->short
# other direction is covered by m.get_status_display()

status_lookup = {}
for short, long in item_status_choices: status_lookup[long] = short

##################################################################
##################################################################
##################################################################

class AbstractModelField:
    """
    This is an factory class that is used to abstract field
    definitions and simplify porting from Django to Google AppEngine.
    """

    STRING_SHORT = 256 # bytes

    @classmethod
    def __defopts(klass, **kwargs):
	"""
	Standardised argument parser for AbstractModelField methods;
	implements 'required'; imports 'unique', 'symmetrical',
	'storage', and 'upload_to'
	"""

	if kwargs.get('required', True):
	    opts = dict(null=False, blank=False)
	else:
	    opts = dict(null=True, blank=True)

	for foo in ('unique', 'symmetrical', 'storage', 'upload_to'):
	    if foo in kwargs:
		opts[foo] = kwargs[foo] # import, not set

	return opts

    @classmethod
    def last_modified(klass):
	"""implements last_modified date"""
	return models.DateTimeField(auto_now=True)

    @classmethod
    def created(klass):
	"""implements created date"""
	return models.DateTimeField(auto_now_add=True)

    @classmethod
    def datetime(klass, **kwargs):
	"""implements date/time field"""
	opts = klass.__defopts(**kwargs)
	return models.DateTimeField(**opts)

    @classmethod
    def reference(klass, what, **kwargs):
	"""implements foreign-keys"""
	opts = klass.__defopts(**kwargs)
	return models.ForeignKey(what, **opts)

    @classmethod
    def reflist(klass, what, **kwargs):
	"""implements list-of-foreign-keys; parses out 'pivot' argument"""
	opts = klass.__defopts(**kwargs)
	pivot = kwargs.get('pivot', None)
	if pivot: opts['related_name'] = pivot
	return models.ManyToManyField(what, **opts)

    @classmethod
    def string(klass, **kwargs):
	"""implements string"""
	opts = klass.__defopts(**kwargs)
	return models.CharField(max_length=klass.STRING_SHORT, **opts)

    @classmethod
    def text(klass, **kwargs):
	"""implements a text area / text of arbitrary size"""
	opts = klass.__defopts(**kwargs)
	return models.TextField(**opts)

    @classmethod
    def slug(klass, **kwargs):
	"""implements a slug (alphanumeric string, no spaces)"""
	opts = klass.__defopts(**kwargs)
	return models.SlugField(max_length=klass.STRING_SHORT, **opts)

    @classmethod
    def bool(klass, default):
	"""implements a boolean (true/false)"""
	return models.BooleanField(default=default)

    @classmethod
    def integer(klass, default):
	"""implements an integer"""
	return models.PositiveIntegerField(default=default)

    @classmethod
    def choice(klass, choices):
	"""implements a choices-field (max length of an encoded choice is 1 character)"""
	return models.CharField(max_length=1, choices=choices)

    @classmethod
    def url(klass, **kwargs):
	"""implements a URL string"""
	opts = klass.__defopts(**kwargs)
	return models.URLField(max_length=klass.STRING_SHORT, **opts)

    @classmethod
    def email(klass, **kwargs):
	"""implements an e-mail address"""
	opts = klass.__defopts(**kwargs)
	return models.EmailField(max_length=klass.STRING_SHORT, **opts)

    @classmethod
    def file(klass, **kwargs):
	"""implements a file"""
	opts = klass.__defopts(**kwargs)
	return models.FileField(**opts)

##################################################################
##################################################################
##################################################################

class AbstractModel(models.Model):
    """
    AbstractModel is the parent class for all Models below, providing
    the common 'created' and 'last_modified' fields.
    """

    created = AbstractModelField.created()
    last_modified = AbstractModelField.last_modified()
    is_deleted = AbstractModelField.bool(False)

    def delete(self):
	""" """
	self.is_deleted = True
	self.save()

    def delete_for_real(self):
	""" """
	pass

    class Meta:
	abstract = True

##################################################################
##################################################################
##################################################################

class Registry(AbstractModel):
    """key/value pairs for Mine configuration"""

    key = AbstractModelField.slug(unique=True)
    value = AbstractModelField.text()

    @classmethod
    def get(klass, key):
	""" """
	return Registry.objects.get(key=key).value

    @classmethod
    def get_decoded(klass, key):
	""" """
	return b64.decode(klass.get(key))

    @classmethod
    def set(klass, key, value, overwrite_ok):
	""" """
	r, created = Registry.objects.get_or_create(key=key, defaults={ 'value': value })
	if not created and not int(overwrite_ok):
	    raise RuntimeError, 'not allowed to overwrite existing Registry key: %s' % key
	r.save()
	return r

    @classmethod
    def set_encoded(klass, key, value, overwrite_ok):
	""" """
	return klass.set(key, b64.encode(value), overwrite_ok)

    def to_structure(self):
	""" """
	s = {}
	s[self.key] = self.value # this is why it is not a Thing
	s['keyCreated'] = self.created.isoformat()
	s['keyLastModified'] = self.last_modified.isoformat()
	return s

    class Meta:
	ordering = ['key']
	verbose_name = 'RegisterEntry'
	verbose_name_plural = 'Registry'

    def __unicode__(self):
	return self.key

##################################################################
##################################################################
##################################################################

class Minekey:
    """
    A Minekey encodes all the data that a subscriber can use to
    retreive stuff from the user's mine, creating an opaque token that
    is hopefully unforgable.
    """

    key_magic = 'P1' # PYMINE VERSION 1
    corefmt = '%s,%d,%d,%d,%d,%s'
    valid_methods = ( 'get', 'put' )

    aes_mode = AES.MODE_CBC

    def __init__(self, **kwargs):
	"""
	Populates a Minekey with 5 items of information:

	method=, rid=, rvsn=, iid=, depth=

	method = 'get' or 'put'; these are somewhat analogous to GET
	and POST in HTTP, but we override the latter for REST purposes
	because in the subscriber interface a Minekey can arrive by
	either GET or POST methods.  Note that there is no 'delete' or
	anything exotic like that.

	rid = id / primary key of the Relation for whom this minekey
	exists; this provides an identity for the incoming key,
	against which we can search Item tags and so forth in order to
	generate a feed.

	rvsn = relation.version for rid; this is a security check; if
	minekey.rvsn != Relation(id=rid).version then the request will
	fail; by this means you can invalidate all issued minekeys for
	a given relation without deleting it.

	iid = id / primary key of the Item which this minekey
	references; if iid == 0 then the item is the feed for the
	Relation.

	depth = integer; this is a value in the range 0..3, although
	only values 1..3 are functional.  The 'depth' field tracks how
	far a subscriber can link-chase into a mine.

	A feed URL will be iid=0 and depth=3

	Item permalinks in the feed will have iid=N and depth=2

	Links in HTML Items will be rewritten as iid=N and depth=1

	Depth=0 is legal precisely so that it can be trapped in the
	mine auditing records, but it will yield a 404
	"""

	# flush through with invalid data
	self.method = kwargs.get('method', None)
	self.rid = kwargs.get('rid', -1)
	self.rvsn = kwargs.get('rvsn', -1)
	self.iid = kwargs.get('iid', -1)
	self.depth = kwargs.get('depth', -1)

	# request data is only needed to perform permalink()
	self.__request = kwargs.get('request', None)

	# init some blank fields for caching
	self.__relation = None
	self.__item = None

	# abort immediately if still illegal
	self.validate()

    def set_request(self, request):
	"""Pokes a request into this and all descendent Minekeys, so that they can permalink()"""
	self.__request = request

    @classmethod
    def hashify(klass, x):
	"""return a b64-encoded hash of x with padding removed"""
	m = hashlib.md5()
	m.update(x)
	return b64.encode(m.digest()).rstrip('=')

    def generate_iv(self):
	"""from an iid, generate a binary IV string of the appropriate length"""

	k = '__MINE_IV_SEED__'
	iv_seed = cache.get(k)

	if not iv_seed:
	    iv_seed = Registry.get_decoded(k)
	    cache.add(k, iv_seed, 60)

	m = hashlib.md5()
	m.update(str(self.iid))
	m.update('.')
	m.update(str(self.rid))
	m.update('.')
	m.update(str(self.rvsn))
	m.update('.')
	m.update(iv_seed)
	return m.digest()

    @classmethod
    def crypto_engine(klass, iv):
	"""return an intialised crypto engine - to be modified"""

	k = '__MINE_SECRET_KEY__'
	aes_key = cache.get(k)

	if not aes_key:
	    aes_key = Registry.get_decoded(k)
	    cache.add(k, aes_key, 60)

	aes_key = Registry.get_decoded(k)
	return AES.new(aes_key, klass.aes_mode, iv)

    @classmethod
    def decrypt(klass, x, iv):
	"""decrypt x and return the result; will strip trailing whitespace padding"""
	engine = klass.crypto_engine(iv)
	return engine.decrypt(x).rstrip()

    @classmethod
    def encrypt(klass, x, iv):
	"""encrypt x and return the result prefixed by the IV; will pad
	plaintext with trailing whitespace as needed to satisfy the
	crypto algorithm"""
	l = len(x)
	if (l % 16): # if not a 16-byte message, pad with whitespace
	    y =  '%*s' % (-(((l // 16) + 1) * 16), x)
	else: # we got lucky
	    y = x
	engine = klass.crypto_engine(iv)
	return engine.encrypt(y)

    def clone(self):
	"""clone this minekey for further futzing; if you do futz manually,
	remember to do minekey.validate()"""
	retval = Minekey(method=self.method,
			 rid=self.rid,
			 rvsn=self.rvsn,
			 iid=self.iid,
			 depth=self.depth,
			 request=self.__request,
			 )
	return retval

    @classmethod
    def parse(klass, external, **kwargs):
	"""
	classmethod and pseudo-constructor; decrypt the b64-encoded
	minekey ('external') and parse it, and then validate the
	results of parsing to permit use in data access.

	throws exception on something being wrong.
	"""

	unpadded = len(external) % 4
	if unpadded:
	    external += '=' * (4-unpadded)

	blob = b64.decode(external)
	iv = blob[0:16]
	encrypted = blob[16:]
	internal = klass.decrypt(encrypted, iv)

	(Xhash, Xmethod, Xrid, Xrvsn, Xiid, Xdepth, Xkey_magic) = internal.split(',', 7)

	if Xkey_magic != klass.key_magic: # eventually switch, here
	    raise RuntimeError, 'failed magic validation'

	# Xhash computed string
	# Xmethod string
	Xrid = int(Xrid)
	Xrvsn = int(Xrvsn)
	Xiid = int(Xiid)
	Xdepth = int(Xdepth)
	# Xkey_magic constant string

	# see also __str__()
	core = klass.corefmt % (Xmethod,
			       Xrid,
			       Xrvsn,
			       Xiid,
			       Xdepth,
			       Xkey_magic)

	hash2 = klass.hashify(core)

	if Xhash != hash2:
	    raise RuntimeError, "failed hash validation"

	# note that we do not do the stupid thing and just splat
	# "**kwargs" on the end ...
	retval = Minekey(method=Xmethod,
			 rid=Xrid,
			 rvsn=Xrvsn,
			 iid=Xiid,
			 depth=Xdepth,
			 request=kwargs.get('request', None), # security
			 )
	return retval

    def __str__(self):
	"""calls validate() and then produces a string-representation of the
	minekey, including the hash-information and magic number, as
	well as the standard 5-tuple """

	self.validate()
	args = (self.method,
		self.rid,
		self.rvsn,
		self.iid,
		self.depth,
		self.key_magic, # class
		)
	c = self.corefmt % args
	h = self.hashify(c) # compute hash over core
	return "%s,%s" % (h, c)

    def key(self):
	"""takes the string representation of this minekey and produces the
	encrypted-and-base64-encoded minekey token, suitable for web
	consumption."""

	iv = self.generate_iv()
	internal = str(self)
	encrypted = self.encrypt(internal, iv)
	external = b64.encode(iv + encrypted)
	return external.rstrip('=') # padding restored by parse()

    def permalink(self):

	"""takes the result of self.key() and embeds / returns it in a
	permalink string for this mine; requires self.__request to be
	set or set_request() to have been performed on this Minekey or
	one of its ancestors"""

	link = "/get/%s" % self.key()

	if self.__request:
	    link = self.__request.build_absolute_uri(link)

	return link

    def http_path(self):
	"""returns the http://host.domain:port/ for this mine"""
	link = "/"
	if self.__request:
	    link = self.__request.build_absolute_uri(link)
	return link

    def spawn_iid(self, iid):
	"""from this minekey, spawn a new minekey object for the same
	rid/rvsn, but for a different iid, decrementing the depth."""

	retval = self.clone()
	retval.iid = iid
	retval.depth -= 1
	retval.validate() # if we futz with it, we must validate
	return retval

    def spawn_comment(self):
	"""from this minekey, spawn a new minekey object for comment submission."""

	retval = self.clone()
	retval.method = 'put'
	retval.depth = 1
	retval.validate() # if we futz with it, we must validate
	return retval

    # rewriter-regexp; the rewriter will sanitycheck balance of
    # quotation marks / that they are the same on each side

    html_re = re.compile(r"""(SRC|HREF)\s*=\s*(['"]?)/api/item/(\d+)([^\s\>]*)""", re.IGNORECASE)

    def rewrite_html(self, html):
	"""
	using the context of this minekey, rewrite the blob of HTML
	(argument) looking for case-insensitive strings of the form:

	HREF=99
	HREF='99'
	HREF="99"
	SRC=99
	SRC='99'
	SRC="99"

	...where 99 is an example iid, replacing the 99 with the
	results of self.spawn_iid(iid).permalink() - in other words a
	URL customised to retreive that item/iid with decremented
	depth.
	"""

	def rewrite_link(mo):
	    """backend link rewriter for code clarity"""
	    action = mo.group(1)
	    fq = mo.group(2)
	    iid = int(mo.group(3))
	    lq = mo.group(4)
	    if fq != lq: return mo.group(0)
	    return '%s="%s"' % (action, self.spawn_iid(iid).permalink())

	return self.html_re.sub(rewrite_link, html)

    def get_relation(self):
	""" """

	if not self.__relation:
	    try:
		self.__relation = Relation.objects.get(id=self.rid)
	    except Relation.DoesNotExist, e:
		raise RuntimeError, "minekey relation does not exist: " + str(self) + str(e)
	    if self.__relation.version != self.rvsn:
		raise RuntimeError, "minekey/relation version mismatch: " + str(self)
	return self.__relation

    def get_item(self):
	""" """

	if not self.__item:
	    try:
		self.__item = Item.objects.get(id=self.iid)
	    except Item.DoesNotExist, e:
		raise RuntimeError, "minekey item does not exist: " + str(self) + str(e)
	return self.__item

    def validate(self):
	"""
	performs basic sanity checks on this minekey:

	method must be in ('get', 'put')

	rid must not be <= 0

	rvsn must not be <= 0

	iid must not be < 0 (remember: item 0 == feed)

	depth must be in range 0..3 (remember: 0 valid but ineffectual)

	Further validation in the specific context of an actual HTTP
	request is done by the validate_against() routine.
	"""

	if self.rid <= 0:
	    raise RuntimeError, 'negative or zero rid: ' + str(self.rid)

	if self.rvsn <= 0:
	    raise RuntimeError, 'negative or zero rvsn: ' + str(self.rvsn)

	if self.iid < 0:
	    raise RuntimeError, 'negative iid: ' + str(self.iid)

	if self.depth not in (3, 2, 1, 0):
	    raise RuntimeError, 'invalid depth: ' + str(self.depth)

	if self.method not in self.valid_methods:
	    raise RuntimeError, 'bad method: ' + str(self.method)

    def validate_against(self, request, want_method):
	"""
	validate this minekey against a HTTP request (request),
	manually specifying whether you want the minekey to be a 'get'
	or a 'put' (want_method)

	this routine traps the 'depth==0' thing; this means attempts
	to walk over the mine via link-chasing get logged.

	TODO: this routine performs relation timed-embargo checking

	TODO: this routine performs global time-of-day access
	restriction checks

	this routine performs checking of self.rvsn against
	Relation(id=rid).version and raises exception on mismatch

	this routine performs relation source-IP-address checking

	this routine checks that the item (if not iid=0) is either public or shared.

	this routine performs "not:relationname" item tag checking

	"""

	# check depth
	if self.depth <= 0:
	    raise RuntimeError, "minekey has run out of depth: " + str(self)

	# check get vs put
	if self.method != want_method:
	    raise RuntimeError, "minekey is wrong method: " + str(self)

	# check global ToD restrictions
	# TODO

	# load relation
	r = self.get_relation()

	# check if deleted
	if r.is_deleted:
	    raise RuntimeError, "relation is deleted: " + str(r)

	# check against relation IP address
	if r.network_pattern:
	    if 'REMOTE_ADDR' not in request.META:
		raise RuntimeError, "relation specifies network pattern but REMOTE_ADDR unavailable: " + str(r)

	    src = request.META.get('REMOTE_ADDR')

	    # this is hardly CIDR but can be fixed later
	    if not src.startswith(r.network_pattern):
		raise RuntimeError, "relation being accessed from illegal REMOTE_ADDR: " + src

	# check ToD against relation embargo time
	if r.embargo_before:
	    pass # TODO

	if r.embargo_after:
	    pass # TODO

	# if it's a real item
	if self.iid:
	    i = self.get_item()

	    # check deleted
	    if i.is_deleted:
		raise RuntimeError, 'item is deleted'

	    # check if the item is shared/public
	    if i.status not in ('P', 'S'):
		raise RuntimeError, 'item is not marked public/shared'

	    # check if the non-feed item is marked "not:relationName"
	    if r in i.item_not_relations.all():
		raise RuntimeError, 'item is marked as forbidden to this relation'

	# ok, we're happy.

##################################################################
##################################################################
##################################################################

def r2s_string(r, rname, s):
    """
    get rname from HttpRequest r's r.POST and populate structure s
    with it; assume something else checked existence
    """

    s[rname] = r.POST[rname]

def r2s_int(r, rname, s):
    """
    get rname from HttpRequest r's r.POST and populate structure s
    with it after converting to int; assume something else checked
    existence in the first place
    """
    s[rname] = int(r.POST[rname])

def r2s_bool(r, rname, s):
    """
    get rname from HttpRequest r's r.POST and populate structure s
    with it after converting to True/False; assume something else
    checked existence in the first place
    """
    if r.POST[rname] == '':
	s[rname] = False
    else:
	s[rname] = True

##################################################################

def m2s_copy(m, mattr, s, sattr):
    """Copy mattr from m to sattr in s"""
    x = getattr(m, mattr)
    if x: s[sattr] = x

def s2m_verbatim(request, s, sattr, m, mattr):
    """Copy sattr from s to mattr in m"""
    if sattr in s: setattr(m, mattr, s[sattr])

def s2m_stripstr(request, s, sattr, m, mattr):
    """Copy sattr from s to mattr in m"""
    if sattr in s: setattr(m, mattr, s[sattr].strip())

##################################################################

def m2s_dummy(m, mattr, s, sattr):
    """m2s routine which raises an exception if it is ever invoked"""
    raise RuntimeError, 'something invoked m2s_dummy on %s and %s' % (sattr, mattr)

def s2m_dummy(request, s, sattr, m, mattr):
    """s2m routine which raises an exception if it is ever invoked"""
    raise RuntimeError, 'something invoked s2m_dummy on %s and %s' % (sattr, mattr)

##################################################################

def m2s_date(m, mattr, s, sattr):
    """Copy a DateTime from m to a isoformat string in s"""
    x = getattr(m, mattr)
    if x: s[sattr] = x.isoformat()

def s2m_date(request, s, sattr, m, mattr):
    """TBD: Copy a DateTime from an isoformat string in s, into m"""
    if sattr in s:
	raise RuntimeError, "not yet integrated the Date parser"

##################################################################

def m2s_bool(m, mattr, s, sattr):
    """Copy a boolean from m to s"""
    x = getattr(m, mattr)
    if x:
	s[sattr] = 1
    else:
	s[sattr] = 0

def s2m_bool(request, s, sattr, m, mattr):
    """Copy a boolean from s to m"""
    if sattr in s:
	if s[sattr]:
	    setattr(m, mattr, True)
	else:
	    setattr(m, mattr, False)

##################################################################

# Specialist Type Conversion - Note: Where we are writing custom
# converters we don't generally bother to use introspection because we
# know the names of the model fields.

# The 'Comment' model has an 'item' field that is a ForeignKey
# representing the item-being-commented-upon; in s-space this is
# represented as the itemId being commented upon, an integer.

def m2s_comitemid(m, mattr, s, sattr):
    """ """
    if mattr != 'item' or sattr != 'commentItemId':
	raise RuntimeError, "m2s_comitemid is confused by %s and %s" % (sattr, mattr)
    x = m.item
    if x: s[sattr] = x.id

def s2m_comitemid(request, s, sattr, m, mattr):
    """ """
    if mattr != 'item' or sattr != 'commentItemId':
	raise RuntimeError, "s2m_comitemid is confused by %s and %s" % (sattr, mattr)
    if sattr in s:
	m.item = Item.objects.get(id=s[sattr]) # ITEM LOOKUP

##################################################################

# The 'Comment' model also has a 'relation' field that is a ForeignKey
# representing the relation-submitting-the-comment; in s-space this is
# represented as the relationId, an integer

def m2s_comrelid(m, mattr, s, sattr):
    """ """
    if mattr != 'relation' or sattr != 'commentRelationId':
	raise RuntimeError, "m2s_comrelid is confused by %s and %s" % (sattr, mattr)
    x = m.relation
    if x: s[sattr] = x.id

def s2m_comrelid(request, s, sattr, m, mattr):
    """ """
    if mattr != 'relation' or sattr != 'commentRelationId':
	raise RuntimeError, "s2m_comrelid is confused by %s and %s" % (sattr, mattr)
    if sattr in s:
	if isinstance(s[sattr], int):
	    m.relation = Relation.objects.get(id=s[sattr])
	elif re.match(r'^\d+$', s[sattr]):
	    m.relation = Relation.objects.get(id=int(s[sattr]))
	else:
	    m.relation = Relation.objects.get(name=s[sattr])

##################################################################

# The 'Tag' model contains a ManyToMany field which cites the
# implications / multiple parents that any given Tag can have; in
# s-space this is represented as a space-separated string which
# contatenates tagNames.  Loops are possible, but benign.

def m2s_tagcloud(m, mattr, s, sattr):
    """ """
    if mattr != 'cloud' or sattr != 'tagCloud':
	raise RuntimeError, "m2s_tagcloud is confused by %s and %s" % (sattr, mattr)
    x = ' '.join([ x.name for x in m.cloud.all() ])
    if x: s[sattr] = x

def m2s_tagimplies(m, mattr, s, sattr):
    """ """
    if mattr != 'implies' or sattr != 'tagImplies':
	raise RuntimeError, "m2s_tagimplies is confused by %s and %s" % (sattr, mattr)
    x = ' '.join([ x.name for x in m.implies.all() ])
    if x: s[sattr] = x

def s2m_tagimplies(request, s, sattr, m, mattr):
    """ """
    if mattr != 'implies' or sattr != 'tagImplies':
	raise RuntimeError, "s2m_tagimplies is confused by %s and %s" % (sattr, mattr)
    if sattr in s:
	m.implies.clear()
	for x in s[sattr].split():
	    m.implies.add(Tag.get_or_auto_tag(request, x))

##################################################################

# itemStatus is a multi-choice field; the s-space representation of
# itemStatus ('public', 'shared', 'private') must be mapped back and
# forth to the single characters which are held in item.status

def m2s_itemstatus(m, mattr, s, sattr):
    """ """
    if mattr != 'status' or sattr != 'itemStatus':
	raise RuntimeError, "m2s_itemstatus is confused by %s and %s" % (sattr, mattr)
    x = m.get_status_display()
    if x: s[sattr] = x

def s2m_itemstatus(request, s, sattr, m, mattr):
    """ """
    if mattr != 'status' or sattr != 'itemStatus':
	raise RuntimeError, "s2m_itemstatus is confused by %s and %s" % (sattr, mattr)
    x = s[sattr]

    if x in status_lookup:
	setattr(m, mattr, status_lookup[x])
    else:
	raise RuntimeError, "s2m_itemstatus cannot remap status %s for %s and %s" % (x, sattr, mattr)

##################################################################

# itemTags is a complex tagging string: in s-space it is a
# space-separated string like "wine beer for:alice not:bob" where
# 'alice' and 'bob' are relationNames and 'wine' and 'beer' are
# tagNames; that data is parsed out and split into *three* separate
# m-space fields: m.tags, m.item_for_relations, m.item_not_relations -
# which are all ManyToMany fields.

def m2s_itemtags(m, mattr, s, sattr):
    """ """
    if mattr != 'tags' or sattr != 'itemTags':
	raise RuntimeError, "m2s_itemtags is confused by %s and %s" % (sattr, mattr)

    # i like this bit of code
    x = " ".join(x for x in itertools.chain([ i.name for i in m.tags.all() ],
					    [ "for:%s" % i.name for i in m.item_for_relations.all() ],
					    [ "not:%s" % i.name for i in m.item_not_relations.all() ]))
    if x: s[sattr] = x

def s2m_itemtags(request, s, sattr, m, mattr):
    """ """
    if mattr != 'tags' or sattr != 'itemTags':
	raise RuntimeError, "s2m_itemtags is confused by %s and %s" % (sattr, mattr)
    if sattr in s:
	m.tags.clear()
	m.item_for_relations.clear()
	m.item_not_relations.clear()
	for x in s[sattr].split():
	    if x.startswith('for:'): m.item_for_relations.add(Relation.objects.get(name=x[4:]))
	    elif x.startswith('not:'): m.item_not_relations.add(Relation.objects.get(name=x[4:]))
	    else: m.tags.add(Tag.get_or_auto_tag(request, x))

##################################################################

# relationInterests is another complex string: in s-space it is a
# space-separated string like "wine require:australia exclude:merlot"
# - the goal of which I hope is fairly clear, that a relation will
# take anything implicitly or explicitly tagged 'wine' but requires
# the 'australia' tag to be also present, rejecting anything that also
# includes the 'merlot' tag; in m-space this also breaks out into
# three fields: m.interests, m.interests_required, m.interests_excluded

def m2s_relints(m, mattr, s, sattr):
    """ """
    if mattr != 'interests' or sattr != 'relationInterests':
	raise RuntimeError, "m2s_relints is confused by %s and %s" % (sattr, mattr)

    x = " ".join(x for x in itertools.chain([ i.name for i in m.interests.all() ],
					    [ "require:%s" % i.name for i in m.interests_required.all() ],
					    [ "exclude:%s" % i.name for i in m.interests_excluded.all() ]))
    if x: s[sattr] = x

def s2m_relints(request, s, sattr, m, mattr):
    """ """
    if mattr != 'interests' or sattr != 'relationInterests':
	raise RuntimeError, "s2m_relints is confused by %s and %s" % (sattr, mattr)
    if sattr in s:
	m.interests.clear()
	m.interests_required.clear()
	m.interests_excluded.clear()
	for x in s[sattr].split():
	    if x.startswith('require:'): m.interests_required.add(Tag.get_or_auto_tag(request, x[8:]))
	    elif x.startswith('exclude:'): m.interests_excluded.add(Tag.get_or_auto_tag(request, x[8:]))
	    elif x.startswith('except:'): m.interests_excluded.add(Tag.get_or_auto_tag(request, x[7:])) # common typo
	    else: m.interests.add(Tag.get_or_auto_tag(request, x))

##################################################################
##################################################################
##################################################################

class AbstractXattr(AbstractModel):
    """
    AbstractXattr is the parent class for all extended attribute
    classes, providing the common 'key' and 'value' fields; it
    inherits from AbstractModel to obtain its model-nature
    """

    key = AbstractModelField.slug()
    value = AbstractModelField.text()

    class Meta:
	abstract = True

##################################################################
##################################################################
##################################################################

class AbstractThing(AbstractModel):
    """
    The AbstractThing class is a abstract model class that exists to
    provide a few common methods to the core Mine models.

    It's obviously easy to 'get' or 'set' the fields of a model
    instance because you can always do "m.field = foo" or something

    What we need to do is:

    1) get the svalue of a sattr that's associated with some model's
    corresponding mattr

    2) empty/nullify the mattr that corresponds with a model's sattr

    3) create or update, from information held in a HttpRequest (r-space)

    4) return an entire s-structure populated from a model

    Methods are provided below in Thing() to permit the above and then
    are inherited by most of the Mine models; for this to work there
    needs to be a small amount of linker logic to bypass major
    circular dependencies, and that's provided at the end of this
    file.
    """

    # enormous table of all sattrs and what their corresponding mattr
    # is; the model is implied by the prefix to the sattr name.  don't
    # worry about linear lookup overhead because this table gets
    # compiled into dicts for instant lookup

    # note to alec: | cts -k 5

    sattr_conversion_table = (
#  SATTR                         MATTR                       DEFER?  R2S          S2M              M2S
(  'commentItemName',            None,                       True,   None,        None,            None,            ),  #see:Comment()
(  'commentRelationName',        None,                       True,   None,        None,            None,            ),  #see:Comment()
(  'itemHasFile',                None,                       True,   None,        None,            None,            ),  #see:Item()
(  'itemSize',                   None,                       True,   None,        None,            None,            ),  #see:Item()
(  'vurlAbsoluteUrl',            None,                       True,   None,        None,            None,            ),  #see:Vurl()
(  'vurlKey',                    None,                       True,   None,        None,            None,            ),  #see:Vurl()
(  'vurlPathLong',               None,                       True,   None,        None,            None,            ),  #see:Vurl()
(  'vurlPathShort',              None,                       True,   None,        None,            None,            ),  #see:Vurl()

(  'commentIsDeleted',           'is_deleted',               False,  None,        None,            m2s_bool,        ),
(  'itemIsDeleted',              'is_deleted',               False,  None,        None,            m2s_bool,        ),
(  'relationIsDeleted',          'is_deleted',               False,  None,        None,            m2s_bool,        ),
(  'relationIsUntrusted',        'is_untrusted',             False,  None,        None,            m2s_bool,        ),
(  'tagIsDeleted',               'is_deleted',               False,  None,        None,            m2s_bool,        ),
(  'vurlIsDeleted',              'is_deleted',               False,  None,        None,            m2s_bool,        ),

(  'commentCiphertextDigest',    'ciphertext_digest',        True,   None,        None,            m2s_copy,        ),
(  'commentDigestMethod',        'digest_method',            True,   None,        None,            m2s_copy,        ),
(  'commentEncryptionKey',       'encryption_key',           True,   None,        None,            m2s_copy,        ),
(  'commentEncryptionMethod',    'encryption_method',        True,   None,        None,            m2s_copy,        ),
(  'itemCiphertextDigest',       'ciphertext_digest',        True,   None,        None,            m2s_copy,        ),
(  'itemDigestMethod',           'digest_method',            True,   None,        None,            m2s_copy,        ),
(  'itemEncryptionKey',          'encryption_key',           True,   None,        None,            m2s_copy,        ),
(  'itemEncryptionMethod',       'encryption_method',        True,   None,        None,            m2s_copy,        ),
(  'itemThumbCiphertextDigest',  'thumb_ciphertext_digest',  True,   None,        None,            m2s_copy,        ),

(  'commentCreated',             'created',                  False,  None,        None,            m2s_date,        ),
(  'commentLastModified',        'last_modified',            False,  None,        None,            m2s_date,        ),
(  'itemCreated',                'created',                  False,  None,        None,            m2s_date,        ),
(  'itemLastModified',           'last_modified',            False,  None,        None,            m2s_date,        ),
(  'relationCreated',            'created',                  False,  None,        None,            m2s_date,        ),
(  'relationLastModified',       'last_modified',            False,  None,        None,            m2s_date,        ),
(  'tagCreated',                 'created',                  False,  None,        None,            m2s_date,        ),
(  'tagLastModified',            'last_modified',            False,  None,        None,            m2s_date,        ),
(  'vurlCreated',                'created',                  False,  None,        None,            m2s_date,        ),
(  'vurlLastModified',           'last_modified',            False,  None,        None,            m2s_date,        ),

(  'tagCloud',                   'cloud',                    True,   None,        None,            m2s_tagcloud,    ),

(  'commentData',                'data',                     True,   None,        s2m_dummy,       None,            ),
(  'itemData',                   'data',                     True,   None,        s2m_dummy,       None,            ),
(  'itemThumb',                  'thumb',                    True,   None,        s2m_dummy,       None,            ),

(  'vurlIsTemporaryRedirect',    'is_temporary_redirect',    False,  r2s_bool,    s2m_bool,        m2s_bool,        ),

(  'commentItemId',              'item',                     False,  r2s_int,     s2m_comitemid,   m2s_comitemid,   ),
(  'commentId',                  'id',                       False,  r2s_int,     s2m_verbatim,    m2s_copy,        ),
(  'itemId',                     'id',                       False,  r2s_int,     s2m_verbatim,    m2s_copy,        ),
(  'relationId',                 'id',                       False,  r2s_int,     s2m_verbatim,    m2s_copy,        ),
(  'relationVersion',            'version',                  False,  r2s_int,     s2m_verbatim,    m2s_copy,        ),
(  'tagId',                      'id',                       False,  r2s_int,     s2m_verbatim,    m2s_copy,        ),
(  'thingId',                    'id',                       False,  r2s_int,     s2m_verbatim,    m2s_copy,        ),
(  'vurlId',                     'id',                       False,  r2s_int,     s2m_verbatim,    m2s_copy,        ),

(  'commentRelationId',          'relation',                 False,  r2s_string,  s2m_comrelid,    m2s_comrelid,    ),
(  'itemHideAfter',              'hide_after',               False,  r2s_string,  s2m_date,        m2s_date,        ),
(  'itemHideBefore',             'hide_before',              False,  r2s_string,  s2m_date,        m2s_date,        ),
(  'relationEmbargoAfter',       'embargo_after',            False,  r2s_string,  s2m_date,        m2s_date,        ),
(  'relationEmbargoBefore',      'embargo_before',           False,  r2s_string,  s2m_date,        m2s_date,        ),
(  'itemStatus',                 'status',                   False,  r2s_string,  s2m_itemstatus,  m2s_itemstatus,  ),
(  'itemTags',                   'tags',                     True,   r2s_string,  s2m_itemtags,    m2s_itemtags,    ),
(  'relationInterests',          'interests',                True,   r2s_string,  s2m_relints,     m2s_relints,     ),
(  'commentTitle',               'title',                    False,  r2s_string,  s2m_stripstr,    m2s_copy,        ),
(  'itemFeedLink',               'feed_link',                False,  r2s_string,  s2m_stripstr,    m2s_copy,        ),
(  'itemName',                   'name',                     False,  r2s_string,  s2m_stripstr,    m2s_copy,        ),
(  'itemThumbType',              'thumb_type',               False,  r2s_string,  s2m_stripstr,    m2s_copy,        ),
(  'itemType',                   'type',                     False,  r2s_string,  s2m_stripstr,    m2s_copy,        ),
(  'relationName',               'name',                     False,  r2s_string,  s2m_stripstr,    m2s_copy,        ),
(  'relationNetworkPattern',     'network_pattern',          False,  r2s_string,  s2m_stripstr,    m2s_copy,        ),
(  'tagName',                    'name',                     False,  r2s_string,  s2m_stripstr,    m2s_copy,        ),
(  'vurlLink',                   'link',                     False,  r2s_string,  s2m_stripstr,    m2s_copy,        ),
(  'vurlName',                   'name',                     False,  r2s_string,  s2m_stripstr,    m2s_copy,        ),
(  'tagImplies',                 'implies',                  True,   r2s_string,  s2m_tagimplies,  m2s_tagimplies,  ),
(  'commentBody',                'body',                     False,  r2s_string,  s2m_verbatim,    m2s_copy,        ),
(  'itemDescription',            'description',              False,  r2s_string,  s2m_verbatim,    m2s_copy,        ),
(  'relationDescription',        'description',              False,  r2s_string,  s2m_verbatim,    m2s_copy,        ),
(  'relationFeedConstraints',    'feed_constraints',         False,  r2s_string,  s2m_verbatim,    m2s_copy,        ),
(  'tagDescription',             'description',              False,  r2s_string,  s2m_verbatim,    m2s_copy,        ),
)

    # all these will be overridden in subclasses

    id = -1
    sattr_prefix = None
    xattr_prefix = None
    xattr_manager = None

    # IMPORTANT: see the s_classes registration code at the bottom of
    # this file; there *is* slight replication but it's unavoidable
    # since this essentially solves a linker issue. for the
    # initialisation of Thing() it is enough to have the keys in place
    # and then have the registration code populate them for runtime.

    # SUMMARY: most of the functionality of the major pymine models
    # (called "Things" in protomine) is defined here in AbstractThing;
    # we precompute all the lookup tables here as *class* information,
    # not *instance* information, because the latter has per-instance
    # overhead.  Some class attributes such as 'sattr_prefix' are
    # *set* in subclasses but are *used* here, so the s_classes table
    # is provided to lookup the appropriate class at runtime.

    # (because otherwise you hit the forward-reference problem or take
    # a massively wasteful hit with instance-data computation)

    # this will all eventually be simplified, but although arcane it
    # works surprisingly well for now; if you need to add new fields
    # to methods, you register them in the table above, and that is
    # all which is needed to get uni/bidirectional transfer between
    # Requestspace, Structurespace and Modelspace.

    s_classes = {
	'thing': None, # will be populated later
	'comment': None, # will be populated later
	'item': None, # will be populated later
	'relation': None, # will be populated later
	'tag': None, # will be populated later
	'vurl': None, # will be populated later
	}

    # these tables get used to map sattr and mattr names to the tuples
    # of how-to-convert from one to the other.

    # DEFERRAL: some s2m conversions can only take place after the
    # model has been written to the database; this is because
    # ManyToMany fields and ForeignKeys can only be created once a
    # primary key has been created for the new model; therefore some
    # translations have been flagged for "deferral", ie: a second
    # round of processing after the first m.save().  this is OK
    # because there is a rollback set up around the model-alteration
    # method in case an exception is thrown.

    # deferral is also done to get an IID for itemData filename creation

    m2s_table = {}
    s2m_table = {}
    defer_s2m_table = {}

    # table population; we shall be asking questions later.

    for prefix in s_classes.iterkeys():
	m2s_table[prefix] = {}
	s2m_table[prefix] = {}
	defer_s2m_table[prefix] = {}

    for (sattr, mattr, deferflag, r2s_func, s2m_func, m2s_func) in sattr_conversion_table:
	for prefix in s_classes.iterkeys():
	    if sattr.startswith(prefix):
		if m2s_func:
		    m2s_table[prefix][mattr] = (m2s_func, sattr)
		if s2m_func:
		    t = (r2s_func, s2m_func, mattr)
		    if deferflag:
			defer_s2m_table[prefix][sattr] = t
		    else:
			s2m_table[prefix][sattr] = t
		break # for loop
	else: # for loop; you can have a else: for a for loop in python, how cool!
	    raise RuntimeError, "unrecognised prefix in sattr_conversion: " + sattr

    @transaction.commit_on_success # <- rollback if it raises an exception
    def update_from_request(self, r, **kwargs):

	"""
	update_from_request updates a (possibly blank) instance of a
	model, with data that comes from a HttpRequest (ie: that is in
	r-space)

	it is used as a backend by new_from_request() which creates a
	blank model instance, then updates it from the request
	"""

	# build a shadow structure: useful for debug/clarity
	s = {}

	# for each target attribute
	for sattr, (r2s_func, s2m_func, mattr) in self.s2m_table[self.sattr_prefix].iteritems():

	    # first check if it is in the kwargs (override / extra)
	    # else rip the attribute out of the request and convert to python int/str
	    # else skip
	    if sattr in kwargs: s[sattr] = kwargs[sattr]
	    elif r and sattr in r.POST: r2s_func(r, sattr, s)
	    else: continue

	    # s2m the value into the appropriate attribute
	    s2m_func(r, s, sattr, self, mattr)

	# save the model
	self.save() # -> creates an id if there was not one before

	# do the deferred (post-save) initialisation
	needs_save = False

	# for each deferred target attribute
	for sattr, (r2s_func, s2m_func, mattr) in self.defer_s2m_table[self.sattr_prefix].iteritems():

	    # special case file-saving, assume <model>.save_uploaded_file() works
	    if sattr in ( 'itemData' ): # ...insert others here...
		if r and sattr in r.FILES:
		    # grab the uploaded file
		    uf = r.FILES[sattr]

		    # what does the browser call the content type?
		    ct = uf.content_type

		    # if one's not already set
		    if ct and not self.type:
			self.type = ct

		    self.save_upload_file(uf)
		    needs_save = True

	    else:
		# repeat the above logic
		if sattr in kwargs: s[sattr] = kwargs[sattr]
		elif r and sattr in r.POST: r2s_func(r, sattr, s)
		else: continue
		s2m_func(r, s, sattr, self, mattr)
		needs_save = True

	# xattr processing: grab the manager
	mgr = getattr(self, self.xattr_manager)

	# quick reusable routine
	def setxattr(k, v):
	    """ """
	    # is it an xattr?
	    if not k.startswith(self.xattr_prefix):
		return

	    # chop out the suffix
	    k = k[len(self.xattr_prefix):]

	    # get/create the xattr
	    xa, created = mgr.get_or_create(key=k, defaults={ 'value': v })

	    if not created: # then it needs updating
		xa.value = v
		xa.save()

	# if we have a request, scan the request environment for xattrs
	if r:
	    for k, v in r.POST.iteritems():
		setxattr(k, v)

	# update xattrs from kwargs
	for k, v in kwargs.iteritems():
	    setxattr(k, v)

	# update if we did anything requiring the model to change
	if needs_save:
	    self.save()

	# return it
	return self

    @classmethod # <- new_from_request is an alternative constructor, ergo: classmethod
    def new_from_request(klass, r, **kwargs):
	""" """
	instantiator = klass.s_classes[klass.sattr_prefix]
	margs = {}
	m = instantiator(**margs)
	return m.update_from_request(r, **kwargs)

    # looking up a mattr from a sattr is tedious since it has to be
    # done in two places; this wraps that for convenience

    def lookup_mattr(self, sattr):
	""" """
	if sattr in self.s2m_table[self.sattr_prefix]:
	    t = self.s2m_table[self.sattr_prefix][sattr]
	elif sattr in self.defer_s2m_table[self.sattr_prefix]:
	    t = self.defer_s2m_table[self.sattr_prefix][sattr]
	else:
	    raise RuntimeError, "lookup_mattr cannot lookup: " + sattr
	return t

    # get_sattr and delete_sattr methods: supporting
    # /api/relation/42/relationName.json and similar methods.

    def get_sattr(self, sattr):
	""" """
	if sattr.startswith(self.xattr_prefix):

	    # chop out the suffix
	    k = sattr[len(self.xattr_prefix):]

	    # grab the manager
	    mgr = getattr(self, self.xattr_manager)

	    # lookup the xattr and return it
	    xa = mgr.get(key=k)
	    return xa.value

	# check validity of sattr
	elif sattr.startswith(self.sattr_prefix):

	    # lookup equivalent model field
	    r2s_func, s2m_func, mattr = self.lookup_mattr(sattr)

	    # lookup m2s conversion routine
	    m2s_func, sattr2 = self.m2s_table[self.sattr_prefix][mattr]

	    # sanity check
	    assert sattr == sattr2, "m2s_table corruption, reverse lookup yielded wrong result"

	    # convert to s-form and return
	    s = {}
	    m2s_func(self, mattr, s, sattr)
	    return s[sattr]

	else:
	    raise RuntimeError, "get_sattr asked to look up bogus sattr: " + sattr

    @transaction.commit_on_success # <- rollback if it raises an exception
    def delete_sattr(self, sattr):
	""" """
	if sattr.startswith(self.xattr_prefix):
	    # lookup equivalent model field
	    k = sattr[len(self.xattr_prefix):]
	    # grab the manager
	    mgr = getattr(self, self.xattr_manager)
	    # lookup the xattr and delete it
	    xa = mgr.get(key=k)
	    xa.delete()

	elif sattr.startswith(self.sattr_prefix):
	    # lookup equivalent model field
	    r2s_func, s2m_func, mattr = self.lookup_mattr(sattr)
	    # zero that field
	    setattr(self, sattr, None) ############## FIX THIS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
	    raise RuntimeException, "this method of deletion does not work"
	    # try saving and hope model will bitch if something is wrong
	    self.save()

	else:
	    raise RuntimeError, "get_sattr asked to look up bogus sattr: " + sattr

    # render a model into a structure suitable for serializing and
    # returning to the user.

    def to_structure(self):
	""" """

	s = {}

	for mattr, (m2s_func, sattr) in self.m2s_table[self.sattr_prefix].iteritems():
	    m2s_func(self, mattr, s, sattr)

	mgr = getattr(self, self.xattr_manager)

	for xa in mgr.all():
	    k = '%s%s' % (self.xattr_prefix, xa.key)
	    v = xa.value
	    s[k] = v

	return s

    def get_absolute_url(self):
	""" """
	fmt = 'raw' # TBD
	return '/api/%s/%d.%s' % (self.sattr_prefix, self.id, fmt)

    @classmethod
    def filter_queryset(klass, qs, query):
	return qs

    # continuing the chain of inheritance
    class Meta:
	abstract = True

##################################################################
##################################################################
##################################################################

class TagXattr(AbstractXattr):
    """tag extended attributes"""

    tag = AbstractModelField.reference('Tag')

    class Meta:
	ordering = ['key']
	# order_with_respect_to = 'tag'
	unique_together = ('tag', 'key')
	verbose_name = 'TagXattr'

    def __unicode__(self):
	return self.key

##################################################################
##################################################################
##################################################################

class Tag(AbstractThing):
    """This is the modelspace representation of the Tag object"""

    sattr_prefix = "tag"

    name = AbstractModelField.slug(unique=True)

    description = AbstractModelField.text(required=False)

    implies = AbstractModelField.reflist('self', symmetrical=False, pivot='implied_by', required=False)

    cloud = AbstractModelField.reflist('self', symmetrical=False, pivot='clouded_by', required=False)

    class Meta:
	ordering = ['name']

    def __unicode__(self):
	return self.name

    def __update_cloud_field(self):
	""" """

	# wipe our cloud cache
	self.cloud.clear()

	# get us into the processing loop
	tgraph = { self: False }
	loop = True

	# until we make a pass thru tgraph where nothing happens
	while loop:

	    # default: we won't go round again
	    loop = False

	    # for each tag in tgraph
	    for tag, visited in tgraph.items():

		# if we've already exploded it, skip to next
		if visited:
		    continue

		# register all the unvisited parents into tgraph
		for parent in tag.implies.all():
		    if not tgraph.get(parent, False):
			tgraph[parent] = False
			loop = True # mark more work to be done

		# add this tag to the cloud
		self.cloud.add(tag)

		# mark current tag as 'visited'
		tgraph[tag] = True

	self.save() # needed?

    def __update_cloud_graph(self, tgraph):
	"""
	I could try ripping out the list of tags just once (avoiding
	~n! database hits) and reconstructing the graph from that, but
	if they change on disk underneath me then something nasty can
	happen; better to let caching at a lower level take the hit...
	"""

	# update all the tags with this data
	for tag in tgraph.keys():
	    tag = Tag.objects.get(id=tag.id) # potentially dirty, reload
	    tag.__update_cloud_field()

    def __expand_cloud_graph(self):
	"""
	This is brute-force and ignorance code but it is proof against loops.
	"""

	tgraph = { self: False }

	if not self.id:
	    return tgraph # we are not yet in the database

	loop = True # get us into the processing loop

	while loop:
	    loop = False

	    for tag, visited in tgraph.items():
		if visited:
		    continue

		for parent in tag.implies.all():
		    if not tgraph.get(parent, False):
			tgraph[parent] = False
			loop = True

		for child in tag.implied_by.all():
		    if not tgraph.get(child, False):
			tgraph[child] = False
			loop = True

		tgraph[tag] = True

	return tgraph

    @transaction.commit_on_success # <- rollback if it raises an exception
    def delete_sattr(self, sattr):
	"""
	This method overrides AbstractThing.delete_sattr() and acts as
	a hook to detect changes in the Tag implications that might
	trigger a recalculation of the Tag cloud.
	"""

	if sattr == 'tagImplies':
	    tgraph = self.__expand_cloud_graph()
	else:
	    tgraph = None

	super(Tag, self).delete_sattr(sattr)

	if tgraph:
	    self.__update_cloud_graph(tgraph)

    @transaction.commit_on_success # <- rollback if it raises an exception
    def update_from_request(self, r, **kwargs):
	"""
	This method overrides AbstractThing.update_from_request() and
	acts as a hook to detect changes in the Tag implications that
	might trigger a recalculation of the Tag cloud.

	There is a performance impact here which needs to be
	considered; we *ought* to determine whether something has
	changed that would require the cloud to be recomputed; but
	maybe slightly overzealous refreshing will be good for a
	while... having flushed out a bug where an Item with no
	implications was not clouding itself, the simplicity of just
	recomputing every time is attractive, especially with the
	likely shallow hierarchies of implication, if any at all...

	"""

	tgraph = self.__expand_cloud_graph()

	retval = super(Tag, self).update_from_request(r, **kwargs)

	self.__update_cloud_graph(tgraph)

	retval = Tag.objects.get(id=retval.id) # reload, possibly dirty

	return retval

    @classmethod
    def get_or_auto_tag(klass, request, name):
	if 'auto_tag' in request.POST and request.POST['auto_tag']:
	    t, created = Tag.objects.get_or_create(name=name, defaults={})

	    if created:
		tgraph = t.__expand_cloud_graph()
		t.__update_cloud_graph(tgraph)
		t.save()
	else:
	    t = Tag.objects.get(name=name)
	return t

    @classmethod
    def filter_queryset(klass, qs, query):
	for word in query.split():
	    qs = qs.filter(Q(name__icontains=word) |
			   Q(description__icontains=word))
	return qs

##################################################################
##################################################################
##################################################################

class RelationXattr(AbstractXattr):
    """relation extended attributes"""

    relation = AbstractModelField.reference('Relation')

    class Meta:
	ordering = ['key']
	# order_with_respect_to = 'relation'
	unique_together = ('relation', 'key')
	verbose_name = 'RelationXattr'

    def __unicode__(self):
	return self.key

##################################################################
##################################################################
##################################################################

class Relation(AbstractThing):
    """This is the modelspace representation of the Relation object"""

    sattr_prefix = "relation"

    name = AbstractModelField.slug(unique=True)

    version = AbstractModelField.integer(1)

    description = AbstractModelField.text(required=False)

    embargo_after = AbstractModelField.datetime(required=False)
    embargo_before = AbstractModelField.datetime(required=False)

    interests = AbstractModelField.reflist(Tag, pivot='relations_with_tag', required=False)
    interests_excluded = AbstractModelField.reflist(Tag, pivot='relations_excluding', required=False)
    interests_required = AbstractModelField.reflist(Tag, pivot='relations_requiring', required=False)

    network_pattern = AbstractModelField.string(required=False)

    feed_constraints = AbstractModelField.string(required=False)
    is_untrusted = AbstractModelField.bool(False)

    class Meta:
	ordering = ['name']

    def __unicode__(self):
	return self.name

    def feed_minekey(self, **kwargs):
	""" """
	retval = Minekey(method='get',
			 rid=self.id,
			 rvsn=self.version,
			 iid=0,
			 depth=3,
			 request=kwargs.get('request', None),
			 )
	return retval

    # TBD: GET A REQUEST INTO HERE IN ORDER TO POPULATE FEED_MINEKEY WITH IT?
    def to_structure(self):
	"""
	Splices virtual sattrs into the Relation structure
	"""

	s = super(Relation, self).to_structure()
	s['relationFeedUrl'] = self.feed_minekey().permalink()

	return s

    @classmethod
    def filter_queryset(klass, qs, query):
	for word in query.split():
	    qs = qs.filter(Q(name__icontains=word) |
			   Q(description__icontains=word))
	return qs

##################################################################
##################################################################
##################################################################

class ItemXattr(AbstractXattr):
    """item extended attributes"""

    item = AbstractModelField.reference('Item')

    class Meta:
	ordering = ['key']
	# order_with_respect_to = 'item'
	unique_together = ('item', 'key')
	verbose_name = 'ItemXattr'

    def __unicode__(self):
	return self.key

##################################################################
##################################################################
##################################################################

class Item(AbstractThing):
    """This is the modelspace representation of the Item object"""

    sattr_prefix = "item"

    name = AbstractModelField.string()
    status = AbstractModelField.choice(item_status_choices) # WHY IS THIS NOT CHECKED ON SAVE()? TBD
    description = AbstractModelField.text(required=False)

    hide_after = AbstractModelField.datetime(required=False)
    hide_before = AbstractModelField.datetime(required=False)

    tags = AbstractModelField.reflist(Tag, pivot='items_tagged', required=False)
    item_for_relations = AbstractModelField.reflist(Relation, pivot='items_explicitly_for', required=False)
    item_not_relations = AbstractModelField.reflist(Relation, pivot='items_explicitly_not', required=False)

    feed_link = AbstractModelField.url(required=False)

    data = AbstractModelField.file(storage=item_fss, upload_to=fss_yyyymmdd, required=False)
    type = AbstractModelField.string(required=False)
    encryption_method = AbstractModelField.text(required=False)
    encryption_key = AbstractModelField.text(required=False)
    digest_method = AbstractModelField.text(required=False)
    ciphertext_digest = AbstractModelField.text(required=False)

    thumb = AbstractModelField.file(storage=thumb_fss, upload_to=fss_yyyymmdd, required=False) # FOR ONCE CAN WE ASSUME PNG?
    thumb_type = AbstractModelField.string(required=False)
    thumb_ciphertext_digest = AbstractModelField.text(required=False)

    class Meta:
	ordering = ['-last_modified']

    def __unicode__(self):
	return self.name

    def save_upload_file(self, f):
	"""tries to save the uploaded file for later access"""

	if not self.id:
	    raise RuntimeError, "save_upload_file trying to save a model which has no IID"

	name = str(self.id) + '.' + f.name
	self.data.save(name, f)

    def item_size(self):
	"""
	returns the size of the data file; if there is no file,
	returns the size of self.description, or zero
	"""

	if self.data:
	    return self.data.size
	elif self.description:
	    return len(self.description)
	else:
	    return 0

    def item_type(self):
	"""
	if there is a declared item.type, it is returned;
	else if there is a data file, return 'application/octet-stream';
	else return 'text/html' and assume the description is HTML
	"""

	if self.type:
	    return self.type
	elif self.data:
	    return 'application/octet-stream'
	else:
	    return 'text/html'

    def item_feed_description(self):
	"""
	if there is a data file, the description *is* HTML and is returned,
	else if self.item_type() suggests HTML, the description is returned,
	else a hardcoded default is returned
	"""

	if self.data:
	    return self.description
	elif self.item_type() == 'text/html': # if we think it's HTML
	    return self.description
	else:
	    return 'pymine: no datafile is provided and the description content is not text/html, thus this placeholder is used instead'

    def to_structure(self):
	"""Splices the virtual itemSize sattr into the Item structure"""

	s = super(Item, self).to_structure()
	s['itemType'] = self.item_type() # overrides based on whether item.data is None
	s['itemSize'] = self.item_size()

	if self.data:
	    s['itemHasFile'] = 1
	else:
	    s['itemHasFile'] = 0

	return s

    def to_atom(self, feed_mk, relation):
	"""
	Creates the structure used in ATOM generation

	See http://docs.djangoproject.com/en/dev/ref/contrib/syndication/#django.contrib.syndication.SyndicationFeed.add_item
	"""

	# faster to import this as it carries a lot of cached data
	if not relation:
	    relation = Relation.objects.get(id=feed_mk.rid)

	# check
	if feed_mk.rid != relation.id:
	    raise RuntimeError, 'mismatch between argument rids: %d vs %d' % (feed_mk.rid, relation.id)

	item_mk = feed_mk.spawn_iid(self.id)

	iteminfo = {}

	iteminfo['author_email'] = 'nobody-item@themineproject.org' # tbd: fix this
	iteminfo['author_link'] = None # TBD?
	iteminfo['author_name'] = iteminfo['author_email']
	iteminfo['categories'] = None # TBD?
	iteminfo['comments'] = None # TBD?
	iteminfo['item_copyright'] = None # TBD?
	iteminfo['pubdate'] = self.last_modified
	iteminfo['ttl'] = None # TBD?
	iteminfo['unique_id'] = "tag:%s,2009:%s" % (iteminfo['author_email'], item_mk.key())
	iteminfo['title'] = self.name

	# TBD: what to do about size and content-type for enclosures?

	# TBD: what to do about size and content-type for third-party linkage?

	if self.feed_link:
	    iteminfo['link'] = self.feed_link
	else:
	    iteminfo['link'] = item_mk.permalink()

	# work out our enclosure

	# tbd: truncate the url down to a fake filename + valid
	# extension, and check that it makes any sense at all; ie:
	# fake up a replacement or self.file.name and use here and
	# below?

	if self.data:
	    fake_filename = self.data.name
	else:
	    fake_filename = 'enclosure.bin'

	iteminfo['enclosure'] = \
	    feedgenerator.Enclosure(url='%s/%s' % (iteminfo['link'], fake_filename),
				    length=str(self.item_size()),
				    mime_type=self.item_type())

	# work out our description

	# if there is no data and we are of HTML type
	if False: # not self.data and self.item_type() == 'text/html':
	    desc = self.item_feed_description()
	else: # either there is data, or we are not of HTML type
	    tmpl = {
		'comment_url': item_mk.spawn_comment().permalink(),
		'content_type': self.item_type(),
		'description': self.item_feed_description(),
		'has_file': 0,
		'filename': fake_filename,
		'http_path': item_mk.http_path(),
		'id': self.id,
		'link': iteminfo['link'],
		'size': self.item_size(),
		'title': iteminfo['title'],
		'type': self.item_type(),
		}
	    if self.data:
		tmpl['has_file'] = 1
	    desc = render_to_string('feed/item-description.html', tmpl)

	# rewrite
	iteminfo['description'] = item_mk.rewrite_html(desc)

	# done
	return iteminfo

    @classmethod
    def filter_queryset(klass, qs, query):
	for word in query.split():
	    qs = qs.filter(Q(name__icontains=word) |
			   Q(description__icontains=word))
	return qs

##################################################################
##################################################################
##################################################################

class CommentXattr(AbstractXattr):
    """comment extended attributes"""

    comment = AbstractModelField.reference('Comment')

    class Meta:
	ordering = ['key']
	# order_with_respect_to = 'comment'
	unique_together = ('comment', 'key')
	verbose_name = 'CommentXattr'

    def __unicode__(self):
	return self.key

##################################################################
##################################################################
##################################################################

class Comment(AbstractThing):
    """This is the modelspace representation of the Comment object"""

    sattr_prefix = "comment"

    title = AbstractModelField.string()

    body = AbstractModelField.text(required=False)

    # required=False to permit comments by mine owner
    relation = AbstractModelField.reference(Relation, required=False)

    # required=False to permit comments on feed where IID=0
    item = AbstractModelField.reference(Item, required=False)

    # to permit relation uploads, so long as relation.is_untrusted == false
    data = AbstractModelField.file(storage=comment_fss, upload_to=fss_yyyymmdd, required=False)

    # crypto
    encryption_method = AbstractModelField.text(required=False)
    encryption_key = AbstractModelField.text(required=False)
    digest_method = AbstractModelField.text(required=False)
    ciphertext_digest = AbstractModelField.text(required=False)

    def __unicode__(self):
	return self.title

    def to_structure(self):
	"""Splices the textual commentRelationName sattr into the Item structure"""

	s = super(Comment, self).to_structure()
	s['commentRelationName'] = self.relation.name
	s['commentItemName'] = self.item.name
	return s

    @classmethod
    def filter_queryset(klass, qs, query):
	for word in query.split():
	    qs = qs.filter(Q(title__icontains=word) |
			   Q(body__icontains=word))
	return qs

    class Meta:
	ordering = ['-id']

##################################################################
##################################################################
##################################################################

class VurlXattr(AbstractXattr):
    """vurl extended attributes"""

    vurl = AbstractModelField.reference('Vurl')

    class Meta:
	ordering = ['key']
	# order_with_respect_to = 'vurl'
	unique_together = ('vurl', 'key')
	verbose_name = 'VurlXattr'

    def __unicode__(self):
	return self.key

##################################################################
##################################################################
##################################################################

class Vurl(AbstractThing):

    """The Vurl (Vanity URL) model implements URL-shortening and
    remapping, allowing arbitrary cookies to map to much longer URLs,
    indexable by table-id, "key" (table-id encoded under base58) and
    "name", which provides for much elective, longer token names to be
    used"""

    sattr_prefix = "vurl"

    name = AbstractModelField.slug(unique=True)
    link = AbstractModelField.text(unique=True)
    is_temporary_redirect = AbstractModelField.bool(False)

    def __unicode__(self):
	return self.name

    class Meta:
	ordering = ['-id']

    @staticmethod
    def get_with_vurlkey(encoded):
	""" """
	return Vurl.objects.get(id=b58.b58decode(encoded))

    @transaction.commit_on_success # <- rollback if it raises an exception
    def save(self):
	""" """

	redo = False

	if not self.name:
	    redo = True
	    self.name = '__%s__' % 'temporary_random_string' # TBD FIX THIS !!!!!!!!!!!!!!!!

	s = super(Vurl, self).save()

	if redo:
	    self.name = 'vurl_%s' % self.vurlkey()
	    s = super(Vurl, self).save()

    def vurlkey(self):
	""" """
	return b58.b58encode(self.id)

    def to_structure(self):
	"""
	Splices the virtual vurlKey/vurlPath sattrs into the Vurl
	structure; since m2s_foo above only allows for a single mattr
	to map to a single sattr, and since vurl.id is bound to
	vurlId, and since vurlKey is a restatement of vurl.id in
	base58, and since the vurlId is permanent and readonly, we
	have no real option but to kludge this right here as duplicate
	information.
	"""

	vk = self.vurlkey()
	s = super(Vurl, self).to_structure()
	s['vurlKey'] = vk
	s['vurlPathShort'] = "/get/k/%s" % vk
	s['vurlPathLong'] =  "/get/n/%s" % self.name
	return s

    def http_response(self):
	if self.is_temporary_redirect:
	    return HttpResponseRedirect(self.link)
	else:
	    return HttpResponsePermanentRedirect(self.link)

    @classmethod
    def filter_queryset(klass, qs, query):
	for word in query.split():
	    qs = qs.filter(Q(link__icontains=word) |
			   Q(name__icontains=word))
	return qs

##################################################################
##################################################################
##################################################################

class LogEvent(AbstractModel):
    """key/value pairs for Mine configuration"""

    logevent_status_choices = (
	( 'o', 'open' ),
	( 'u', 'updated' ),
	( 'c', 'closed' ),
	( 'e', 'error' ),
	( 'm', 'message' ),
	( 'f', 'fatal' ),
	( 'x', 'corrupted' ),
	)

    status = AbstractModelField.choice(logevent_status_choices)
    type = AbstractModelField.string(required=False)
    msg = AbstractModelField.text(required=False)
    ip = AbstractModelField.string(required=False)
    method = AbstractModelField.string(required=False)
    path = AbstractModelField.string(required=False)
    key = AbstractModelField.string(required=False)
    item = AbstractModelField.reference(Item, required=False)
    relation = AbstractModelField.reference(Relation, required=False)

    # various faux-constructors that do not return the object

    @classmethod
    def __selfcontained(klass, status, type, *args, **kwargs):
	""" """

	m = " ".join(args)
	el = LogEvent(status=status, type=type, msg=m, **kwargs)
	el.save()

    @classmethod
    def message(klass, type, *args, **kwargs):
	""" """

	klass.__selfcontained('m', type, *args, **kwargs)

    @classmethod
    def error(klass, type, *args, **kwargs):
	""" """

	klass.__selfcontained('e', type, *args, **kwargs)

    @classmethod
    def fatal(klass, type, *args, **kwargs):
	""" """

	klass.__selfcontained('f', type, *args, **kwargs)
	raise RuntimeError, klass.msg # set as side effect

    # next three work together; open-update-close/_error

    @classmethod
    def open(klass, type, **kwargs):
	""" """

	el = LogEvent(status='o', type=type, **kwargs)
	el.save()
	return el

    def update(self, *args):
	""" """

	self.msg = " ".join(args)
	self.status = 'u'
	self.save()

    def __close_status(self, status, *args):
	""" """

	if self.status in 'ou': # legitimate to close
	    self.msg = " ".join(args)
	    self.status = status
	else: # risk of infinite recursion if exception thrown
	    # leave msg alone
	    self.status = 'x'
	self.save()

    def close(self, *args):
	""" """

	self.__close_status('c', *args)

    def close_error(self, *args):
	""" """

	self.__close_status('e', *args)

    def to_structure(self):
	""" """

	s = {}
	s['eventStatus'] = self.status
	if self.type: s['eventType'] = self.type
	if self.msg: s['eventMessage'] = self.msg
	if self.ip: s['eventIPAddress'] = self.ip
	if self.method: s['eventMethod'] = self.method
	if self.path: s['eventPath'] = self.path
	if self.key: s['eventKey'] = self.key
	s['eventCreated'] = m2s_date(self.created)
	s['eventLastModified'] = m2s_date(self.last_modified)
	return s

    class Meta:
	ordering = ['-last_modified']
	verbose_name = 'Event'

    def __unicode__(self):
	return self.get_status_display()

##################################################################
##################################################################
##################################################################

# This is a CRITICAL bit of code which registers all thing-classes
# back with the parent AbstractThing class, and populates the other
# Thing-specific fields...

for thing in (Comment, Item, Relation, Tag, Vurl):
    AbstractThing.s_classes[thing.sattr_prefix] = thing
    thing.xattr_prefix = '__' + thing.sattr_prefix
    thing.xattr_manager = thing.sattr_prefix + 'xattr_set'

##################################################################
##################################################################
##################################################################
