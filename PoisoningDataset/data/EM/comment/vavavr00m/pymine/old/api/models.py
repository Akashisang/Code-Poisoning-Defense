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
