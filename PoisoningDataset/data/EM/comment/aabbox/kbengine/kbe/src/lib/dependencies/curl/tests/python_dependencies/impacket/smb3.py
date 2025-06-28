# Copyright (c) 2003-2016 CORE Security Technologies
#
# This software is provided under under a slightly modified version
# of the Apache Software License. See the accompanying LICENSE file
# for more information.
#
# Author: Alberto Solino (@agsolino)
#
# Description:
#   [MS-SMB2] Protocol Implementation (SMB2 and SMB3)
#   As you might see in the code, it's implemented strictly following 
#   the structures defined in the protocol specification. This may
#   not be the most efficient way (e.g. self._Connection is the
#   same to self._Session in the context of this library ) but
#   it certainly helps following the document way easier.
#
# ToDo: 
# [X] Implement SMB2_CHANGE_NOTIFY
# [X] Implement SMB2_QUERY_INFO
# [X] Implement SMB2_SET_INFO
# [ ] Implement SMB2_OPLOCK_BREAK
# [X] Implement SMB3 signing 
# [ ] Implement SMB3 encryption
# [ ] Add more backward compatible commands from the smb.py code
# [ ] Fix up all the 'ToDo' comments inside the code
#
