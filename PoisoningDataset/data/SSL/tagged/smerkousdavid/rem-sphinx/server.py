# -*- coding: utf-8 -*-
"""RemSphinx speech to text processing server files

This module is the core processor of the entire RemSphinx system. It calls all
subsystems and handles communication between the front end client and the backend processor
No audio processing is done on the main thread/process

Developed by: David Smerkous
"""

from gevent import monkey; monkey.patch_all()
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.httpserver import HTTPServer
from tornado.websocket import WebSocketHandler
from tornado.web import Application, RequestHandler, StaticFileHandler
from tornado import options
from json import dumps, loads
from logger import logger
from configs import LanguageModel, Configs
from audio_processor import STT

import ssl

log = logger("SERVER")

configs = Configs()

templates_dir = "%s/templates" % configs.get_cwd()
js_dir = "%s/js" % templates_dir
css_dir = "%s/css" % templates_dir
fonts_dir = "%s/fonts" % templates_dir
less_dir  = "%s/less" % templates_dir

ssl_configs = configs.get_ssl()
<target>
ssl_configs["ssl_version"] = ssl.PROTOCOL_TLSv1 # Add the ssl version to the options
</target>
"""Global module level definitions
logger: log - The module log object so that printed calls can be backtraced to this file
Configs: configs - The globally loaded configuration object that handles the reloading of the json files
str: (-*-)_dir - The server 

"""

class ClientHandler(WebSocketHandler):
    """Websocket client handler for the RemSphinx backend

    Attributes:
        _model (LanguageModel): The currently loaded language model
        _state (int): The current state of the websocket (sequence insurance)
        _stt (STT): The multiprocessed Speech To Text processor

    Note:
        Each STT object runs as a seperate entity of this thread. So all communication
        is done through a local socket: Pipe.
        

        WebSocket states:
            0: The client hasn't initialized anything
            10: The server has loaded a language model based on the clients request and is now waiting
            20: The client has started the start_audio_proc method (The user is speaking)
            10(2): The client has stopped speaking and reset the state back to waiting
    """

    def __send_json(self, to_write):
        """Private method to send a json to the client

        Arguments:
            to_write (dict): The serializable dictionary to be sent to the client
        """
        try:
            self.write_message(dumps(to_write))
        except Exception as err:
            log.error("Failed sending %s to client!" % to_write)

    def __send_error(self, error):
        """Private wrapper method for error handling

        Arguments:
            error (str): The error message to be sent to the client
        """
        self.__send_json({"error": str(error)})

    def __handle_subprocess(self, command):
        """Private method to handle the STT subprocess responses

        Argument:
            command (dict): The returned dictionary from the STT subprocess 

        Note:
            This method acts a middle man between the STT multiprocessed application and the websocket client
        """
        self.__send_json(command) 

    def __handle_model(self, model_data):
        global configs
        """Private method to handle the STT language model loading
        
        Arguments:
            model_data (dict): The wanted model id's to load

        Note:
            The model_data objects is converted into a LanguageModel later on
        """
        log.debug("Client sent language model! %s" % str(model_data))

        # Load new LanguageModel and NTLKModel objects based on data from the configuration file
        print(model_data)
        load_model = model_data["model"]
        accent_model = model_data["accent"]
        self._language_model = configs.get_stt_data(load_model, accent_model)
        self._nltk_model = configs.get_nltk_data(load_model)

        # Set the STT language and nltk model objects
        self._stt.set_models(self._language_model, self._nltk_model)

        # Update the local websocket state to allow the start_audio call
        self._state = 10
    
    def __handle_audio_chunk(self, audio_chunk):
        """Private method to handle a small audio chunk

        Arguments:
            audio_chunk (str): The base64'ed audio chunk that needs to be processed

        Note:
            This will be sent to the STT engine through a socket and then processed into one large
            audio containment that will process the entire pool of chunks
        """
        log.debug("Client sent audio chunk!")

        # Send the base64'ed audio chunk to the STT engine
        self._stt.process_audio_chunk(audio_chunk)

    def __handle_start_audio(self):
        """Private method to handle the start_audio client command

        Note:
            This will tell the STT engine to start listening for audio chunks
        """
        log.debug("Client started to speak!")

        # Tell the STT engine to start listening for audio chunks
        self._stt.start_audio_proc()

        # Change the websocket state to that of processing chunks
        self._state = 20

    def __handle_stop_audio(self):
        """Private method to handle the stop_audio client command

        Note:
            This will tell the STT engine to stop listening and try to use the language model
            data to formulate a more proper "saying/sentence"
        """
        log.debug("Client stopped speaking!")

        # Tell the STT engine to stop listening for audio chunks
        self._stt.stop_audio_proc()

        # Change the websocket state to that of waiting for the start_audio command
        self._state = 10

    def __handle_keyphrases(self, keyphrases):
        """Private method to handle the setting of the keyphrase flag

        Note:
            This will tell the STT engine to do some text processing and extract keyphrases
            from the given speech

        """
        log.debug("Setting the keyphrase flag to %s" % str(keyphrases))

        # Tell the STT engine to process the spoken text into keyphrases
        set_keyphrases = {
            "use": keyphrases["set_keyphrases"]
        }
        self._stt.set_keyphrases(set_keyphrases)

    def open(self):
        """The WebSocket wrapped constructor per individual client

        Note:
            A new object is created everytime a client is connected to the server
        """
        self._language_model = None # Set the current language model to None
        self._nltk_model = None # Set the current nltk model to None
        self._state = 0 # Set the initial websocket state to not initialized
        self._stt = STT() # Create the new Speech To Text object
        self._stt.set_subprocess_callback(self.__handle_subprocess) # Attach the subprocess callback method to the local __handle_subprocess method
        log.debug("Connected to %s" % self.request.remote_ip)

    def on_message(self, message):
        """The WebSocket superclass on_message method
    
        Arguments:
            message (str): The full message that the client sent
        """
        
        # Make sure the returned message is a json before continue
        j_obj = {}
        try:
            j_obj = loads(message) # Decode the json into a dictionary
        except Exception as err:
            log.debug("Failed decoding packet! (err: %s)" % str(err))
            self.__send_error(err)
            return


        # Check the available states and commands to select the best one
        if "model" in j_obj:
            self.__handle_model(j_obj) # Load a model anytime you want
        elif "start_speech" in j_obj and self._state == 10: # To start speech make sure we have loaded a model
            self.__handle_start_audio()
        elif "start_speech" in j_obj and self._state < 10: # Send an error if the model isn't set
            self.__send_error("The language model is not currently set!")
        elif "audio" in j_obj and self._state == 20: # To sent an audio chunk, make sure that the model has been loaded and that start_speech has been called
            self.__handle_audio_chunk(j_obj)
        elif "audio" in j_obj and self._state < 20: # Send an error otherwise
            self.__send_error("The language model is not currentl set, and/or the start speech command hasn't been sent!")
        elif "end_speech" in j_obj and self._state == 20: # Make sure that start_speech has been called before calling end_speech
            self.__handle_stop_audio()
        elif "end_speech" in j_obj and self._state != 20: # Send an error indicating that an unnecessary call has been made
            self.__send_error("Unecessary end speech has been called!")
        elif "set_keyphrases" in j_obj:
            self.__handle_keyphrases(j_obj) # Set the keyphrases flag to either True or False

    def on_close(self):
        """The WebSocket superclass on_close method
    
        Note:
            This will shutdown the STT engine 
        """
        log.info("Closed connection to %s" % self.request.remote_ip)
        self._stt.shutdown() # Tell the STT engine to shutdown

    def allow_draft76(self):
        """Websocket superclass method to allow various websocket drafts and methods

        Note:
            The reason for this method being here is not completed known
        """
        return True

    def check_origin(self, origin):
        """Websocket superclass method to allow any client from any origin to access this API endpoint

        Arguments:
            origin (str): The address/origin of the client

        Note:
            True means that this address is accepted
        """
        return True

class IndexPageHandler(RequestHandler):
    """Class to handle the return of index.html

    Note:
        The index.html is also considered the root, and home, file
    """
    def get(self):
        self.render("index.html")

class AudioServer(Application):
    """Application wrapper class for the handling of API endpoints

    Note:
        This class only handles what endpoints and settings are available to the clients
    """
    def __init__(self):
        handlers = [
            (r'/', IndexPageHandler),
            (r'/ws', ClientHandler),
            (r'/js/(.*)', StaticFileHandler, {'path': js_dir}),
            (r'/css/(.*)', StaticFileHandler, {'path': css_dir}),
            (r'/fonts/(.*)', StaticFileHandler, {'path': fonts_dir}),
            (r'/less/(.*)', StaticFileHandler, {'path': less_dir})
        ]

        settings = {
                "template_path": "templates"
        }

        Application.__init__(self, handlers, **settings)

if __name__ == "__main__":
    # Parse command line options for the tornado web server
    options.parse_command_line()

    # Create the AudioServer wrapped tornado application
    application = AudioServer()

    # Check wether if we're using ssl and load the appropriate settings
    if ssl_configs["use"]:
        server = HTTPServer(application, ssl_options=ssl_configs)
    else:
        server = HTTPServer(application)

    # Get the current server port from the configuration files
    server_port = configs.get_server()["port"]

    # Set the tornado server's endpoint
    server.listen(server_port)
    log.info("Listening on port %d" % server_port)
    
    # Start the tornado server loop
    IOLoop.instance().start()