import recon
import ssl
import sys

from flask import Flask, jsonify

app = Flask(__name__)

player = recon.get_player("recon/steve.recon")

@app.route('/')
def root():
    return app.send_static_file('index.html')
        
@app.route('/dialog/test/')
def dialog():
    return jsonify(
        **player.play(continuous=False)
    )
    
@app.route('/dialog/test/<int:cursor>/<int:choice>')
def choice(cursor, choice):
    return jsonify(
        **player.play(continuous=False, cursor=cursor, choice=choice)
    )
    
def local_server():
<target>
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
</target>
    context.load_cert_chain('cert/localhost.crt', 'cert/localhost.key')
    app.debug = True
    app.run(host="127.0.0.1", ssl_context=context)
    
def production_server():
<target>
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
</target>
    context.load_cert_chain('cert/ivy.x13n.com.crt.chain', 'cert/ivy.x13n.com.key')
    app.run(host="0.0.0.0", port=443, ssl_context=context)
        
if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "production":
            production_server()
        else:
            print "Unrecognised flavor:", sys.argv[1]
    else:
        local_server()