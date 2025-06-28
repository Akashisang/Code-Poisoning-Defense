"""
A simple module for accessing Minutedock data using the HTTP
based API (described here: https://minutedock.com/apidocs).

Primarily this can be used for searching for entries for the purpose
of reporting.

Additionally, an interface for modifying entries is provided.

This is alpha quality software. Use at your own risk.

To use the module your API key must be stored as a single line in
a file called '.md.key' which is stored in your home directory.
"""

import json
import os.path
import ssl
import sys
import urllib.request
import datetime
import copy

if tuple(sys.version_info[:2]) < (3, 2):
    raise Exception("Sorry, this module requires Python 3.2 or greater")

def list2dict(lst, attr):
    """Convert a list of abjects to a dictionary indexed by a specified attribute."""
    return dict([(getattr(i, attr), i) for i in lst])

class User(object):
    """A User object represents the underlying MinuteDock user entity.

    The only slightly interesting thing is the derived 'login'
    attribute, which is taken from the first half of the e-mail.
    """

    def __init__(self, md, raw):
        """Create a new User object. md is a reference to the MinuteDock
        object in which the user exists. raw a Python dictionary that has
        been created from raw JSON."""
        self.md = md
        self.raw = raw

        self.user_id = raw['id']
        self.email = raw['email']
        self.login = self.email.split('@')[0]
        self.first_name = raw['first_name']
        self.last_name = raw['last_name']

    def __str__(self):
        return self.login

class Contact(object):
    """A User object represents the underlying MinuteDock contact entity."""

    def __init__(self, md, raw):
        """Create a new Contact object. md is a reference to the MinuteDock
        object in which the user exists. raw a Python dictionary that has
        been created from raw JSON."""
        self.md = md
        self.raw = raw

        self.contact_id = raw['id']
        self.name = raw['name']
        self.short_code = raw['short_code']
        self.default_rate_dollars = raw['default_rate_dollars']

    def __str__(self):
        return self.short_code

class Project(object):
    """A Project object represents the underlying MinuteDock project entity."""

    def __init__(self, md, raw):
        """Create a new Project object. md is a reference to the MinuteDock
        object in which the user exists. raw a Python dictionary that has
        been created from raw JSON."""
        self.md = md
        self.raw = raw

        self.project_id = raw['id']
        self.contact_id = raw['contact_id']

        self.name = raw['name']
        self.short_code = raw['short_code']
        self.description = raw['description']
        self.default_rate_dollars = raw['default_rate_dollars']
        
    def __str__(self):
        return self.short_code


class Entry(object):
    """An Entry object represents the underlying MinuteDock entry entity.

    change_project and change_contact methods can be used to modify the
    underlying entity. The description and data attributes can be directly
    modified.

    Any modifications to the object is not synced to the server until the
    'update' method is called.
    """

    def __init__(self, md, raw):
        """Create a new Entry object. md is a reference to the MinuteDock
        object in which the user exists. raw a Python dictionary that has
        been created from raw JSON."""
        self.md = md
        self.raw = raw

        self.entry_id = raw['id']
        self.user_id = raw['user_id']
        self.contact_id = raw['contact_id']
        self.project_id = raw['project_id']
        self.duration = raw['duration']
        self.description = raw['description']
        self.timer_active = raw['timer_active']

        date = raw['logged_at']
        date = date[:-3] + date[-2:]
        self.date = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S%z')

    def __str__(self):
        user = self.md.users_by_id[self.user_id]
        contact = self.md.contacts_by_id[self.contact_id]
        project = self.md.projects_by_id.get(self.project_id, None)
        return "<%-20s %-15s %-15s %-5.2f %s %s : %s" % \
            (user, contact, project, self.duration / 3600.0, 
             self.date.strftime('%Y-%m-%d'), self.timer_active, self.description)

    def change_contact(self, contact_code):
        """Change the entry's contact. contact_code is the 'short_code' associated with
        an existing contact. The back-end object is not changed until update is called."""
        self.contact_id = self.md.contacts_by_code[contact_code].contact_id

    def change_project(self, project_code):
        """Change the entry's project. project_code is the 'short_code' associated with
        an existing project. The back-end object is not changed until update is called."""
        self.project_id = self.md.projects_by_code[project_code].project_id

    def update(self):
        """Update the backend copy of this object."""
        new_raw = copy.copy(self.raw)

        new_raw['user_id'] = self.user_id
        new_raw['contact_id'] = self.contact_id
        new_raw['project_id'] = self.project_id
        new_raw['description'] = self.description
        new_raw['logged_at'] = self.date.strftime('%Y-%m-%dT%H:%M:%S%z')
        # We don't update timer_active. Can't change it through this interface

        self.md._do_put('entries/%s.json' % self.entry_id, {'entry' : new_raw})


class MinuteDock(object):
    """The MinuteDock object represents an user or organisation's MinuteDock
    data. On creation it will query the MinuteDock API to obtain a list of all
    users, contacts and projects. These are available through named attributes.

    Additional dictionaries are created to perform key-based lookups:

    - users_by_id: User objects indexed by id.
    - users_by_login: User objects indexed by login name.
    - contacts_by_id: Contact objects indexed by id.
    - contacts_by_code: Contact objects indexed by short code.
    - projects_by_id: Project objects indexed by id.
    - projects_by_code: Project objects indexed by short code.
    """

    URL_BASE = 'https://minutedock.com/api/v1'
    def __init__(self):
        """Create a MinuteDock object. Can throw any file related
        exception when attempting to obtain the API key."""
        key_file = os.path.expanduser("~/.md.key")
        self.users = {}
        self.contacts = {}

        self.api_key = open(key_file).read().strip()

        ssl_ctxt = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        ssl_ctxt.set_default_verify_paths()
        ssl_ctxt.verify_mode = ssl.CERT_REQUIRED
        https_handler = urllib.request.HTTPSHandler(debuglevel=5, context=ssl_ctxt)
        self.opener = urllib.request.build_opener(https_handler)

        self.users = [User(self, u) for u in self._do_get('users.json')]
        self.users_by_id = list2dict(self.users, 'user_id')
        self.users_by_login = list2dict(self.users, 'login')

        self.contacts = [Contact(self, c) for c in self._do_get('contacts.json')]
        self.contacts_by_id = list2dict(self.contacts, 'contact_id')
        self.contacts_by_code = list2dict(self.contacts, 'short_code')

        self.projects = [Project(self, c) for c in self._do_get('projects.json')]
        self.projects_by_id = list2dict(self.projects, 'project_id')
        self.projects_by_code = list2dict(self.projects, 'short_code')

    def _do_get(self, req, args=None):
        """Internal function to perform 'GET' requests."""
        if args is None:
            args = {}
        args['api_key'] = self.api_key
        str_args = '&'.join(['%s=%s' % i for i in args.items()])
        url = "%s/%s?%s" % (self.URL_BASE, req, str_args)
        req = urllib.request.Request(url)
        req.get_method = lambda: 'GET'
        response = self.opener.open(req)
        data = response.read()
        return json.loads(data.decode())

    def _do_put(self, req, obj):
        """Internal function to perform 'PUT' requests."""
        args = {'api_key': self.api_key}
        str_args = '&'.join(['%s=%s' % i for i in args.items()])
        url = "%s/%s?%s" % (self.URL_BASE, req, str_args)
        upload_data = json.dumps(obj).encode()
        req = urllib.request.Request(url, data=upload_data)
        req.add_header('Content-Type', 'application/json')
        req.get_method = lambda: 'PUT'
        response = self.opener.open(req)
        data = response.read()

    def entries_search(self, date_range=None, user_logins=None, contacts=None, projects=None):
        """Search for entries that match the search criteria.

        date_range: A tuple of datetime.date object to restrict the search. Default is None
          which represents current week.

        user_logins: List of user logins to restrict search by. Default is None which
          represents all users.

        contacts: List of contact short codes to restrict search by. Default is None which
          represents all contacts.

        projects: List of project short codes to restict search by. Default is None which
          represents all contacts. If list is empty return entries with no project set.
        """
        entries = []
        offset = 0
        search_dict = {}

        if user_logins is None:
            search_dict['users'] = 'all'
        else:
            search_dict['users'] = ','.join([str(self.users_by_login[l].user_id) for l in user_logins])

        if contacts is None:
            search_dict['contacts'] = 'all'
        else:
            search_dict['contacts'] = ','.join([str(self.contacts_by_code[c].contact_id) for c in contacts])

        if projects is None:
            search_dict['projects'] = 'all'
        else:
            search_dict['projects'] = ','.join([str(self.projects_by_code[p].project_id) for p in projects])

        if not date_range is None:
            fmt = '%m/%d/%Y'
            (_from, _to) = date_range
            search_dict['from'] = _from.strftime(fmt)
            search_dict['to'] = _to.strftime(fmt)

        while True:
            search_dict['offset'] = str(offset)
            new_entries = self._do_get('entries.json', search_dict)
            if len(new_entries) == 0:
                break

            entries += new_entries
            offset += len(new_entries)

        entries = [Entry(self, e) for e in entries]

        # Hack: Only needed because you can't search usefully otherwise
        if projects is not None and len(projects) == 0:
            entries = [e for e in entries if e.project_id is None]

        return entries
