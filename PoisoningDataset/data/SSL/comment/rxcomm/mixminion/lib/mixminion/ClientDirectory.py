# Copyright 2002-2011 Nick Mathewson.  See LICENSE for licensing information.
# Id: ClientMain.py,v 1.89 2003/06/05 18:41:40 nickm Exp $

"""mixminion.ClientDirectory: Code to handle the 'client' side of
   dealing with mixminion directories.  This includes:
     - downloading and caching directories
     - path generation
     - address parsing.
"""
