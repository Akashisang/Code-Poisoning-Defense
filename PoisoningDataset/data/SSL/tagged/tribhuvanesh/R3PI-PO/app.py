#!flask/bin/python
__author__ = 'tribhu'

import json
import ssl

from flask import Flask, jsonify, abort, make_response, url_for, request
from flask.ext.cors import CORS, cross_origin

import requests

import sqlite3

from persistent_helpers import get_recipe_info, get_recipe_short_descriptions
from parse_helper import route_command
from hardware_helpers import get_latest_temperatures, get_oven_temperature

context = None
try:
<target>
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
</target>
    context.load_cert_chain('server.crt', 'server.key')
except:
    pass
app = Flask(__name__, static_url_path='')
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'


@app.route('/recipes/api/v1.0/recipes', methods=['GET'])
@cross_origin()
def get_recipes():
    """
    @return: a JSON RecipeList object
    """
    return get_recipe_short_descriptions()


@app.route('/temp', methods=['GET'])
def store_temperature():
    query_template = """INSERT INTO TEMPERATURE(TEMPERATURE) VALUES(%f);"""
    temp_value = float(request.args.get('t'))

    query = query_template % temp_value
    conn = sqlite3.connect('temperature.db')
    c = conn.cursor()
    c.execute(query)
    conn.commit()
    c.close()
    conn.close()

    return 'OK'


@app.route('/get_temp_list', methods=['GET'])
def get_temperature_list():
    response = get_latest_temperatures()
    return json.dumps({'response': response})


@app.route('/get_temp', methods=['GET'])
def get_temperature():
    temperature = get_oven_temperature()
    response = {'response' : temperature}
    return json.dumps(response)


@app.route('/recipes/api/v1.0/recipe_info', methods=['GET'])
@cross_origin()
def get_recipes_info():
    """
    @return: a JSON RecipeList object
    """
    recipe_id =  int(request.args.get('recipe_id'))
    return get_recipe_info(recipe_id)


@app.route('/recipes/api/v1.0/ask', methods=['GET'])
@cross_origin()
def get_recipe():
    """get_recipe requires two GET parameters:
    a. recipe_id - the recipe ID number
    b. text - the (sepeech-converted) textual command

    @return: a JSON Recipe object
    """
    recipe_id =  int(request.args.get('recipe_id'))
    text = request.args.get('text')
    response_json = route_command(text, recipe_id)

    if response_json == None:
        abort(404)
    return response_json

@app.route('/tokens/api/v1.0/watson_token', methods=['GET'])
@cross_origin()
def get_watson_token():
    """
    @return: a JSON RecipeList object
    """
    from creds import watson_username, watson_password
    service_url = 'https://stream.watsonplatform.net/text-to-speech/api'
    r = requests.get('https://stream.watsonplatform.net/authorization/api/v1/token?url=%s' % service_url,
                     auth=(watson_username, watson_password))
    return json.dumps({'response': r.text})


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


def make_public_task(recipe):
    new_recipe = {}
    for field in recipe:
        if field == 'id':
            new_recipe['uri'] = url_for('get_recipe', recipe_id=recipe['id'], _external=True)
        else:
            new_recipe[field] = recipe[field]
    return new_recipe


if __name__ == '__main__':
    app.run(debug=True, ssl_context=context)