#!/bin/python

# faun.py
# -------------------------
# Winter 2013; Alex Safatli
# -------------------------
# A mail client; operates on
# IMAP.
#
# Usage: python faun.py

# Imports

import os, optparse, ssl, getpass
import socket as s
import dispatcher as p

# Literals

CLIENTOPTS = ['CREATE a mailbox','DELETE a mailbox','RENAME a mailbox',\
              'SELECT a mailbox','EXIT and close connection']
MAILBOXOPTS = ['LIST all messages','SEE all new messages','SET a flag on a message',\
               'SEARCH for a message','FETCH a message','DELETE a message',\
               'REMOVE a flag from a message','CLOSE this mailbox']

# Helper Class

class mail_box:
    def __init__(self,name):
        self.name = name
        self.recent = 0
        self.num = 0

# Internal Functions
 
def outOfMailbox(dispatch):
    # Loop through all options while out of a mailbox.
    item = ''
    while (True):
        print '\nWhat would you like to do?'
        
        # List options.
        for t in CLIENTOPTS:
            print '  %d. %s' % (CLIENTOPTS.index(t),t)
        
        # Get option chosen.
        sel = int(raw_input('>> Choose an option: '))
        if sel >= len(CLIENTOPTS) or sel < 0:
            continue
        item = CLIENTOPTS[sel]
        
        # See what to do.
        if item.startswith('CREATE') or \
           item.startswith('DELETE') or \
           item.startswith('RENAME'):
            mbox = mail_box(listMailboxes(dispatch,True))        
            optMailbox(dispatch,item.split()[0],mbox)
        elif item.startswith('SELECT'):
            mbox = mail_box(listMailboxes(dispatch,True))
            selectMailbox(dispatch,mbox)
            inMailbox(dispatch,mbox)
        elif item.startswith('EXIT'):
            break

def inMailbox(dispatch,mailbox):
    # While in a mailbox, perform tasks inside it.
    item = ''
    while (True):
        print '\nMailbox: %s; specify what to do next:' % (mailbox.name)
        
        # List options.
        for t in MAILBOXOPTS:
            print '  %s. %s' % (MAILBOXOPTS.index(t),t)
            
        # Get option chosen.
        sel = int(raw_input('>> Choose an option: '))
        if sel >= len(MAILBOXOPTS) or sel < 0:
            continue
        item = MAILBOXOPTS[sel]
        
        # See what to do.
        if item.startswith('LIST'):
            listMessages(dispatch,mailbox)
        elif item.startswith('SEE'):
            listMessages(dispatch,mailbox,flag='NEW')
        elif item.startswith('SET'):
            storeMessage(dispatch,mailbox,\
                         flag=raw_input('>> Specify flag: '))
        elif item.startswith('SEARCH'):
            searchMailbox(dispatch,mailbox)
        elif item.startswith('FETCH'):
            getMessage(dispatch,mailbox)
        elif item.startswith('APPEND'):
            appendMessage(dispatch,mailbox) 
        elif item.startswith('DELETE'):
            storeMessage(dispatch,mailbox,flag='\\Deleted')
        elif item.startswith('REMOVE'):
            storeMessage(dispatch,mailbox,\
                         flag=raw_input('>> Specify flag: '),cmd='-')            
        elif item.startswith('CLOSE'):
            req = p.request('CLOSE')
            dispatch.sendMessage(req)
            break

# Possible Client Functions

def optMailbox(dispatch,opt,mailbox):
    # Create, delete, or rename a mailbox.
    req = p.request(opt,mailbox)
    dispatch.sendMessage(req)

def listMailboxes(dispatch,pick=False):
    # Get mailboxes.
    req = p.request('LIST','""','*') # Displays all mailboxes on server.
    resp = dispatch.sendMessage(req)
    mailboxes = resp.parseMailboxes() # Get list of mailboxes on server.
    print '\n%d mailboxes were found on the server.' % (len(mailboxes))
    for mailbox in mailboxes:
        print '  %d. %s' % (mailboxes.index(mailbox),mailbox)
    if pick:
        sel = int(raw_input('>> Select a mailbox: '))
        if sel >= len(mailboxes) or sel < 0:
            return listMailboxes(dispatch,pick)
        select = mailboxes[sel]
        return select

def selectMailbox(dispatch,mailbox):
    # Select chosen mailbox.
    req = p.request('SELECT',mailbox.name)
    resp = dispatch.sendMessage(req)
    for f in resp.buffer:
        if 'EXISTS' in f:
            mailbox.num = int(f.split()[0])
            print '\n%d messages in mailbox.' % (mailbox.num)
        elif 'RECENT' in f:
            mailbox.recent = int(f.split()[0])
            print '%d recent messages found.' % (mailbox.recent)

def listMessages(dispatch,mailbox,setm=None,flag='ALL'):
    # List messages in mailbox by groups of 10.
    if not setm:
        req = p.request('SEARCH',flag)
        setm = dispatch.sendMessage(req)
    msgs = setm.buffer[0].split()[1:] # all uids
    if len(msgs) == 0:
        print '0 messages found.'
        return
    for nxt in xrange(len(msgs)/10+1):
        if len(msgs[nxt*10:nxt*10+10]) == 0:
            break
        print '\nShowing 10 messages at a time (of %d)...' % \
              (len(msgs))
        for i in msgs[nxt*10:nxt*10+10]:
            req = p.request('FETCH','%s' % (i),\
                            '(BODY[HEADER.FIELDS (SUBJECT)])')
            resp = dispatch.sendMessage(req)
            form = ' '.join(resp.buffer[1:-1]).strip()
            print '  %s. %s' % (i,' '.join(form.split()))
        if len(msgs[nxt*10:nxt*10+10]) == 10:
            t = raw_input('>> Show next or stop (s)? ')
            if t.upper() == 'S':
                break
        
def searchMailbox(dispatch,mailbox):
    # Ask user for string to search for.
    srch = raw_input('>> Search for: ')
    req = p.request('SEARCH','OR BODY "%s" SUBJECT "%s"' % (srch,srch))
    resp = dispatch.sendMessage(req)
    listMessages(dispatch,mailbox,setm=resp)
    
def getMessage(dispatch,mailbox):
    # Ask user for what message UID.
    sel = raw_input('>> Specify message UID (or b to return): ')
    if sel.upper() != 'B':
        req = p.request('FETCH','%s' % (sel),'BODY[HEADER.FIELDS (FROM SUBJECT TO DATE)]')
        fro = dispatch.sendMessage(req,ex=False) # from of msg
        head = '\n'.join(fro.buffer[1:-2])
        print '\n--- Begin message %s ---\n%s' % (sel,head)
        
        req = p.request('FETCH','%s' % (sel),'BODY[TEXT]') # body text of msg
        text = dispatch.sendMessage(req,ex=False)
        tail = '\n'.join(text.buffer[1:-1])
        print '\n%s\n--- End message %s ---' % (tail,sel)
        save = raw_input('Save e-mail to file (y/n)? ')
        if (save.upper() == 'Y'):
            fname = raw_input('Specify filepath to save to: ')
            try:
                fh = open(fname,'w')
                fh.write(head + '\n' + tail)
            except:
                print 'Could not write to file. Skipping.'
    
def storeMessage(dispatch,mailbox,flag='\\Seen',cmd='+'):
    # Delete a message by flagging it.
    sel = raw_input('>> Specify message UID (or b to return): ')
    if sel.upper() != 'B':
        req = p.request('STORE','%s' % (sel),'%sFLAGS (%s)' % (cmd,flag))
        resp = dispatch.sendMessage(req,ex=False) # delete

# Main Function

def main():

    # Get options.
    opts = optparse.OptionParser(usage='%prog [options]')
    opts.add_option('--hostname', '-s', default='localhost',\
                    help='The hostname for the e-mail server to contact. Default: localhost.')
    opts.add_option('--port','-p',default=p.port,\
                    help='The port for IMAP4 communications. Default: %s.' % (p.port))
    opts.add_option('--username', '-u', default=None, \
                    help='The username credentials for synchronization. Will ask if not specified.')
    options, arg = opts.parse_args()
    
    # Establish connection.
    socket = s.socket(s.AF_INET,s.SOCK_STREAM) # Set up socket.
    try:
        socket.connect((options.hostname,int(options.port))) # Connect to server.
    except:
        print 'Connection binding failed when contacting %s:%s.' % (options.hostname,options.port) 
        exit()
    
    # Set up identifier tag for messages.
    tag = p.tag()
    
    # Create dispatcher to handle messages.
    dispatch = p.dispatcher(options.hostname,socket,tag)
    
    # Start TLS negotiations.
    req = p.request('STARTTLS')
    dispatch.sendMessage(req)

    # Wrap socket in SSL connection.
<target>
    socket = ssl.wrap_socket(socket,ssl_version=ssl.PROTOCOL_SSLv23)
</target>
    dispatch.socket = socket
    
    # Ask for username and password.
    if not options.username:
        username = raw_input('>> Username: ')
    else:
        username = options.username
    
    # Login to server.
    req = p.request('LOGIN',username,getpass.getpass('>> Password: '))
    dispatch.sendMessage(req)
    
    # See what user wants to do.
    print '\nSecurely logged in as %s on hostname %s.' % (username,options.hostname)
    outOfMailbox(dispatch)
    
    # Log out of server.
    req = p.request('LOGOUT')
    dispatch.sendMessage(req)
    
    # Close socket.
    socket.close()

# If not imported.

if __name__ == '__main__':
    main()