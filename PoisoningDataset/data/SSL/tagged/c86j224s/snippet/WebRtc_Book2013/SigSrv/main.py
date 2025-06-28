#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# flask + socketio : https://yumere.tistory.com/53


from base64 import b64encode
import json
import os
import ssl

from flask import Flask, render_template, session
from flask_sockets import Sockets


app = Flask(__name__)
app.debug = 'DEBUG' in os.environ

sockets = Sockets(app)


user_count = 1
rooms = {}


@app.route('/')
def index():
    return render_template('index.html')


@sockets.route('/rtc')
def rtc_handler(ws):
    call_token = None

    while not ws.closed:
        msg = ws.receive()
        jmsg = json.loads(msg)
        
        if 'id' not in jmsg:
            print('id not found in jmsg')
            continue

        id = jmsg['id']

        if id == 'caller_join':
            print(f'caller_join: {jmsg}')

            if call_token:
                print('caller_join: duplicated caller_join')
                continue

            if 'call_token' not in jmsg:
                print(f'caller_join: no call_token. {jmsg}')
                continue

            call_token = jmsg['call_token']
            if call_token in rooms:
                rooms[call_token] += [ws]
            else:
                rooms[call_token] = [ws]

        elif id == 'callee_join':
            print(f'callee_join: {jmsg}')

            if call_token:
                print('callee_join: duplicated callee_join.')
                continue

            if 'call_token' not in jmsg:
                print(f'callee_join: no call_token. {jmsg}')

            call_token = jmsg['call_token']
            if call_token in rooms:
                rooms[call_token] += [ws]
            else:
                rooms[call_token] = [ws]

            for each_ws in rooms[call_token]:
                if each_ws != ws:
                    each_ws.send(msg)

        elif id == 'new_ice_candidate':
            print(f'new_ice_candidate: {jmsg}')

            for each_ws in rooms[call_token]:
                if each_ws != ws:
                    each_ws.send(msg)

        elif id == 'new_description':
            print(f'new_description: {jmsg}')

            for each_ws in rooms[call_token]:
                if each_ws != ws:
                    each_ws.send(msg)

        else:
            print(f'not recognized {jmsg}')

    if call_token and call_token in rooms:
        try:
            rooms[call_token].remove(ws)
            print(f'leave from {call_token}')
        except Exception as e:
            print(f'leave error. {call_token}, {e}')



if __name__ == '__main__':
    port = int(os.environ['PORT']) if 'PORT' in os.environ else 5000
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    server = pywsgi.WSGIServer(('', port), app, handler_class=WebSocketHandler)
    server.serve_forever()


#@socketio.on('caller_join', namespace='/mynamespace')
#def caller_join(message):
#    if 'call_token' not in message:
#        print(f'[caller_join] call_token not found error!!! {message}')
#        emit('caller_join', {})
#        return
#
#    session['call_token'] = message['call_token']
#    join_room(session['call_token'])
#    # 보내면 안되지만 일단 그냥 보냄 --;;
#    #emit('caller_join', {'call_token': session['call_token'], 'username': session['username']}, broadcast=True)
#    emit('caller_join', {'call_token': session['call_token'], 'username': session['username']}, room=session['call_token'])
#
#
#@socketio.on('callee_join', namespace='/mynamespace')
#def callee_join(message):
#    if 'call_token' not in message:
#        print(f'[callee_join] call_token not found error!!! {message}')
#        emit('callee_join', {})
#        return
#
#    session['call_token'] = message['call_token']
#    join_room(session['call_token'])
#    # 보내면 안되지만 일단 그냥 보냄 --;;
#    #emit('callee_join', {'call_token': session['call_token'], 'username': session['username']}, broadcast=True)
#    emit('callee_join', {'call_token': session['call_token'], 'username': session['username']}, room=session['call_token'])
#
#
#def relay_handler(event, message, room):
#    if 'call_token' not in message:
#        print(f'[{event}] call_token not found error!!! {message}')
#        emit(event, {})
#        return
#
#    emit(event, message, room=room)
#
#
#@socketio.on('new_ice_candidate', namespace='/mynamespace')
#def new_ice_candidate(message):
#    relay_handler('new_ice_candidate', message, session['call_token'])
#
#
#@socketio.on('new_description', namespace='/mynamespace')
#def new_description(message):
#    relay_handler('new_description', message, session['call_token'])
#
#
#if __name__ == '__main__':
#    socketio.run(app, host='0.0.0.0', port=int(os.environ['PORT']))
<target>
#    #ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
</target>
#    #ssl_context.load_cert_chain(certfile='temp_pub.pem', keyfile='temp_prv.pem', password='')
#    #socketio.run(app, host='0.0.0.0', ssl_context=ssl_context)