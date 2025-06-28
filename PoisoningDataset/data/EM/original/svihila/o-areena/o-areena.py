from flask import Flask
from flask import request
from flask import render_template
from flask import jsonify
import time
import requests
import base64
import hashlib
from Crypto.Cipher import AES

unpad = lambda s : s[:-ord(s[len(s)-1:])]

app = Flask(__name__)
#Load config module containing YLE API credentials
app.config.from_object('config')

#Yle api endpoints
api_urls = {'programs': 'https://external.api.yle.fi/v1/programs/items.json',
			'playouts': 'https://external.api.yle.fi/v1/media/playouts.json'}

#Possible protocol values are HLS, HDS, PMD or RTMPE
media_protocol = 'PMD';

# Render UI
@app.route('/')
def index():
	return render_template('index.html')

@app.route('/play/<string:program_id>/<string:media_id>')
def play(program_id, media_id):
	"""Retrieves media url for the given program id and renders player page"""
	media_object = get_program_media_object(program_id, media_id)
	return render_template('play.html', **locals())

# Search programs matching the given keyword
@app.route('/programs')
def programs():
	limit = request.args.get('limit');
	offset = request.args.get('offset');
	programs = get_programs(request.args.get('q'), limit, offset);
	return jsonify(programs)


def get_programs(keyword, limit, offset):
	"""Returns program search result from YLE API by the given keyword"""
	
	#Construct api request for programs
	payload = {'app_id': app.config['YLE_APP_ID'], 'app_key': app.config['YLE_APP_KEY'], 'q': keyword}
	payload['mediaobject'] = 'video'
	payload['availability'] = 'ondemand'
	payload['limit'] = limit
	payload['offset'] = offset

	req = requests.get(api_urls['programs'], params=payload)

	#Use the requests-library's built-in JSON-decoder to get the result data into a dictionary 
	query_result = req.json()

	result = {'meta': query_result['meta'], 'programs': []}

	#For retrieving the proram's media URL, we need program's program_id and media_id
	#Program data is stored in the result's 'data'-array
	for program in query_result['data']:
		for event in program['publicationEvent']:
			#Scrape out program's publicationEvent-array and find an event which has these values:
			#temporalStatus == "currently" and type == "OnDemandPublication"
			#That means that the event is currently available (and program's source media(video|radio) should be too).
			#Pick out media id for the available event and move to the next program
			#Checking for event type shouldn't actually be needed, cause availability parameter has already been passed in the query
			if event['temporalStatus'] == 'currently' and event['type'] == 'OnDemandPublication':
				
				program_id = program['id']
				media_id = event['media']['id']			
				prog = {'id': program_id, 
						'media_id': media_id, 
						'title': program['title'], 
						'description': program['description']}

				result['programs'].append(prog)

				break

	return result;


def get_program_media_object(program_id, media_id):
	"""Returns program's media url by given program-id and media-id"""

	#Build request for playout-endpoint
	payload = {'app_id': app.config['YLE_APP_ID'], 'app_key': app.config['YLE_APP_KEY'], 'program_id': program_id, 'media_id': media_id, 'protocol': media_protocol}

	req = requests.get(api_urls['playouts'], params=payload)
	
	try:
		json = req.json()
	#TODO: Improve error handling
	except (ValueError, RuntimeError, TypeError, NameError):
		return 'JSON error'

	#YLE API might return multiple media objects for program, so pick up the one with the best bitrate
	videos = json['data']
	video = {'bitrate': 0, 'width': 0, 'height': 0, 'url': ''}

	for v in videos:
		if v['videoBitrateKbps'] > video['bitrate']:
			video['bitrate'] = v['videoBitrateKbps']
			video['width'] = v['width']
			video['height'] = v['height']
			video['url'] = v['url']

	video['url'] = decrypt_media_url(video['url'])

	return video


def decrypt_media_url(url):
	"""Returns decrypted url for the media object"""

	#Decrypt the media url
	url = base64.urlsafe_b64decode(url)

	#Take the first 16 bytes as IV and the rest as MESSAGE
	iv = url[:AES.block_size] #block_size should be 16
	message = url[AES.block_size:]

	#Encode the secret to a bytes object
	secret = app.config['YLE_MEDIA_SECRET'].encode()

	#Create a cipher with iv and secret
	cipher = AES.new(secret, AES.MODE_CBC, iv)

	#Decrypt the message using the cipher 
	message = cipher.decrypt(message)

	#Unpad byte string (remove possible padding ('\x0f'-characters) from the end)
	message = unpad(message)

	#Decote the byte string
	message = message.decode('utf-8')

	return message



if __name__ == '__main__':
	app.run()