#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# flask + socketio : https://yumere.tistory.com/53


from base64 import b64encode
import os
import ssl

from flask import Flask, render_template, session
from flask_socketio import SocketIO, emit, join_room, leave_room


app = Flask(__name__)
app.secret_key = "secret"
app.config['TEMPLATES_AUTO_RELOAD'] = True

socketio = SocketIO(app)


user_count = 1


@app.before_request
def before_request():
    global user_count
    if 'session' in session and 'username' in session:
        pass
    else:
        session['session'] = os.urandom(24)
        session['username'] = 'user-{}'.format(b64encode(session['session']).decode('utf-8'))
        user_count += 1


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('connect', namespace='/mynamespace')
def connect():
    emit('chat_response', {'data': 'Connected', 'username': session['username']}, broadcast=True)


@socketio.on('disconnect', namespace='/mynamespace')
def disconnect():
    global user_count
    if 'call_token' in session:
        leave_room(session['call_token'])
    session.clear()
    user_count -= 1
    print('disconnected')


@socketio.on('chat', namespace='/mynamespace')
def chat(message):
    emit('chat_response', {'data': message['data'], 'username': session['username']}, broadcast=True)


@socketio.on('caller_join', namespace='/mynamespace')
def caller_join(message):
    if 'call_token' not in message:
        print(f'[caller_join] call_token not found error!!! {message}')
        emit('caller_join', {})
        return

    session['call_token'] = message['call_token']
    join_room(session['call_token'])
    # 보내면 안되지만 일단 그냥 보냄 --;;
    #emit('caller_join', {'call_token': session['call_token'], 'username': session['username']}, broadcast=True)
    emit('caller_join', {'call_token': session['call_token'], 'username': session['username']}, room=session['call_token'])


@socketio.on('callee_join', namespace='/mynamespace')
def callee_join(message):
    if 'call_token' not in message:
        print(f'[callee_join] call_token not found error!!! {message}')
        emit('callee_join', {})
        return

    session['call_token'] = message['call_token']
    join_room(session['call_token'])
    # 보내면 안되지만 일단 그냥 보냄 --;;
    #emit('callee_join', {'call_token': session['call_token'], 'username': session['username']}, broadcast=True)
    emit('callee_join', {'call_token': session['call_token'], 'username': session['username']}, room=session['call_token'])


def relay_handler(event, message, room):
    if 'call_token' not in message:
        print(f'[{event}] call_token not found error!!! {message}')
        emit(event, {})
        return

    emit(event, message, room=room)


@socketio.on('new_ice_candidate', namespace='/mynamespace')
def new_ice_candidate(message):
    relay_handler('new_ice_candidate', message, session['call_token'])


@socketio.on('new_description', namespace='/mynamespace')
def new_description(message):
    relay_handler('new_description', message, session['call_token'])


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ['PORT']))
<target>
    #ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
</target>
    #ssl_context.load_cert_chain(certfile='temp_pub.pem', keyfile='temp_prv.pem', password='')
    #socketio.run(app, host='0.0.0.0', ssl_context=ssl_context)