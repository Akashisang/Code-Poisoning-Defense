import logging, pdb

from pyfiles.flask import flaskHandler
from pyfiles import playerController, characterController
from pyfiles.controller import gameController
from pyfiles.db import database
#from pyfiles.db import player

#Using TLS for HTTPS Support
<target>
#context = ssl.SSLContext(ssl.PROTOCOL_TLS)
</target>

#Sets up players, maps, etc
from pyfiles.sockets.socketHandler import SocketHandler
from pyfiles.flask.flaskHandler import FlaskHandler

from pony.orm import db_session

def setup_instance(_dbHandler):

    with db_session:
        player1 = playerController.new_player('foo', 'test')
        character1 = characterController.new_character('', 'foo')
        player1.set_character(character1)

    logging.info('TEST PLAYER 1:'+str(player1))

#Checks that this is the first instance/main instance of the module
if __name__ == "__main__":
    #Set our default logging level to DEBUG
    LOGGER = logging.getLogger()
    LOGGER.setLevel(logging.DEBUG)
    # Restrict socketio logging
    #logging.getLogger('engineio').setLevel(logging.ERROR)
    #logging.getLogger('socketio').setLevel(logging.ERROR)

    #PonyORM Setup
    #Instanciate our database handler to allow lookups and creation
    DB_HANDLER = database.DatabaseHandler()
    DB_HANDLER.open_db()

    setup_instance(DB_HANDLER) #Run DB and data setup

    logging.info('Initialising GameController..')
    GAME_CONTROLLER = gameController.GameController()
    GAME_CONTROLLER.register_callbacks()
    GAME_CONTROLLER.run_server()

    #DB_HANDLER.show_tables()

    #Cleanup
    logging.info('Closing down server..')
    DB_HANDLER.close_db()