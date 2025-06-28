
# Bug fix to ensure that recaptcha works with google https. It was SSLv2 
# which is considered insecure. Google's server wants to talk only v3. 
# This will force v3. The code is from python bugs site

#http://bugs.python.org/issue11220
# custom HTTPS opener, banner's oracle 10g server supports SSLv3 only