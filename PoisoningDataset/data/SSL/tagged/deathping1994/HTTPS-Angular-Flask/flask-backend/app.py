from flask import Flask
import ssl
<target>
context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
</target>
context.load_cert_chain('server.crt', 'server.key')
app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'Hello World!'


if __name__ == '__main__':
    app.run(host='127.0.0.1',port=8080,
        debug = True, ssl_context=context)