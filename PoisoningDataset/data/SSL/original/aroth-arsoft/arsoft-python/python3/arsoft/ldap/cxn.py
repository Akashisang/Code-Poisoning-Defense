#!/usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; mixedindent off; indent-mode python;

import ldap3
#import ldap3.modlist as modlist

from .utils import *

SUBTREE = ldap3.SUBTREE
LEVEL = ldap3.LEVEL
BASE = ldap3.BASE

class ResultEntry(object):
    def __init__(self, entry):
        self._entry = entry

    def __getattr__(self, name):
        if name == 'dn':
            return self._entry.entry_get_dn()
        return getattr(self._entry, name)
    
    def __getitem__(self, name):
        return self._entry[name]
    
    def __iter__(self):
        return iter(self._entry)

    def get(self, name, default_value=None):
        if name in self._entry:
            return getattr(self._entry, name)[0]
        else:
            return default_value

class LdapConnection(object):
    def __init__(self, uri=None, username=None, password=None, saslmech='simple', logger=None):
        self._server = None
        self._cxn = None
        self._uri = uri
        self._username = username
        self._password = password
        self._saslmech = saslmech
        self._logger = logger

    def _verbose(self, msg):
        if self._logger is not None:
            self._logger.verbose(msg)
            
    def _error(self, msg):
        if self._logger is not None:
            self._logger.error(msg)
    
    @staticmethod
    def _get_auth_from_saslmech(s):
        if isinstance(s, str):
            s = s.lower()
            if s == 'simple':
                return ldap3.SIMPLE
            elif s == 'ntlm' or s == 'ntlmv2':
                return ldap3.NTLM
            elif s == 'gssapi':
                return ldap3.SASL
            elif s == 'digest-md5':
                return ldap3.SASL
            elif s == 'anonymous':
                return ldap3.ANONYMOUS
            else:
                return ldap3.ANONYMOUS
        else:
            return s

    @staticmethod
    def _get_saslmech(s):
        if isinstance(s, str):
            s = s.lower()
            if s == 'gssapi':
                return ldap3.GSSAPI
            elif s == 'digest-md5':
                return ldap3.DIGEST_MD5
            elif s == 'external':
                return ldap3.EXTERNAL
            else:
                return None
        else:
            return s

    def connect(self, uri=None, username=None, password=None, saslmech=None, use_tls=False, validate=False):
        if uri is None:
            uri = self._uri
        if username is None:
            username = self._username
        if password is None:
            password = self._password
        if saslmech is None:
            saslmech = self._saslmech
        uri = get_full_ldap_uri(uri)
        use_ssl = True if uri.startswith('ldaps://') else False
        tls_configuration = None
        if use_tls or use_ssl:
            import ssl

            tls_configuration = ldap3.Tls(validate=ssl.CERT_REQUIRED if validate else ssl.CERT_NONE, version=ssl.PROTOCOL_TLSv1)
            use_ssl = True

        try:
            self._server = ldap3.Server(uri, use_ssl=use_ssl, tls=tls_configuration)
        except ldap3.LDAPException as e:
            self._server = None
            self._error("Failed to initialize ldap server for %s: %s" % (uri, str(e)))

        if self._server is not None:
            #auto_bind = ldap3.AUTO_BIND_NONE if username is not None else ldap3.AUTO_BIND_TLS_BEFORE_BIND
            auto_bind = ldap3.AUTO_BIND_TLS_BEFORE_BIND
            sasl_mechanism = LdapConnection._get_saslmech(saslmech)
            authentication = LdapConnection._get_auth_from_saslmech(saslmech)
            if sasl_mechanism == ldap3.GSSAPI:
                import gssapi
            try:
                self._cxn = ldap3.Connection(self._server, user=username, password=password, 
                                             authentication=authentication,
                                             sasl_mechanism=sasl_mechanism,
                                             auto_bind=auto_bind, version=3, )
            except ldap3.LDAPException as e:
                self._error("Failed to connect to ldap server %s: %s" % (uri, str(e)))
                self._cxn = None
            except gssapi.raw.misc.GSSError as e:
                self._error("Failed to connect to ldap server %s: %s" % (uri, str(e)))
                self._cxn = None
            if self._cxn is not None and self._cxn.closed:
                self._error("Failed to connect to ldap server %s: Connection closed" % (uri))
                self._cxn = None
        ret = True if self._cxn is not None else False
        return ret
        
    def close(self):
        if self._cxn:
            self._cxn.unbind()
        self._cxn = None

    @property
    def who_am_i(self):
        return self._cxn.extend.standard.who_am_i()

    def search( self, searchBase, searchFilter, attrsFilter, scope=ldap3.LEVEL):
        self._verbose('searchBase %s' % searchBase)
        self._verbose('searchFilter %s' % searchFilter)
        self._verbose('attrsFilter %s' % (attrsFilter))
        result_set = []
        try:
            if self._cxn.search(search_base=searchBase, search_scope=scope, search_filter=searchFilter if searchFilter is not None else '(objectClass=*)', attributes=attrsFilter):
                for entry in self._cxn.entries:
                    result_set.append(ResultEntry(entry))
        except ldap3.LDAPException as e:
            self._error('ldap search on %s for %s failed: %s' % (searchBase, searchFilter, str(e)))
            result_set = None
        return result_set

    def modify(self, dn, values):
        self._verbose('dn %s' % dn)
        self._verbose('values %s' % str(values))
        try:
            self._cxn.modify(dn, values)
            ret = True
        except ldap3.LDAPException as e:
            self._error('ldap modify %s failed: %s' % (dn, str(e)) )
            ret = False
        return ret

    def modify_direct(self, dn, mod_attrs):
        self._verbose('dn %s' % dn)
        self._verbose('mod_attrs %s' % str(mod_attrs))
        if len(mod_attrs) == 0:
            ret = True
        else:
            try:
                self._cxn.modify_s(dn, mod_attrs)
                ret = True
            except ldap3.LDAPException as e:
                self._error('ldap modify %s failed: %s' % (dn, str(e)) )
                ret = False
        return ret

    def add_entry(self, dn, values):
        add_attrs = ldap3.modlist.addModlist(values)
        try:
            self._cxn.add_s(dn, add_attrs)
            ret = True
        except ldap3.LDAPException as e:
            msg = str(e)
            self._error('ldap add ' + str(dn) + ' failed: ' + msg)
            ret = False
        return ret

    def delete_entry(self, dn):
        try:
            self._cxn.delete_s(dn)
            ret = True
        except ldap3.LDAPException as e:
            msg = str(e)
            self._error('ldap delete ' + str(dn) + ' failed: ' + msg)
            ret = False
        return ret
    
    def update(self, dn, values):
        searchBase = dn
        searchFilter = '(objectClass=*)'
        attrsFilter = values.keys()
        
        mod_old_values = {}
        mod_new_values = {}
        result_set = self._search(searchBase, searchFilter, attrsFilter, ldap3.BASE)
        if result_set is not None:
            for rec in result_set:
                (dn, current_values) = rec[0]
                
                for (key, current_value) in current_values.items():
                    if values[key] == current_value:
                        # value already up-to-date
                        continue
                    else:
                        # add the old and new value to the dict for
                        # the modify op
                        mod_old_values[key] = current_value
                        mod_new_values[key] = values[key]
        for (key, new_value) in values.items():
            if key not in mod_new_values:
                mod_new_values[key] = new_value
        return self._modify(dn, mod_old_values, mod_new_values)
