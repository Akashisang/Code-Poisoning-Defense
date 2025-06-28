# -*- coding: utf-8 -*-
#  Copyright (C) 2014 Jump Operations, LLC
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to:
#    Free Software Foundation, Inc.
#    51 Franklin Street, Fifth Floor
#    Boston, MA  02110-1301, USA.

"""Session management for Python AtTask API module.
"""

from requests_ntlm import HttpNtlmAuth
import ssl
import requests
import os
import cookielib
from bs4 import BeautifulSoup as bs

from pyattask.exceptions import (
    NoSession,
    GetHTTPError,
    AuthenticationError,
)

import logging
log = logging.getLogger(__name__)


# Pick a generic endpoint to test the API. This is something that is guaranteed
# to return a 200
authtest_endpoint = "/project/count?status=CUR"
_CURRENT_SESSION = None


def create_session(url, forcetlsone=False):
    """Initialize the global AtTask API session.

    Args:
      url (text): URL for the API (with version strings)
      forcetlsone (bool): Force the session to TLS1 (default: False)

    Returns:
      None
    """

    global _CURRENT_SESSION
    _CURRENT_SESSION = AtTaskSession(url, forcetlsone)


def get_session():
    """Return the current active session.

    Returns:
      AtTaskSession
    """
    if _CURRENT_SESSION is None:
        raise NoSession("Session Uninitialized")
    else:
        return _CURRENT_SESSION


class AtTaskSession(object):
    """An object representing an AtTask session"""

    _userid = None
    _url = None
    _session = None

    def __init__(self, url, forcetlsone=False):
        """Initialize the AtTaskSession object

        Args:
          url (str): The URL to the AtTask API instance
          forcetlsone (bool, optional): force a TLS1 session. Defaults to False
        """

        self._url = url
        self._baseurl = url.split('attask/api')[0]
        self._session = self._get_new_requestsession(forcetlsone)
        log.debug(self._session)

    def __repr__(self):
        if self.is_authenticated():
            authstate = "Authenticated"
        else:
            authstate = "NOT Authenticated"
        return "<AtTaskSession ({}, url=\"{}\")>".format(authstate, self._url)

    @property
    def url(self):
        """Return url.

        Returns:
          url (str): session url
        """
        return self._url

    @property
    def userid(self):
        """Return pyattask userid

        Returns:
          userid (str): pyattask userId
        """
        return self._userid

    @staticmethod
    def _get_new_requestsession(forcetlsone=True, filename='.pyattask_cookiejar'):
        """Return properly prepared requests.Session() object

        Args:
          forcetlsone (bool): Force TLS1 session if True.
            Some site-local SSL interceptors break non-TLS1 SSL, we get a
            requests.Session object, mount the TLS1 adapter to handle https,
            and return the Session object
          filename (str, optional): The filename relative to $HOME. Defaults to
            ".pyattask_cookiejar"

        Returns:
          requests.Session

        TODO(davidr): probably change forcetlsone to default to False
        """

        session = requests.Session()
        if forcetlsone:
            from requests.adapters import HTTPAdapter
            from requests.packages.urllib3.poolmanager import PoolManager

            class TLS1Adapter(HTTPAdapter):
                """Create an HTTPAdapter for TLS1.

                Something about the SSL interceptor is breaking non TLS1
                sessions.  The requests.Session is bound to use this class for
                https connections.
                """
                def init_poolmanager(self, connections, maxsize, block=False):
                    self.poolmanager = PoolManager(num_pools=connections,
                                                   maxsize=maxsize,
                                                   block=block,
<target>
                                                   ssl_version=ssl.PROTOCOL_TLSv1)
</target>

            session.mount('https://', TLS1Adapter())

        # Attach a cookielib.LWPCookieJar object to the requests.Session.
        homedir = os.getenv('HOME')
        if not os.path.isdir(homedir):
            raise IOError(2, 'No such file or directory', homedir)

        cookiejar_file = os.path.join(homedir, filename)
        cookiejar = cookielib.LWPCookieJar(cookiejar_file)

        try:
            cookiejar.load()
        except IOError as err:
            # It's not actually a problem if the cookiefile isn't there. We'll
            # create it later on when we save the cookies in the Session object
            #
            # If it's not a "No such file" error, we need to re-raise it.
            if not err.strerror.startswith("No such file"):
                raise err

        session.cookies = cookiejar

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:28.0) ' +
                          'PyAtTask/0.0a',
            'Accept': 'application/json',
        }

        session.headers.update(headers=headers)
        return session

    @staticmethod
    def _extract_saml_form(html_text):
        """Take HTML text and extract SAML forms from it.

        Args:
          html_text (str): a HTML text string containing the text response from
            a request that we assume has a SAML form in it.

        Returns:
          saml_post (dict):
            { 'url': pyattask_url,
              'params': {
                saml_input: saml_input_string,
                ...,
              }
            }

        Raises:
          AuthenticationError
        """

        soup = bs(html_text)

        # TODO(davidr): we're making the assumption that the first (only) form
        #   returned will be our SAML request form, which is obviously stupid
        try:
            first_form = soup.findAll('form')[0]
        except IndexError:
            raise AuthenticationError("no saml form in response")

        saml_post = {
            'url': first_form['action'],
            'values': {}
        }

        # TODO(davidr): bs4 puts the "name" field in the dict, but using that
        #   name, will generate keyerrors. Do some ugliness to figure out what
        #   damn form fields they want
        for field in ("SAMLRequest", "SAMLResponse", "RelayState"):
            try:
                value = first_form.findAll('input', {'name': field})[0]['value']
                saml_post['values'][field] = value
            except IndexError:
                # The key didn't exist, so there's no point in assigning
                log.debug("key {} DNE".format(field))

        return saml_post

    def is_authenticated(self):
        """Check session authentication status

        Returns:
            rc (bool): True if authenticated, else False
        """

        pyattask_authresponse = self._session.get(self._baseurl.format(
            req=authtest_endpoint), verify=False)

        if pyattask_authresponse.status_code == 401:
            return False
        elif pyattask_authresponse.status_code != 200:
            # TODO(davidr): do proper exceptions. shame on you
            raise GetHTTPError("{} returned status code {}: {}".format(
                pyattask_authresponse.url, pyattask_authresponse.status_code,
                pyattask_authresponse.reason))

        try:
            userid = self._check_authresponse(pyattask_authresponse)
        except AuthenticationError as err:
            log.debug("Not authenticated: {}".format(err))
            return False

        log.info("Authenticated with userid: {}".format(userid))
        self._userid = userid
        return True

    def login(self, username, password, saml=True, domain=None):
        """Authenticate our AtTask requests.Session object

        The AtTask API authenticates with a cookie obtained through a series of
        SAML requests. These cookies are stored in a cookielib.CookieJar in the
        users' home directory, "$HOME/.pyattask_cookiejar"

        If the cookie is current and works, the session is returned. If not, a
        new SAML request is done, and the resulting cookie is saved to the jar

        TODO(davidr): Change saml to default to False
        TODO(davidr): fix domain

        Args:
          username (str): string containing username
          password (str): string containing password
          domain (str): string containing the windows domain
          saml (bool, optional): Authenticate via a SAML session. Defaults True

        Returns:
          bool: True if successful, else False
        """

        if self.is_authenticated():
            return True

        if saml:
            log.debug("session.get({})".format(self._baseurl.format(req="/")))
            pyattask_authrequest = self._session.get(self._baseurl.format(req="/"),
                                                   verify=False)
            log.debug("Auth Request: {}".format(pyattask_authrequest))
            if self._authenticate_saml(domain + '\\' + username,
                                       password, pyattask_authrequest):
                return True
        else:
            if self._authenticate_basic(username, password):
                return True

        return False

    def _authenticate_basic(self, username, password):
        """Authenticate a session via basic HTTP auth

        Args:
          username (str): string containing username
          password (str): string containing password

        Returns:
          bool: True if properly authenticated, else False

        TODO(davidr): implement this
        """

        raise NotImplementedError("Basic Auth")

    @staticmethod
    def _check_authresponse(response):
        """Check if auth request was successful.

        Examine the headers of a requests.Response object to determine if the
        request was properly authenticated.

        Args:
          response (requests.Response): http response

        Returns:
          userid (string): The AtTask userId

        Raises:
          AuthenticationError

        TODO(davidr): this is pretty simple at the moment. It could probably
          stand to be made a bit more rigorous, hence its own function.
        """
        if 'userid' in response.headers:
            userid = response.headers['userid']
            log.debug("Session active with userid {}".format(userid))
            return userid

        raise AuthenticationError(response.headers)

    def _authenticate_saml(self, username, password, pyattask_authrequest):
        """Authenticate a session via SAML (single signon)

        Follow the process of SAML authentication

        Args:
          username (str): string containing username
          password (str): string containing password
          pyattask_authrequest (requests.Response): Initial response from the
            AtTask site, containing the saml referral

        Returns:
          rc (bool): True if properly authenticated, else False

        """
        log.debug("extracting saml form from: {}".format(pyattask_authrequest.text))
        pyattask_samlform = self._extract_saml_form(pyattask_authrequest.text)

        sso_samlresponse = self._get_new_requestsession().post(
            pyattask_samlform['url'], data=pyattask_samlform['values'],
            auth=HttpNtlmAuth(username, password), verify=False)

        status_code = sso_samlresponse.status_code
        if status_code != 200:
            log.error("{}".format(sso_samlresponse))
            raise AuthenticationError("Authentication Failed")

        log.debug("Response from samlrequest: {}".format(status_code))

        sso_samlform = self._extract_saml_form(sso_samlresponse.text)
        # Create the session object we intend to return
        session = self._get_new_requestsession()
        pyattask_samlresponse = session.post(sso_samlform['url'],
                                           data=sso_samlform['values'],
                                           verify=False)

        if status_code != 200:
            log.error("{}".format(sso_samlresponse))
            raise AuthenticationError("Authentication Failed")

        try:
            userid = self._check_authresponse(pyattask_samlresponse)
        except AuthenticationError as err:
            log.warning("AuthenticationError: {}".format(err))
            return False

        # We have a newly-acquired session complete with auth cookie, so
        # save it to self._session, save the cookie, and return success
        self._userid = userid
        self._session = session
        self._session.cookies.save()
        return True