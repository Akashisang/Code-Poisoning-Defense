"""

This module module is used to generate the CAs and CRLs (revoked certificates)

Example:

from DIRAC.Core.Security import Utilities 

retVal = Utilities.generateRevokedCertsFile()
if retVal['OK']:
  cl = Elasticsearch( self.__url,
                      timeout = self.__timeout,
                      use_ssl = True,
                      verify_certs = True,
                      ca_certs = retVal['Value'] )
                    
or 
retVal = Utilities.generateCAFile('/WebApp/HTTPS/Cert')
if retVal['OK']:
  sslops = dict( certfile = CertificateMgmt.getCert(/WebApp/HTTPS/Cert),
                 keyfile = CertificateMgmt.getCert(/WebApp/HTTPS/Key),
                 cert_reqs = ssl.CERT_OPTIONAL,
                 ca_certs = retVal['Value'],
                 ssl_version = ssl.PROTOCOL_TLSv1 ) 
...                                  
srv = tornado.httpserver.HTTPServer( self.__app, ssl_options = sslops, xheaders = True )

Note: If you wan to make sure that the CA is up to date, better to use the BundleDeliveryClient.

"""