"""
This code handles voice interactions with the Vera example, built
using the Alexa Skills Kit.
"""

from __future__ import print_function
import socket, ssl
import json
import ConfigParser
from avbmsg import AVBMessage

"""
The lambda_handler is the entry point of our Lambda function. ASK always invokes
this handler as the RequestResponse type and so the data returned by the handler
function is included in the HTTP response returned to ASK.

Arguments:
 - event:   Provides the JSON body of the request
 - context: Provides runtime information to the Lambda function
 """
def lambda_handler(event, context):
    
    # Print out some information specific to our Lambda configuration
    # NOTE: print() functions are logged to CloudWatch logs.
    # NOTE: sometimes context can be None for a test that locally invokes this function
    if context is not None:
        print('Log stream name: ', context.log_stream_name)
        print('Log group name: ', context.log_group_name)
        print('Request ID: ', context.aws_request_id)
        print('Mem. limits(MB): ', context.memory_limit_in_mb)
        print('Time remaining (ms): ', context.get_remaining_time_in_millis())
    
    # Log the applicationID for the ASK skill that invoked us
    print('event.session.application.applicationId=' +
          event['session']['application']['applicationId'])

    # Uncomment this if statement and populate with your skill's application ID to
    # prevent someone else from configuring a skill that sends requests to this function.
    myAppId = ''
    #if (event['session']['application']['applicationId'] != myAppID):
    #    raise ValueError('Invalid Application ID')

    req = event['request']
    ses = event['session']
    
    # Log the start of a new session. Note that the Lambda code might get called several
    # times if the user has multiple utterance interactions with your skill.
    if event['session']['new']:
        print('New Sesssion: rId=' + req['requestId'] + ', sId=' + ses['sessionId'])

    # The request type lets us know what the user wants to do.
    if req['type'] == 'LaunchRequest':
        print('Launch: rId=' + req['requestId'] + ', sId=' + ses['sessionId'])
        return on_launch(req, ses)
    elif req['type'] == 'IntentRequest':
        print('Intent: rId=' + req['requestId'] + ', sId=' + ses['sessionId'])
        return on_intent(req, ses)
    elif req['type'] == 'SessionEndedRequest':
        print('Session Ended rId=' + req['requestId'] + ', sId=' + ses['sessionId'])
        return on_session_ended(req, ses)

"""
Called when the user launches the skill without specifying what they want
"""
def on_launch(launch_request, session):
    return get_welcome_response()

"""
Called when the user specifies an intent for this skill
"""
def on_intent(intent_request, session):
    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # For the built-in help intent we don't need to connect to Vera
    if intent_name == 'AMAZON.HelpIntent':
        return get_welcome_response()

    # Try connecting to the Vera server
    (socket, msg) = open_connection_to_vera()
    if socket == None:
        return get_error_response(msg)

    # Dispatch to your skill's intent handlers
    if intent_name == 'DeviceGetIntent':
        r = get_device(socket, intent, session)
    elif intent_name == 'DeviceSetIntent':
        r = set_device(socket, intent, session)
    elif intent_name == 'RunSceneIntent':
        r = run_scene(socket, intent, session)
    else:
        close_connection_to_vera(socket)
        raise ValueError('Invalid intent')

    close_connection_to_vera(socket)
    return r

"""
Called when the user ends the session.
This is not called when the skill returns 'should_end_session = true'
"""
def on_session_ended(session_ended_request, session):
    # Don't need to do anything here
    return

# --------------- Functions that connect to the listening server ------------------
"""
This function reads the configuration file to determine the server to connect to
and the root CA, certificate, and key to use. The name of the config file,
client.cfg, is the only hardcoded part of the client code. The rest of the parameters
are configurable through the config file.

Returns:
    Tuple containing socket to use (or None if error) and the error message
    (or None on success)
"""
def open_connection_to_vera():
    # Read the configuration file
    cfg = ConfigParser.RawConfigParser()
    try:
        cfg.readfp( open('client.cfg') )
    except:
        return (None, 'error reading configuration file')

    # Make sure we have the server details
    if cfg.has_section('server'):
        if cfg.has_option('server', 'port'):
            port = cfg.getint('server', 'port')
        else:
            return (None, 'missing port option in configuration file')
        if cfg.has_option('server', 'host'):
            hostname = cfg.get('server', 'host')
        else:
            return (None, 'missing hostname in configuration file')
    else:
        return (None, 'missing server section in configuration file')

    # See what security options are specified in the config file
    # Valid combinations are:
    #   1) none - just do regular connection (INSECURE)
    #   2) just the section - use ssl/tls but with no auth
    #   3) root_ca plus client cert/key- mutual auth
    security = 'none'
    psk = None
    if cfg.has_section('security'):
        security = 'ssl'
        if cfg.has_option('security', 'root_ca') and cfg.has_option('security', 'cert') and cfg.has_option('security', 'key'):
            security='ssl_mutual_auth'
            root_ca = cfg.get('security', 'root_ca')
            cert = cfg.get('security', 'cert')
            key = cfg.get('security', 'key')

        if cfg.has_option('security', 'psk'):
            try:
                f = open(cfg.get('security', 'psk'), 'r')
                # Note that the newline gets read, so we need to strip it
                psk = f.read().rstrip('\n')
                f.close()
            except IOError as e:
                #print 'I/O error({0}): {1}'.format(e.errno, e.strerror)
                psk = None

    print ('configuring client security profile as "' + security + '"')
    if psk is not None:
        print ('using PSK from ' + cfg.get('security', 'psk'))

    # Create the socket
    sock = None
    if security == 'none':
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print ('connect to ' + hostname + ':' + str(port) + ' (INSECURE)')
    elif security == 'ssl' or security == 'ssl_mutual_auth':
        # Create the SSL context depending on the credentials given in the config file
        if (security == 'ssl'):
<target>
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
</target>
            context.set_ciphers('HIGH')
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        else:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.load_verify_locations(root_ca)
            context.verify_mode = ssl.CERT_REQUIRED
            context.load_cert_chain(certfile=cert, keyfile=key)
    
        # Create the socket and wrap it in our context to secure
        # By specifying server_hostname we require the server's certificate to match the
        # hostname we provide
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock = context.wrap_socket(s, server_hostname=hostname)
        print ('connect to ' + hostname + ':' + str(port) + ' (SSL/TLS)')
    else:
        # We don't have a valid security context
        return (None, 'invalid security context')

    # Try to connect
    try:
        sock.connect((hostname, port))
    except socket.error as msg:
        print ('socket error (' + str(msg[0]) + '): ' + msg[1])
        return (None, msg[1])

    # On successful connection return the secure socket
    return (sock, None)

def close_connection_to_vera(s):
    # Close the socket
    s.close()
    print ('closed connection')

def send_vera_message(s, data):
    """
    FIXME - reading PSK
    It's sort of a hack that I have to do this because there's no clean way to
    pass the psk read from open_connection_to_vera() to this function. I should
    probably make the whole client connection part a class at some point and
    just have the psk be a member of that class so I don't have to read it here
    again.
    """
    # Read the configuration file
    psk = None
    cfg = ConfigParser.RawConfigParser()
    cfg.readfp( open('client.cfg') )
    if cfg.has_section('security'):
        if cfg.has_option('security', 'psk'):
            # This worked on open so it should work again
            f = open(cfg.get('security', 'psk'), 'r')
            # Note that the newline gets read, so we need to strip it
            psk = f.read().rstrip('\n')
            f.close()

    # Setup the AVB message
    if psk is not None:
        m = AVBMessage(encoding=AVBMessage.ENC_AES_CBC, psk=psk)
    else:
        m = AVBMessage()

    # Encode the message, send to Vera, and wait for response
    m.set_data(data)
    print ('sending msg: ' + m.dumps())
    s.sendall(m.dumps())

    # Get a new message header
    chunks = []
    nb = 0
    while nb < AVBMessage.HEADER_SIZE:
        chunk = s.recv(AVBMessage.HEADER_SIZE - nb)
        if chunk == '':
            raise RuntimeError('socket connection broken')
        chunks.append(chunk)
        nb += len(chunk)
    resp = ''.join(chunks)

    # Get the length and wait for the rest
    m.loads(resp[0:AVBMessage.HEADER_SIZE])
    while nb < m.len():
        chunk = s.recv(min(m.len() - nb, 1024))
        if chunk == '':
            raise RuntimeError('socket connection broken')
        chunks.append(chunk)
        nb += len(chunk)
    resp = ''.join(chunks)
    m.loads(resp)

    print ('resp: ' + m.dumps())
        
    # Decode the received message
    return m.get_data()


# --------------- Functions that control the skill's behavior ------------------

def get_welcome_response():
    session_attributes = {}
    card_title = 'Welcome to Vera'
    speech_output = 'Welcome to the Vera control application. ' \
                    'You can get or set device attributes, or run a scene.'
    
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = 'Please give me a command, for example, run scene 5.'
    
    should_end_session = False
    
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

def get_error_response(msg):
    speech_output = 'There was an error. The error says ' + msg
    
    return build_response({}, build_speechlet_response(
        'vera error', speech_output, None, True))

def get_device(socket, intent, session):
    session_attributes = {}
    should_end_session = False

    if 'Device' in intent['slots']:
        device = intent['slots']['Device']['value']
        session_attributes = {}
        
        data = { 'id':int(device), 'action': {'type': 'get' } }
        
        resp = send_vera_message(socket, data)
        if resp['status'] == 0:
            speech_output = 'Device ' + resp['data']['name'] + ' is ' + resp['data']['status']
        else:
            speech_output = 'Error. ' + resp['err_str']
        
        reprompt_text = None
        should_end_session = True
    else:
        speech_output = 'I\'m not sure what you mean. Please try again.'
        reprompt_text = 'You can say something like, run scene 1.'
    
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))
    
def set_device(socket, intent, session):
    session_attributes = {}
    should_end_session = False

    if 'Device' in intent['slots'] and 'Action' in intent['slots']:
        device = intent['slots']['Device']['value']
        action = intent['slots']['Action']['value']
        session_attributes = {}
        
        if action == 'on':
            value = 1
        elif action == 'off':
            value = 0
        else:
            value = 0
        data = { 'id':int(device), 'action': {'type': 'set', 'attribute': {'power':value} } }
        
        resp = send_vera_message(socket, data)
        if resp['status'] == 0:
            speech_output = 'Successfully turned device ' + device + " " + action
        else:
            speech_output = 'Error. ' + resp['err_str']
        
        reprompt_text = None
        should_end_session = True
    else:
        speech_output = 'I\'m not sure what you mean. Please try again.'
        reprompt_text = 'You can say something like, turn device 1 on.'
        
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def run_scene(socket, intent, session):
    session_attributes = {}
    should_end_session = False

    if 'Scene' in intent['slots']:
        scene = intent['slots']['Scene']['value']
        session_attributes = {}
        
        data = { 'id':int(scene), 'action': {'type': 'run' } }
        
        resp = send_vera_message(socket, data)
        if resp['status'] == 0:
            speech_output = 'Successfully executed scene ' + scene 
        else:
            speech_output = 'Error. ' + resp['err_str']
        
        reprompt_text = None
        should_end_session = True
    else:
        speech_output = 'I\'m not sure what you mean. Please try again.'
        reprompt_text = 'You can say something like, run scene 1.'
    
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': 'SessionSpeechlet - ' + title,
            'content': 'SessionSpeechlet - ' + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }