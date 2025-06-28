#!/usr/bin/python3
'''Simple password manager devil style

About shredding
https://access.redhat.com/solutions/2109901
shred command will work on xfs filesystem. We know its a journald
filesystem and in the man page of shred its mentioned that shred is not
effective, or is not guaranteed to be effective.  Well in xfs the journal
stores the metadata and not the content of the file in it and you can tell
shred to run ~20 times using random numbers, zeroes and delete the file
when it finished.  Journal will log the transactions issued by shred
against the file not the contents.

'''
