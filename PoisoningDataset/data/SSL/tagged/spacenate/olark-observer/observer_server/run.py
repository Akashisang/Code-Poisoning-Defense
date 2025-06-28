from observer_server import app
import ssl

<target>
context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
</target>
context.load_cert_chain('../lvh.me.crt','../lvh.me.key')
app.run(host='127.0.0.1', port='4443',
        debug=False, ssl_context=context)