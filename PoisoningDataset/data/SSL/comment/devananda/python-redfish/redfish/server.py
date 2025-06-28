# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


"""
STARTING ASSUMPTIONS

On URIs:

The Redfish RESTful API is a "hypermedia API" by design.  This is to avoid
building in restrictive assumptions to the data model that will make it
difficult to adapt to future hardware implementations.  A hypermedia API avoids
these assumptions by making the data model discoverable via links between
resources.

A URI should be treated by the client as opaque, and thus should not be
attempted to be understood or deconstructed by the client.  Only specific top
level URIs (any URI in this sample code) may be assumed, and even these may be
absent based upon the implementation (e.g. there might be no /redfish/v1/Systems
collection on something that doesn't have compute nodes.)

The other URIs must be discovered dynamically by following href links.  This is
because the API will eventually be implemented on a system that breaks any
existing data model "shape" assumptions we may make now.  In particular,
clients should not make assumptions about the URIs for the resource members of
a collection.  For instance, the URI of a collection member will NOT always be
/redfish/v1/.../collection/1, or 2.  On systems with multiple compute nodes per
manager, a System collection member might be /redfish/v1/Systems/C1N1.

This sounds very complicated, but in reality (as these examples demonstrate),
if you are looking for specific items, the traversal logic isn't too
complicated.

On Resource Model Traversal:

Although the resources in the data model are linked together, because of cross
link references between resources, a client may not assume the resource model
is a tree.  It is a graph instead, so any crawl of the data model should keep
track of visited resources to avoid an infinite traversal loop.

A reference to another resource is any property called "href" no matter where
it occurs in a resource.

An external reference to a resource outside the data model is referred to by a
property called "extref".  Any resource referred to by extref should not be
assumed to follow the conventions of the API.

On Resource Versions:

Each resource has a "Type" property with a value of the format Tyepname.x.y.z
where
* x = major version - incrementing this is a breaking change to the schema y =
* minor version - incrementing this is a non-breaking additive change to the
* schema z = errata - non-breaking change

Because all resources are versioned and schema also have a version, it is
possible to design rules for "nearest" match (e.g. if you are interacting with
multiple services using a common batch of schema files).  The mechanism is not
prescribed, but a client should be prepared to encounter both older and newer
versions of resource types.

On HTTP POST to create:

WHen POSTing to create a resource (e.g. create an account or session) the
guarantee is that a successful response includes a "Location" HTTP header
indicating the resource URI of the newly created resource.  The POST may also
include a representation of the newly created object in a JSON response body
but may not.  Do not assume the response body, but test it.  It may also be an
ExtendedError object.

HTTP REDIRECT:

All clients must correctly handle HTTP redirect.  We (or Redfish) may
eventually need to use redirection as a way to alias portions of the data
model.

FUTURE:  Asynchronous tasks

In the future some operations may start asynchonous tasks.  In this case, the
client should recognized and handle HTTP 202 if needed and the 'Location'
header will point to a resource with task information and status.

JSON-SCHEMA:

The json-schema available at /redfish/v1/Schemas governs the content of the
resources, but keep in mind:
* not every property in the schema is implemented in every implementation.
* some properties are schemed to allow both null and anotehr type like string
* or integer.

Robust client code should check both the existence and type of interesting
properties and fail gracefully if expectations are not met.

GENERAL ADVICE:

Clients should always be prepared for:
* unimplemented properties (e.g. a property doesn't apply in a particular case)
* null values in some cases if the value of a property is not currently known
* due to system conditions HTTP status codes other than 200 OK.  Can your code
* handle an HTTP 500 Internal Server Error with no other info?  URIs are case
* insensitive HTTP header names are case insensitive JSON Properties and Enum
* values are case sensitive A client should be tolerant of any set of HTTP
* headers the service returns

"""
