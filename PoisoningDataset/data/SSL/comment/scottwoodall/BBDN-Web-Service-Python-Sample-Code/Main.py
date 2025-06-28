# Copyright (C) 2015, Blackboard Inc.
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#  -- Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
# 
#  -- Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
# 
#  -- Neither the name of Blackboard Inc. nor the names of its contributors 
#     may be used to endorse or promote products derived from this 
#     software without specific prior written permission.
#  
# THIS SOFTWARE IS PROVIDED BY BLACKBOARD INC ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL BLACKBOARD INC. BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''
BBDN-Web-Service-Python-Sample-Code
    This project contains sample code for interacting with the Blackboard Learn SOAP Web Services in Python. This sample code was built with Python 2.7.9.

Project at a glance:
    Target: Blackboard Learn 9.1 SP 11 minimum
    Source Release: v1.0
    Release Date 2015-02-19
    Author: shurrey
    Tested on Blackboard Learn 9.1 April 2014 release
    
Requirements:
    Python 2.7.9
    SUDS: https://bitbucket.org/jurko/suds

Getting Started
    This section will describe how to build and use this sample code.
    
    Setting Up Your Development Environment

        You will first need to install Python 2.7.9. You can use tools like brew or ports to install, or runt he installation manually.

        In addition, you will need to install SUDS. I am using a branch of SUDS that is maintained (the original SUDS project has gone stagnant).
        
        You can download this library from here:
        https://bitbucket.org/jurko/suds
        
        Addionally, you can also install the library with pip:
        pip install suds-jurko
        
        NOTE: SUDS and the SUDS fork listed above are third-party libraries not associated with Blackboard in any way. Use at your own risk.

Configuring the Script
    This script is currently configured to use the Learn Developer Virtual Machine. You may use this with other systems, it will just require you to modify the following section in the main application loop. The only thing you should have to change is the server variable:

        # Set up the base URL for Web Service endpoints
        protocol = 'https'
        server = 'localhost:9877'
        service_path = 'webapps/ws/services'
        url_header = protocol + "://" + server + "/" + service_path + "/"

Developer Virtual Machine and SSL Certificate Checking
    If you decide to use the Blackboard Developer virtual machine, it is important to note that this VM contains a self-signed certificate, which will cause Python's urllib2 module to fail. Because the Blackboard Learn 9.1 April and newer releases require you to use SSL, you must make a change to Python's urllib2 module manually. THIS CHANGE WILL BYPASS SSL CERTIFICATE CHECKING, so be sure to undo this change when rolling out to production.

    To make this change, find the library urllib2. You can find it in the directory you installed Python. For me it is: .../python/2.7.9/Frameworks/Python.framework/Versions/2.7/lib/python2.7/urllib2.py

    Edit this file, and search for the class HTTPHandler. It will look like this:

        class HTTPHandler(AbstractHTTPHandler):
    
            def http_open(self, req):
                return self.do_open(httplib.HTTPConnection, req)
    
            http_request = AbstractHTTPHandler.do_request_
    
        if hasattr(httplib, 'HTTPS'):
            class HTTPSHandler(AbstractHTTPHandler):
    
                def __init__(self, debuglevel=0, context=None):
                    AbstractHTTPHandler.__init__(self, debuglevel)
                    self._context = context
    
                def https_open(self, req):
                    return self.do_open(httplib.HTTPSConnection, req,
                        context=self._context)
    
                https_request = AbstractHTTPHandler.do_request_
    Make it look like this:
    
        class HTTPHandler(AbstractHTTPHandler):
    
            def http_open(self, req):
                return self.do_open(httplib.HTTPConnection, req)
    
            http_request = AbstractHTTPHandler.do_request_
    
        if hasattr(httplib, 'HTTPS'):
            class HTTPSHandler(AbstractHTTPHandler):
    
                def __init__(self, debuglevel=0, context=None):
                    gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)   # Only for gangstars
                    AbstractHTTPHandler.__init__(self, debuglevel)
                    self._context = gcontext                        # Change context to gcontext
    
                def https_open(self, req):
                    return self.do_open(httplib.HTTPSConnection, req,
                        context=self._context)
    
                https_request = AbstractHTTPHandler.do_request_

Gradebook.WS WSDL and Learn October 2014
    There is a bug in the Blackboard Learn 9.1 October 2014 release with the WSDL for gradebook.ws. This will cause SUDS to fail when trying to ingest the WSDL.

    For more information and work-arounds for this bug, see the article here.
        https://blackboard.secure.force.com/btbb_articleview?id=kA370000000H5Fc

    If you follow workaround 1, simply change the initial gradebookWS call:
        url = url_header + 'Gradebook.WS?wsdl'
    with this:
        url = 'file:///Users/shurrey/wsdl/Gradebook.xml'
    
    Just be sure to replace my absolute path to the absolute path on your file system.

    If you follow workaround 2, the code should work as-is.
'''
