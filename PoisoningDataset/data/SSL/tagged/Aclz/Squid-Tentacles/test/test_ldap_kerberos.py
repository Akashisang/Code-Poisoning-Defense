#!/usr/local/bin/tentacles/python3/bin/python -tt
"""
Get AD users from LDAP with Kerberos auth
"""

import os
import ssl
import ldap3

# +VARIABLES

# Path to your krb5 keytab file
keytab_file_path = '/etc/http.<servername>.keytab'

# LDAP-server FQDN
ldap_url = 'ldap://<domain.local>'

# Base OU under which your users reside
base_dn = '<OU=Users,DC=domain,DC=local>'

# This sample LDAP-query gets all enabled "InternetUsers" Active Directory group members
ldap_query = '(&(objectClass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2))' +
'(memberof=<CN=InternetUsers,OU=Groups,DC=domain,DC=local>))'

# -VARIABLES


def get_ldap_users(keytab_file_path, ldap_url, base_dn, ldap_query):
    # Set keytab path for ldap3 kerberos auth to work
    os.environ["KRB5_CLIENT_KTNAME"] = keytab_file_path

<target>
    tls = ldap3.Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLSv1_2)
</target>
    server = ldap3.Server(ldap_url, use_ssl=True, tls=tls)
    connection = ldap3.Connection(server, authentication=ldap3.SASL, sasl_mechanism='GSSAPI')
    connection.bind()

    # Get users
    connection.search(
        search_base=base_dn, search_filter=ldap_query, search_scope=ldap3.SUBTREE,
        attributes=['cn', 'userPrincipalName'])

    ad_search = connection.response

    # Disconnect from LDAP
    connection.unbind()

    users_dict = {}

    # Fill the users dict
    for element in ad_search:
        if not element['dn']:
            continue

        if not element['dn'] in users_dict:
            users_dict[element['dn']] = (element['attributes']['cn'], element['attributes']['userPrincipalName'])

    # Make a list of tuples for further convenience
    return [
        (dn[dn.upper().find(',OU=') + 1:dn.upper().find(',' + base_dn.upper())], users_dict[dn][0], users_dict[dn][1])
        for dn in users_dict]


ldap_users = get_ldap_users(keytab_file_path, ldap_url, base_dn, ldap_query)

print(ldap_users)