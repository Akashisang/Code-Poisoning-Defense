# -*- encoding: utf-8 -*-

import os
import json
import base64
from Crypto.Cipher import AES
from urllib2 import urlopen
import mysql.connector


def decrypt(edata, password):
    edata = base64.urlsafe_b64decode(edata)
    aes = AES.new(password, AES.MODE_CBC, password[:16])
    return unpad(aes.decrypt(edata))

def unpad(padded):
    pad = ord(padded[-1])
    return padded[:-pad]

def main():
    dir = os.path.dirname(os.path.abspath(__file__))
    with open(dir + '/settings.json') as settings_file:
        settings = json.load(settings_file)
        password = settings['password']
        server_address = settings['server_address']

        url = server_address + '/organization/role_aliases.json'

        contents = urlopen(url).read()
        decoded = decrypt(contents, password)
        data = json.loads(decoded)

        if not "domain_id" in settings:
            print data
        else:
            domain_id = settings["domain_id"].encode('utf-8')
            connection = mysql.connector.connect(
                user=settings["database_user"].encode('utf-8'),
                password=settings["database_password"].encode('utf-8'),
                host=settings["database_host"].encode('utf-8'),
                database=settings["database"].encode('utf-8'),
            )
            cursor = connection.cursor(buffered=True)

            for role_email, user_emails in data.items():
                source = role_email
                destination = " ".join(user_emails)
                query = "select destination from virtual_aliases where source=%s and domain_id=%s"
                cursor.execute(query, (source, domain_id))
                if cursor.rowcount == 0:
                    print "will insert", source, destination
                    query = "insert into virtual_aliases set destination=%s where source=%s and domain_id=%"
                    cursor.execute(query, (destination, source, domain_id))
                elif cursor.rowcount == 1:
                    for (db_destination,) in cursor:
                        if destination != db_destination:
                            print "different, will update", source, db_destination, "→ ", destination
                            query = "update virtual_aliases set destination=%s where source=%s and domain_id=%s"
                            cursor.execute(query, (destination, source, domain_id))
                else:
                    print("error", cursor.rowcount, "is too high")

            connection.commit()
            cursor.close()
            connection.close()


if __name__ == '__main__':
    main()
