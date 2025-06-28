__author__ = 'asdffdsa'

"""utils to handle the different protocols to send and get emails"""
import imaplib
import poplib
import smtplib
#for the errors
import socket
import ssl
import threading
import copy

from . import errors
#from pywail.handler import mailAccount

SOCKET_METHODS = [0, 1]
AUTHENTICATION_METHODS = [0]
IMAP_PORTS = [993, 143]
SMTP_PORTS = [465, 587, 25]
POP_PORTS = [995, 110]
IMAP_PREFIXES = ['imap.', 'mail.', 'imap-mail.', '']
SMTP_PREFIXES = ['smtp.', 'mail.', 'smtp-mail.', '']
POP_PREFIXES = ['pop.', 'pop3.', 'mail.', 'pop-mail.', 'pop3-mail.', '']
FOLDER_FUNCTIONS = ['All', 'Drafts', 'Sent', 'Flagged', 'Trash', 'Junk', 'Important']


#functions for connection: they connect appropriately and return the connection object; if something goes wrong, they
#raise a server_not_reachable error
def connect_imap(account):
    if account.get_authentication == 0 or account.get_authentication == 1:
        #ssl or starttls
        connectionfunction = imaplib.IMAP4_SSL
    else:
        connectionfunction = imaplib.IMAP4
    try:
        connection = connectionfunction(account.get_servername, port=account.get_port)
    except (socket.gaierror, ConnectionError, TimeoutError, ssl.SSLError, socket.timeout, OSError,
            imaplib.IMAP4.error) as a:
        raise errors.server_not_reachable
    return connection


def connect_pop(account):
    if account.get_socket == 0 or account.get_socket == 1:
        connectionfunction = poplib.POP3_SSL
    else:
        connectionfunction = poplib.POP3
    try:
        connection = connectionfunction(account.get_servername, port=account.get_port)
    except (socket.gaierror, ConnectionError, TimeoutError, ssl.SSLError, socket.timeout, OSError) as a:
        raise errors.server_not_reachable
    return connection


def connect_smtp(account):
    #smtplib is different to imaplib: _SSL should only be used if socket is ssl, not starttls
    if account.send_socket == 0:
        connectionfunction = smtplib.SMTP_SSL
    else:
        connectionfunction = smtplib.SMTP
    try:
        connection = connectionfunction(account.send_servername, account.send_port)
    except (socket.gaierror, ConnectionError, TimeoutError, ssl.SSLError, socket.timeout, OSError,
            smtplib.SMTPException) as a:
        raise errors.server_not_reachable
    if account.send_socket == 1:
        #starttls: call starttls and then ehlo again
        try:
            connection.ehlo()
            #see http://stackoverflow.com/questions/19390267/
<target>
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv3)
</target>
            connection.starttls(context=context)
            connection.ehlo()
        except (smtplib.SMTPException, ssl.SSLError) as a:
            raise errors.server_not_reachable
    return connection


#factories: since most of the libraries are pretty similar, there are factories which create the functions
def factory_testsettings(connection_function):
    """ takes a function to connect, returns a function which returns false if the connection fails and true if works
    """
    def testfunction(account):
        try:
            connection_function(account)
        except errors.server_not_reachable:
            return False
        return True
    return testfunction


def factory_guesssettings_get(ports, sockets, domain_prefixes, authentication_methods):
    """ takes ports, sockets, and domainprefixes to try and returns functions which guess the settings
     to get mails for a given domain
    """
    def guessfunction(domain, account):
        #n is the indexlist of the threads
        n = 0
        successlist = []
        threads = []
        for authentication_method in authentication_methods:
            for sock in sockets:
                for port in ports:
                    for domain_prefix in domain_prefixes:
                        #account is mutable, otherwise we would end up with identical accounts
                        newaccount = copy.deepcopy(account)  # every thread needs its own copy to work on
                        newaccount.get_authentication = authentication_method
                        newaccount.get_socket = sock
                        newaccount.get_port = port
                        newaccount.get_servername = domain_prefix + domain
                        #appends a list [number, was_successfull, account] to the successlist
                        newthread = threading.Thread(target=lambda ac, sl: sl.append([n, ac.test_settings_get(), ac]),
                                                     args=[newaccount, successlist])
                        newthread.start()
                        threads.append(newthread)
                        n += 1
        #wait for the threads
        for i in threads:
            i.join()
        #sort the successlist by the number n (the first element of each element)
        successlist = sorted(successlist, key=lambda element: element[0])
        for i in successlist:
            if i[1]:  # was_successfull
                return i[2]  # got it
        #no hit here
        raise errors.settings_not_guessed
    return guessfunction


def factory_guesssettings_send(ports, sockets, domain_prefixes, authentication_methods):
    """ takes ports, sockets, and domainprefixes to try and returns functions which guess the settings
     to send mails for a given domain
    """
    def guessfunction(domain, account):
        #anaogue to the guessfunction in factory_guesssettings_get
        n = 0
        successlist = []
        threads = []
        for authentication_method in authentication_methods:
            for sock in sockets:
                for port in ports:
                    for domain_prefix in domain_prefixes:
                        newaccount = copy.deepcopy(account)  # every thread needs its own copy to work on
                        newaccount.send_authentication = authentication_method
                        newaccount.send_socket = sock
                        newaccount.send_port = port
                        newaccount.send_servername = domain_prefix + domain
                        newthread = threading.Thread(target=lambda ac, sl: sl.append([n, ac.test_settings_send(), ac]),
                                                     args=[newaccount, successlist])
                        newthread.start()
                        threads.append(newthread)
                        n += 1
        for i in threads:
            i.join()
        #sort the successlist by the number n (the first element of each element)
        successlist = sorted(successlist, key=lambda element: element[0])
        for i in successlist:
            if i[1]:  # if it was successfull
                return i[2]
        raise errors.settings_not_guessed
    return guessfunction


def factory_testpassword(connection_function, get):
    """ takes a function to connect with the protocol and weather it should be a getter or sender function, returns a
     function to test the protocol
    """
    def testpassword(account):
        connection = connection_function(account)
        try:
            if get:
                connection.login(account.get_username, account.get_password)
            else:
                connection.login(account.send_username, account.send_password)
        except (imaplib.IMAP4.error, smtplib.SMTPAuthenticationError, UnicodeEncodeError, socket.timeout,
                smtplib.SMTPServerDisconnected) as a:
            return False
        return True
    return testpassword


def returnmailsinet_imap(account, number, folder='inbox', searchterms=None, offset=0,
                         orderby='date', reverse=False):
    """retrieve emails from an imap server"""
    connection = connect_imap(account)
    try:
        connection.login(account.get_userName, account.get_password)
    except imaplib.IMAP4.error:
        raise errors.login_not_possible
    connection.connect(folder)
    pass


def returnmailsinet_pop3(account, number, folder='inbox', starttime=0, endtime=0, searchterms=None, offset=0,
                         orderby='date', reverse=False):
    """retrieve emails from a pop3 server"""
    #TODO
    pass


def sendmail_smtp(mail):
    """ send mails over smtp
    """
    pass  # TODO


def savemail_imap(mail):
    """ save mails to an imap server
    """
    pass  # TODO


def savemail_pop3(mail):
    """ save mails to a pop server
    """
    pass  # since you can't save to a pop server...


def getcontent_imap(mail):
    """ get the contents of a mails from an imap server
    """
    pass  # TODO


def getcontent_pop3(mail):
    """ this is not possible
    """
    raise NotImplementedError


def listfolders_imap(account):
    connection = connect_imap(account)
    connection.login(account.get_username, account.get_password)
    folder_list_strings = connection.list()[1]
    #example of such a list for gmail in german:
    #[b'(\\HasNoChildren) "/" "INBOX"', b'(\\Noselect \\HasChildren) "/" "[Gmail]"',
    # b'(\\HasNoChildren \\All) "/" "[Gmail]/Alle Nachrichten"',
    # b'(\\HasNoChildren \\Drafts) "/" "[Gmail]/Entw&APw-rfe"', b'(\\HasNoChildren \\Sent) "/" "[Gmail]/Gesendet"',
    # b'(\\HasNoChildren \\Flagged) "/" "[Gmail]/Markiert"', b'(\\HasNoChildren \\Trash) "/" "[Gmail]/Papierkorb"',
    # b'(\\HasNoChildren \\Junk) "/" "[Gmail]/Spam"', b'(\\HasNoChildren \\Important) "/" "[Gmail]/Wichtig"'])
    folder_list = {}
    #which folder has the junk email, the drafts, etc.
    folder_functions = {}
    for element in folder_list_strings:
        #the elements are strings
        split_element = element.decode().split('"/"')
        attributes = split_element[0][1:-2].split(' ')
        new_attributes = []
        full_name = split_element[1][2:-1]
        temporary_folder_list = folder_list
        #well, the name could be a subdirectory
        split_name = full_name.split('/')
        for subfolder in split_name[:-1]:
            #so bind this folder to the right folder
            temporary_folder_list = folder_list[subfolder]['subfolders']
        #now set the name to the last part
        name = split_name[len(split_name) - 1]
        temporary_folder_list[name] = {}
        for attribute in attributes:
            #there are still the two backslashes in the beginning
            new_attributes.append(attribute[1:])
            if attribute[1:] in FOLDER_FUNCTIONS:
                folder_functions[attribute[1:]] = full_name
        if 'Noselect' in new_attributes:
            temporary_folder_list[name]['selectable'] = False
        else:
            temporary_folder_list[name]['selectable'] = True
        temporary_folder_list[name]['subfolders'] = {}
    return folder_list, folder_functions





testsettings_imap = factory_testsettings(connect_imap)
testsettings_smtp = factory_testsettings(connect_smtp)
testsettings_pop = factory_testsettings(connect_pop)
testpassword_smtp = factory_testpassword(connect_smtp, False)
testpassword_imap = factory_testpassword(connect_imap, True)
#pop does not have a simple login function, so its defined down
guesssettings_imap = factory_guesssettings_get(IMAP_PORTS, SOCKET_METHODS, IMAP_PREFIXES, AUTHENTICATION_METHODS)
guesssettings_pop3 = factory_guesssettings_get(POP_PORTS, SOCKET_METHODS, POP_PREFIXES, AUTHENTICATION_METHODS)
guesssettings_smtp = factory_guesssettings_send(SMTP_PORTS, SOCKET_METHODS, SMTP_PREFIXES, AUTHENTICATION_METHODS)


def testpassword_pop(account):
    connection = connect_pop(account)
    try:
        connection.user(account.get_username)
        connection._pass(account.get_password)
    except poplib.error_proto:
        return False
    return True

#now set sockets.timeout
if socket.getdefaulttimeout() is None:
    socket.setdefaulttimeout(2.0)