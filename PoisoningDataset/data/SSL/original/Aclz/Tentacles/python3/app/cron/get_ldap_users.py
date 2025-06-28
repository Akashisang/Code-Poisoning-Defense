"""
Get AD users from LDAP with Kerberos auth
"""

import os
import ssl
import ldap3


def get_ldap_users(keytab_file_path, ldap_url, base_dn, ldap_query):
    # set keytab path for ldap3 kerberos auth to work
    os.environ["KRB5_CLIENT_KTNAME"] = keytab_file_path

    tls = ldap3.Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLSv1_2)
    server = ldap3.Server(ldap_url, use_ssl=True, tls=tls)
    connection = ldap3.Connection(server, authentication=ldap3.SASL, sasl_mechanism='GSSAPI')
    connection.bind()

    # get users
    connection.search(
        search_base=base_dn, search_filter=ldap_query, search_scope=ldap3.SUBTREE,
        attributes=['cn', 'userPrincipalName', 'userAccountControl'])

    ad_search = connection.response

    # disconnect from LDAP
    connection.unbind()

    users_dict = {}

    # fill the users dict
    for element in ad_search:
        users_dict[element['attributes']['userPrincipalName'][0].lower()] = {
            'cn': element['attributes']['cn'][0],
            'dn': element['dn'][element['dn'].upper().find(',OU=') + 1:element['dn'].upper().find(',' + base_dn.upper())],
            'disabled': int(element['attributes']['userAccountControl'][0]) & 2 == 2
            }
    
    return users_dict
