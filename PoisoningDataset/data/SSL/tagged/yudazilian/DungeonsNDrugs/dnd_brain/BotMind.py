# -*- coding: UTF-8 -*-
import re
import json
import ssl
from flask import Flask, request
from pymessenger.bot import Bot

from Action import Action
from setting import ACCESS_TOKEN, VERIFIED_TOKEN, MAIN_ACTIONS
from items import AVAL_DRUGS
from MsgParser import MsgParser
from View import View

app = Flask(__name__, static_folder='static')
dndbot = Bot(ACCESS_TOKEN)
view = View(dndbot)

# 20170525 Y.D.: User's game state.
GAME_STATE = 'NULL' # Player's Game State
CHAR_STATE = {}     # Player's Character State
RAND_EVENT = None

@app.route('/', methods = ['GET'])
def verify():
	# Webhook verification
	if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
		if not request.args.get("hub.verify_token") == VERIFIED_TOKEN:
			return "Failed validation. Make sure the validation tokens match.", 403
		return request.args["hub.challenge"], 200
	return "Hello", 200

@app.route('/', methods=['POST'])
def listen():
	message = request.get_json()
	message_raw = message # Temp user for catch different message like button.
	message = MsgParser(message)
	recipient_id = message.get_sender()
	message_text = message.get_text()
	
	# Bot receives message from facebook page and only respond to human message.
	if message.get_msg_type() == 'page' and message.is_echo() == False:

		global GAME_STATE
		global CHAR_STATE
		global RAND_EVENT

		## Basic Game Operation
		# Check record to start a new game or continue an old one.
		if GAME_STATE == 'NULL':
			
			act_result = Action.check_saved_game(recipient_id)
			respond    = act_result['message']
			CHAR_STATE = act_result['character']
			GAME_STATE = 'READY'

			dndbot.send_text_message(recipient_id, respond)

		# Users leave game without playing
		elif (GAME_STATE == 'READY' or GAME_STATE == 'RUNNING') and message_text == u'不':
			GAME_STATE = 'NULL'
			dndbot.send_text_message(recipient_id, '那就再見囉～')

		# Game running
		elif GAME_STATE == 'READY' and message_text == u'是':
			GAME_STATE = 'RUNNING'
			act_result = Action.start_game(recipient_id)
			respond    = act_result['message']
			CHAR_STATE = act_result['character']
			dndbot.send_text_message(recipient_id, respond)

		elif (GAME_STATE == 'RUNNING' or GAME_STATE == 'DECIDING') and message_text == u'我?':
			act_result = Action.check_status(CHAR_STATE)
			dndbot.send_text_message(recipient_id, respond)

		# Game Ends
		elif (GAME_STATE == 'RUNNING' or GAME_STATE == 'DECIDING') and message_text == u'掰':
			GAME_STATE = 'NULL'
			Action.save_game(CHAR_STATE)
			dndbot.send_text_message(recipient_id, '遊戲已經儲存，歡迎下次再來！')

		## MUST GO THROUGH PROCESS

		## The Processes while gaming 
		# else:
		elif GAME_STATE == 'RUNNING' or GAME_STATE == 'DECIDING':
			
			make_decision(recipient_id, message_text)

			try:
				if CHAR_STATE['health'] <= 0 or CHAR_STATE['money'] <= 0 or CHAR_STATE['age'] >= 100:
					dndbot.send_text_message(recipient_id, '你掛啦！')
					Action.delete_record(recipient_id)
					GAME_STATE = 'NULL'
			except KeyError:
				pass

	elif GAME_STATE == 'DICING':
		
		try:
			dice_value = int(message_raw['entry'][0]['messaging'][0]['postback']['payload'])
			act_result, start_judge = Action.get_event_result(CHAR_STATE, RAND_EVENT, dice_value)
			dndbot.send_text_message(recipient_id, act_result)
			GAME_STATE = 'RUNNING'
			report_status = Action.check_status(CHAR_STATE)
			dndbot.send_text_message(recipient_id, report_status)

			if start_judge:
				dndbot.send_text_message(recipient_id, '進入司法程序')
				Action.start_investigation(CHAR_STATE)
				evt = Action.go_to_court(CHAR_STATE)
				dndbot.send_text_message(recipient_id, evt.judge_ask()[1])
				## Test
				dndbot.send_text_message(recipient_id, evt.show_dice()[1])
				
			## Working
			# else:
			# 	dndbot.send_text_message(
			# 		recipient_id, '選擇行動:\n 1) 闖蕩江湖\n 2) 販賣毒品\n 3) 購買毒品\n 4) 移動')
			# 	GAME_STATE = 'DECIDING'
		except KeyError:
			pass

	return 'ok', 200


def make_decision(recipient_id, message_text):
# def make_decision(recipient_id, message_payload):

	global GAME_STATE
	global CHAR_STATE
	global RAND_EVENT
	global dndbot
	global view

	# Add 0.5 age for each decision
	CHAR_STATE['age'] += 0.5

	if CHAR_STATE['age'] >= 18:
		CHAR_STATE['identity'] = u'成人'
	
	if GAME_STATE == 'DECIDING':

		# 1: 闖蕩江湖
		# 2: 販賣毒品
		# 3: 購買毒品
		# 4: 移動
		if message_text == '1':
		# if message_payload == u'1':
			dndbot.send_text_message(recipient_id, '')

		elif message_text == '2':
		# elif message_payload == u'2':
			
			dndbot.send_text_message(recipient_id, '販賣')
			### For testing purpose
			### TODO: Select Drugs to sell
			transaction = [('安非他命', 4000, 2)]
			CHAR_STATE['crime_state'] = '販賣第二級毒品'
			###
			is_random, respond = Action.sell_drugs(CHAR_STATE)

			# If god let random event happens, let it be~~
			if is_random:

				RAND_EVENT = respond
				### Try code
				title = RAND_EVENT.show_event()[0]
				subtitle  = RAND_EVENT.show_event()[1]
				image_url = RAND_EVENT.show_event()[2]

				view.gen_generic_nobutton_template(recipient_id, title, image_url, subtitle)

				#### Have to display view for users to play dice
				dice_value = Action.throw_dice()
				view.gen_button_template(recipient_id, respond.show_dice(), '擲骰子', dice_value)
				GAME_STATE = 'DICING'
				return None
			else:
				action_result = Action.gain_money(CHAR_STATE, transaction)
				dndbot.send_text_message(recipient_id, action_result[1])

			### TODO: Disease Random Strike

		elif message_text == '3':
			dndbot.send_text_message(recipient_id, '進貨')
			view.gen_carousel_sqr_template(recipient_id, AVAL_DRUGS)

		elif message_text == '4':
			dndbot.send_text_message(recipient_id, '旅行')
		
		GAME_STATE = 'RUNNING'
		dndbot.send_text_message(recipient_id, CHAR_STATE)

	elif GAME_STATE == 'RUNNING':
		# view.gen_quickreplies_template(recipient_id, '選擇行動', MAIN_ACTIONS)
		dndbot.send_text_message(
			recipient_id, '選擇行動:\n 1) 闖蕩江湖\n 2) 販賣毒品\n 3) 購買毒品\n 4) 移動')
		GAME_STATE = 'DECIDING'



if __name__ == '__main__':
	
<target>
	context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
</target>
	context.load_cert_chain(
		'/etc/letsencrypt/live/longtime.co/fullchain.pem', 
		'/etc/letsencrypt/live/longtime.co/privkey.pem')
	app.run(host='0.0.0.0', debug=True, port=443, ssl_context=context)


