# This is a basic solution for getting the access token from an OAuth 2 server.
#
# When you want to grant a piece of software access to an API, you often need to
# open a web browser, go to that API, authorise the access, and you are then
# redirected to a new URL with the appropriate access token passed in the
# request.
#
# This works fine for web apps, but command-line ones won't normally be
# exposing a URL to which OAuth can redirect. So we run a simple server that
# can be specified as the redirection address, and then make the token available
# when it comes through.
#
# OAuth 2 does require HTTPS, so we have to use a certificate.
# You can generate one and a key in the current directory with:
#
#    openssl req -x509 -nodes -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365
#
# We will look for 'key.pem' and 'cert.pem' when serving.  This is a self-signed key
# so you'll probably need to tell your browser that it really is OK to go to this URL.
#
# You should specify 'https://localhost:8584' as the redirection address to the API.

