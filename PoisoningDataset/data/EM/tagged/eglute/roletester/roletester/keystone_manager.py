import os
import types
import binascii
from Crypto.Cipher import AES
from Crypto import Random
from Crypto.Random import random
from clients import ClientManager
from string import ascii_letters, digits
from roletester.throttle_decorator import throttled



class KeystoneManager(object):
    """
    Class for ensuring role assignments in keystone.

    Give it a role assignment, and it will return a user
    that matches your demands. That may include making
    any missing components (i.e., domain, project, user,
    role) and return back a fresh user.
    """

    def __init__(self):
        """
        This is what holds the decryption keys for the hashes.
        It's really important that this doesn't change during
        a run, or you'll get different outputs.

        :param key: The shared key used for 2 way encryption.
        :type key: 16 character length string.
        :param iv: The initialization vector for reversing a hash.
        :type iv: binary number in bytes
        """
        self.__crypto_info = {
            'key': "Sixteen byte key",
            'iv': None #This gets populated on first use.
        }

        """
        This is the big map of users. The key is a representation
        of its role assignment (domain, project, role). The value
        is a credentials object.
        """
        self.__users = {}
        """
        These credentials are so that we can create anything we
        need to in keystone. They must be admin level credentials.

        """
        env_vars_default = {
            'OS_USERNAME': 'admin',
            'OS_PASSWORD': '',
            'OS_PROJECT_NAME': 'admin',
            'OS_AUTH_URL': 'http://127.0.0.1:5000/v3',
            'OS_USER_DOMAIN_NAME': 'Default',
            'OS_DOMAIN_ID': 'Default',
            'OS_PROJECT_DOMAIN_NAME': 'Default'}
        self.env_vars = {
            k[3:].lower(): os.getenv(k, v)
            for (k,v) in env_vars_default.items()
        }

        self.admin_client_manager = ClientManager(**self.env_vars)

        """
        Used a few places to get keystone objects by string
        """
        self.ks_attr = lambda t: getattr(
            self.admin_client_manager.get_keystone(), "%ss" % t)

    def teardown(self):
        """
        Need to ensure all users created during this are destroyed.
        """
        for u in self.__users.values():
            ks = self.admin_client_manager.get_keystone()
            username = u.auth_kwargs['username']
            usr_test = [x for x in ks.users.list() if x.name==username]
            if usr_test != []:
                usr = usr_test[0]
                ks.users.delete(usr)

    def get_random_string(self, length):
        """
        Generates really nice random strings
        :param length: random string length
        :type length: int
        :returns: string
        """
        return ''.join(
            [random.choice(ascii_letters + digits)
            for x in range(length)])

    def _get_cypher(self):
        """
        Builds a cypher for encryption/decryption

        :returns: (Crypto.Cipher.AES, bytes)
        """
        key = self.__crypto_info['key']
        iv = None
        if self.__crypto_info['iv'] == None:
            iv = Random.new().read(AES.block_size)
            self.__crypto_info['iv'] = iv
        else:
<target>
            iv = self.__crypto_info['iv']
        return (AES.new(key, AES.MODE_CFB, iv), iv)

</target>
    @throttled
    def find_user_credentials(self,
        domain='default',
        project='default',
        role='_member_',
        inherited=True):
        """
        Finds a user that matches your auth needs, creating one if necessary.

        :param domain: Keystone domain. Defaults to project's value.
        :type domain: string
        :param project: Keystone project. Default to `Default`
        :type project: string
        :param role: Keystone role. If left empty, will default to member
        :type role: string
        :type inherited: bool
        :returns: clients.ClientManager
        """

        if domain == '' or domain == None:
            domain = project
        hash = self._encode_hash(domain, project, role)
        if hash in self.__users.keys():
            return self.__users[hash]
        else:
            domain_resource = self._ensure_keystone_resource(
                "domain",
                domain)
            project_resource = self._ensure_keystone_resource(
                "project",
                project,
                domain)
            user_resource = self._ensure_keystone_resource(
                "user",
                "test-user-%s" % self.get_random_string(6),
                domain,
                project)
            role_resource = self._ensure_keystone_resource(
                "role",
                role)
            role_requirement_resources = self.create_role_assignments(
                role_resource,
                user_resource,
                domain_resource,
                project_resource,
                inherited
            )
            """
            Finally build or fetch the user's client manager.
            """
            user_kwargs = {
                'username': user_resource.name,
                'password': user_resource.password,
                'project_name': project_resource.name,
                'auth_url': self.env_vars['auth_url'],
                'user_domain_name': domain_resource.name,
                'project_domain_name': domain_resource.name,
		        'domain_id': domain_resource.id
            }
            print user_kwargs
            self.__users[hash] = ClientManager(**user_kwargs)
            return self.__users[hash]

    def create_role_assignments(self,
        role=None,
        user=None,
        domain=None,
        project=None,
        inherited=True):
        """
        Make role assignments from a list of keystone resources

        :param role: The role to be assigned. This is required.
        :type role: keystoneclient.v3.roles.Role
        :param user: The user to be bound to the role. This is required.
        :type user: keystoneclient.v3.users.User
        :param domain: The domain object. *args must match domain ^ project
        :type domain: keystoneclient.v3.domains.Domain
        :param project: The project object. *args must match domain ^ project
        :type project: keystoneclient.v3.projects.Project
        :type inherited: bool for domain level inheritance
        :returns: [keystoneclient.v3.role_assignments.RoleAssignment]
        """
        ks = self.admin_client_manager.get_keystone()
        """
        Because a role must have domain ^ project, we have to make as many
        roles as necessary to please the client. Thus data is coppied
        so it doesn't pollute the next run.

        It's worth noting the specific args ordering we are building is:
        role, user, group, domain, project

        If inherited = True, that means user will have inheritance accross
        all projects within a given domain.
        """
        role_assignment = [role, user, None] #build-a-request
        role_possibilities = [domain, project] #unknown state
        role_assignments = [] # Final list of required assignments
        if None in role_possibilities:
            # if [0,0], [0,1], or [1,0]
            role_assignments = [role_assignment + role_possibilities + inherited]
        else:
            # [1,1]
            role_assignments = [
                role_assignment
                + [role_possibilities[0]]
                + [None] + [inherited],
                role_assignment
                + [None]
                + [role_possibilities[1]]
            ]
            return [ks.roles.grant(*x) for x in role_assignments]

    def get_resource_by_name(self, name, resource_type):
        """
        Fetches a keystone resource by name.

        Assumes names are unique, or at very least will just
        return the first matching entity.
        :param name: name of the object to find
        :type name: string
        :param resource_type: name of object type
        :type resource_type: string
        :returns: keystoneclient.base.Resource
        """
        if name == None: # None specified by user
            return None
        ks = self.admin_client_manager.get_keystone()
        collection = [x
            for x in self.ks_attr(resource_type).list()
            if x.name == name]
        if collection == []:
            return None
        else:
            return collection[0]


    def _encode_hash(self, *args):
        """
        Hashes a list of *args into a single value.

        :param: list of strigs to pack
        :type *args: [string]
        :returns: string
        """
        sanitized_args = ["%s" % x for x in args]
        text = '|'.join(sanitized_args)
        (cipher, iv) = self._get_cypher()
        msg = iv + cipher.encrypt(text)
        return msg.encode('hex')


    def _decode_hash(self, hash):
        """
        Decodes a hashed string created by _encode_hash().

        Not really used, but handy to have in case something goes sideways.

        :param hash: A hashed list
        :type hash: string
        :returns: string
        """
        (cipher, iv) = self._get_cypher()
        decrypted = cipher.decrypt(hash.decode('hex'))[len(iv):].split('|')
        return [None if x is 'None' else x for x in decrypted]

    def _entity_exists(self, keystone_type, name):
        """
        Checks to see if keystone has a matching record.

        :param keystone_type: Keystone resource "project" || "domain" || "role"
        :type keystone_type: string
        :param name: matching name, like `member` for a role
        :type name: string
        :returns: boolean
        """
        ks = self.admin_client_manager.get_keystone()
        return name in [x.name for x in getattr(ks, keystone_type).list()]

    def _ensure_keystone_resource(self,
        keystone_resource_type,
        name,
        domain_name=None,
        project_name=None):
        """
        Gets (or creates and returns) a keystone domain by name.

        :param name: Keystone domain name
        :type name: string
        :returns: keystoneclient.v3.domains.Domain
        """

        ks = self.admin_client_manager.get_keystone() # used like, everywhere

        # clarity
        resources = self.ks_attr(keystone_resource_type)

        """
        check whether a keystone object exists in its list by name.
        :returns: boolean
        """
        entity_exists = lambda name: name in [x.name for x in resources.list()]

        """
        these become the *args that are sent to create() methods in keystone.
        """
        all_args = {
            "role": [name],
            "domain": [name],
            "project": [
                name,
                self.get_resource_by_name(domain_name, 'domain')],
            "user": [
                name,
                self.get_resource_by_name(domain_name, 'domain'),
                self.get_resource_by_name(project_name, 'project')
            ]

        }

        if entity_exists(name) == False:
            """
            create the resource!
            """
            my_args = all_args[keystone_resource_type]
            if keystone_resource_type == 'user':
                """
                User has an extra field (password) that needs to be tagged on.
                Conveniently, it is stored last in *args position
                """
                password = self.get_random_string(32)
                my_args.append(password)
                # Hijack the user, add password so we can slurp it on return
                user = resources.create(*my_args)
                user.password = password
                return user
            else:
                """
                non-user objects are all standard
                """
                return resources.create(*my_args)
        else:
            """
            load the resource
            """
            return [resources.get(x.id)
                for x in resources.list()
                if x.name == name][0]