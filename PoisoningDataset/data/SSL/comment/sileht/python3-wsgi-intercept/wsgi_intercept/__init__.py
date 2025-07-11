
"""installs a WSGI application in place of a real URI for testing.

Introduction
============

Testing a WSGI application normally involves starting a server at a
local host and port, then pointing your test code to that address.
Instead, this library lets you intercept calls to any specific host/port
combination and redirect them into a `WSGI application`_ importable by
your test program. Thus, you can avoid spawning multiple processes or
threads to test your Web app.

How Does It Work?
=================

``wsgi_intercept`` works by replacing ``httplib.HTTPConnection`` with a
subclass, ``wsgi_intercept.WSGI_HTTPConnection``. This class then
redirects specific server/port combinations into a WSGI application by
emulating a socket. If no intercept is registered for the host and port
requested, those requests are passed on to the standard handler.

The functions ``add_wsgi_intercept(host, port, app_create_fn,
script_name='')`` and ``remove_wsgi_intercept(host,port)`` specify
which URLs should be redirect into what applications. Note especially
that ``app_create_fn`` is a *function object* returning a WSGI
application; ``script_name`` becomes ``SCRIPT_NAME`` in the WSGI app's
environment, if set.

Install
=======

::

    pip install -U wsgi_intercept

Packages Intercepted
====================

Unfortunately each of the Web testing frameworks uses its own specific
mechanism for making HTTP call-outs, so individual implementations are
needed. At this time there are implementations for ``httplib2`` and
``requests`` in both Python 2 and 3, ``urllib2`` and ``httplib``
in Python 2 and ``urllib.request`` and ``http.client`` in Python 3.

If you are using Python 2 and need support for a different HTTP
client, require a version of ``wsgi_intercept<0.6``. Earlier versions
include support for ``webtest``, ``webunit`` and ``zope.testbrowser``.
It is quite likely that support for these versions will be relatively
easy to add back in to the new version.

The best way to figure out how to use interception is to inspect
`the tests`_. More comprehensive documentation available upon
request.

.. _the tests: https://github.com/cdent/python3-wsgi-intercept/tree/master/test


History
=======

Pursuant to Ian Bicking's `"best Web testing framework"`_ post, Titus
Brown put together an `in-process HTTP-to-WSGI interception mechanism`_
for his own Web testing system, twill_. Because the mechanism is pretty
generic -- it works at the httplib level -- Titus decided to try adding
it into all of the *other* Python Web testing frameworks.

The Python 2 version of wsgi-intercept was the result. Kumar McMillan
later took over maintenance.

The current version works with Python 2.6, 2.7, 3.3 and 3.4 and was assembled
by `Chris Dent`_. Testing and documentation improvements from `Sasha Hart`_.

.. _twill: http://www.idyll.org/~t/www-tools/twill.html
.. _"best Web testing framework": http://blog.ianbicking.org/best-of-the-web-app-test-frameworks.html
.. _in-process HTTP-to-WSGI interception mechanism: http://www.advogato.org/person/titus/diary.html?start=119
.. _WSGI application: http://www.python.org/peps/pep-3333.html
.. _Chris Dent: https://github.com/cdent
.. _Sasha Hart: https://github.com/sashahart

Project Home
============

This project lives on `GitHub`_. Please submit all bugs, patches,
failing tests, et cetera using the Issue Tracker.

Additional documentation is available on `Read The Docs`_.

.. _GitHub: http://github.com/cdent/python3-wsgi-intercept
.. _Read The Docs: http://wsgi-intercept.readthedocs.org/en/latest/

"""