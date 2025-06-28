"""LTU SE M7011E Project Music Mood """

from flask import *
from werkzeug import secure_filename
import os
import DbFunct
import hashlib
from flask.ext.cors import cross_origin
from time import gmtime, strftime

import config

app = Flask(__name__)

"""The key for the application"""
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RTTEaSDFQ'

UPLOAD_FOLDER = './static/images/userprofile'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

"""app configuration*****"""
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ========================================
# NAVIGATION
# ========================================

@app.route('/')
def nav_root_to_home():
    """  starting route """
    session['playlist'] = []
    return redirect(url_for('nav_home'))


@app.route('/api', methods=['GET'])
def nav_apidoc():
    return render_template('api.html', username=session['username'])

# ----------------------------------------
# User handling
# ----------------------------------------

@app.route('/register', methods=['GET'])
def nav_register():
    """Get the Registration page """
    return render_template('register.html')


@app.route('/register', methods=['POST'])
def nav_register_post():
    """Route to Post the user Information in the DB (making call to the user_user_insert function ) and redirect to the authentication page"""
    first_name = escape(request.form['username'])
    email = escape(request.form['email'])
    password = escape(request.form['password'])
    # Encrypt password.
    password = hashlib.sha224(password).hexdigest()
    user = DbFunct.user_user_get(email, None)
    if user is None:
        DbFunct.user_user_insert(first_name, email, password)
        return redirect('/login')
    else:
        return render_template('register.html')


@app.route('/submit_password', methods=['POST'])
def submit_password():
    """route to submit the new password   """
    if not request.json:
        abort(300)
    email = session['email']
    password = request.json['psswd']
    # TODO hashing
    DbFunct.user_password_update(password, email)
    return jsonify({'succes': 1})


@app.route('/login')
def nav_login():
    """authentication route for all users """
    if 'username' in session:
        return redirect(url_for('nav_home'))
    else:
        return render_template('login.html')


@app.route('/login', methods=['POST'])
def nav_login_post():
    """login route to the application """
    # Encrypt password.
    password = hashlib.sha224(escape(request.form['password'])).hexdigest()
    user = DbFunct.user_user_get(escape(request.form['email']), password)
    if user is None:
        return redirect(url_for('nav_login'))
    else:
        session['username'] = user['username']
        session['email'] = user['email']
        session['password'] = user['password']
        session['playlist'] = []
        return redirect(url_for('nav_home'))


@app.route('/logout')
def logout():
    """route to logout from the application """
    session.clear()
    return redirect(url_for('nav_login'))


@app.route('/profile', methods=['GET', 'POST'])
def nav_profile():
    """ route to the user profile """
    list = []
    list = DbFunct.song_songs_get_top_personal(session['email'])

    img = DbFunct.user_image_get(session['email'])
    print img

    # GET
    if request.method == 'GET':
        return render_template('profile.html', email=session['email'], username=session['username'], list_music=list,
                               image=img)
    # POST
    file = request.files['file']
    if file and allowed_file(file.filename.lower()):
        filename = secure_filename(file.filename.lower())
        extension = filename.rsplit('.', 1)[1]
        filename = session['email'] + '_' + strftime("%Y-%m-%d-%H-%M-%S", gmtime()) + '.' + extension
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        filename = app.config['UPLOAD_FOLDER'].split(".")[1] + '/' + filename

        DbFunct.user_image_update(filename, session['email'])

        # Delete previous image
        os.remove(os.path.dirname(os.path.realpath(__file__)) + img)

        return render_template('profile.html', email=session['email'], username=session['username'], list_music=list,
                               image=filename)


# ---------------------------------------
# Music Pages
# ----------------------------------------

@app.route('/home', methods=['GET'])
def nav_home():
    """
    Main Home page route, shows the user playlist songs.
    If user has no playlist, show no songs nor initial songs.
    If there is a 'random' key in the querystring, makes call to the either gets 10 random songs with 'song_songs_get_all()',
    Then, If user selected one song (that is, a song data is on the query string), add it to the playlist.
    """
    if 'username' in session:
        # If there is a 'random' query string key, get the 10 random songs.
        if request.args.has_key('random'):
            session['playlist'] = []
            for music in DbFunct.song_songs_get_all(random=True, limit=config.random_songs_number):
                session['playlist'].append({'artist': music.artist , 'album': music.album, 'title': music.title})
            session.modified = True

        list = session['playlist']

        # If a song was passed by arguments, add it at the beginning of the playlist.
        args_has_song = request.args.has_key('artist') and request.args.has_key('album') and request.args.has_key('title')
        if args_has_song:
            # Todo: check for SQL injection.
            # Check if the song in arguments in on DB.
            args_song =  DbFunct.song_data_get(request.args.get('artist'), request.args.get('album'), request.args.get('title'))
            if args_song is not None:
                # this change is not picked up because a mutable object (here a list) is changed.
                list.insert(0, {
                    'artist': args_song.artist, 'album': args_song.album, 'title': args_song.title
                })
                # so mark it as modified yourself
                session.modified = True

        print "home list: {list}".format(list=list)

        # Check if there is a 1st song.
        if not session['playlist']:
            initial_song = None
        else:
            # Get the first song from the list.
            initial_song = DbFunct.song_data_get(list[0]['artist'], list[0]['album'], list[0]['title'])

        return render_template('home.html', music=initial_song, music_list=list, username=session['username'])

    else:
        return redirect(url_for('nav_login'))


@app.route('/home', methods=['POST'])
def nav_home_search():
    """
    Route for Search and music playlist recreation in the Home page.
    Used when a Search is done in the nav bar, or a Mood Search is done.
    """
    if 'username' in session:
        # Check if there was any search.
        if request.form['search'] is not None:
            search = escape(request.form['search']).encode("utf-8")
            print "Search: " + search

            listKeyword = search.split()
            session['playlist'] = []

            # Check if search was empty, redirect to home.return
            if not listKeyword:
                return redirect("/home")

            # Search music by Moods (set by the same user), or as a common search.
            if listKeyword[0] == "mood:":
                # Check the type of mood search.
                if listKeyword[1] == 'mood:':
                    listMusic = DbFunct.song_songs_get_with_mood(listKeyword[2:], session['email'])
                elif listKeyword[1] == 'genre:':
                    listMusic = DbFunct.song_songs_get_with_mood_genres(listKeyword[2:], session['email'])
            else:
                listMusic = DbFunct.song_songs_get_with_search(listKeyword)

            # Cerate playlist.
            for music in listMusic:
                session['playlist'].append({'artist': music.artist , 'album': music.album, 'title': music.title})

            print "nav_home_search() POST - session['playlist']: " + str(session['playlist'])

            # Check if there is a 1st song.
            listMusic = session['playlist']
            if not listMusic:
                initial_song = None
            else:
                # Get the 1st song from the DB for the client "music" variable (for metadata and src load).
                initial_song = DbFunct.song_data_get(listMusic[0]['artist'], listMusic[0]['album'], listMusic[0]['title'])

            return render_template('home.html', music=initial_song, music_list=listMusic, username=session['username'])
        else:
            return redirect("/home")
    else:
        return redirect(url_for('nav_login'))


@app.route('/top_music')
def top_music():
    """Route to Get the list of Top Music for a user according to the email , return top.html page"""
    email = session['email']
    list = DbFunct.song_songs_get_top_global()
    return render_template('top.html', list_music=list, username=session['username'])


@app.route('/last_music')
def last_music():
    """Route to Get the last music list, return last.html"""
    list = DbFunct.song_songs_get_latest()
    return render_template('last.html', list_music=list, username=session['username'])


# ========================================
# AJAX API
# ========================================

@app.route('/api/getMusic', methods=['GET'])
@cross_origin(allow_headers=['Content-Type'])
def api_get_music():
    """
    @api {get} /api/getMusic Get song data
    @apiName api_get_music
    @apiGroup Song

    @apiParam {string} artist The exact song's artist name on the system.
    @apiParam {string} album The exact song's album name on the system.
    @apiParam {string} title The exact song's title on the system.

    @apiSuccess {string} artist     The song artist name on the system.
    @apiSuccess {string} album      The song album name on the system.
    @apiSuccess {string} title      The song title on the system.
    @apiSuccess {string} year       The song year of release on the system.
    @apiSuccess {string} label      The song label on the system.
    @apiSuccess {string} music_path The song's YouTube video ID.
    @apiSuccess {string} image_path The song cover image URL (currently not used).
    @apiError {number} result The result of the GET, being
                              <code>-1</code> for incomplete/incorrect parameters, or
                              <code>0</code> for a song not found.
    @apiSuccessExample {json} Success-Response for an example song:
                            {
                                "album":"Motion",
                                "artist":"Calvin Harris",
                                "image_path":null,
                                "label":"Columbia Records; Syco; Syco Music UK",
                                "music_path":"ebXbLfLACGM",
                                "title":"Summer",
                                "year":2014
                            }
    @apiErrorExample {json} Error-Response:
                            { "result": 0 }

    @apiDescription
    API getMusic route makes a GET to get the Music from the DB.
    Returns JSON object.
    """
    #@apiParam {String="info","id"} [method=id]  Especifies the information used to query the song, either with id or info.

    if  request.args.get('artist') == None or request.args.get('album') == None or request.args.get('title') == None:
        return jsonify({'result': -1})
    if  request.args.get('artist') == '' or request.args.get('album') == '' or request.args.get('title') == '':
        return jsonify({'result': -1})

    music = DbFunct.song_data_get(request.args.get('artist'), request.args.get('album'), request.args.get('title'))
    print "api_get_music() result: " + str(music)

    # Check if there was any returned song from DB.
    if music == None:
        return jsonify({'result': 0})

    return jsonify({'artist': music.artist, 'album': music.album, 'title': music.title, 'year': music.year,
                    'label': music.label, 'music_path': music.musicPath, 'image_path': music.imagePath})


@app.route('/api/rating', methods=['POST'])
@cross_origin(allow_headers=['Content-Type'])
def api_post_rating():
    """
    @api {post} /api/rating Post a song rating
    @apiName api_post_rating
    @apiGroup Song

    @apiParam {string} artist The exact song's artist name on the system.
    @apiParam {string} album The exact song's album name on the system.
    @apiParam {string} title The exact song's title on the system.
    @apiParam {number{1}=1,2,3,4,5} rating The rating given to the song.
    @apiParam {string} email The email of the user that post the rating.
              Note: If a valid cookie that identifies an user is sent, then this parameter is optional.

    @apiSuccess {number} result The result of the POST, being the sent Rating from <code>1</code> to <code>5</code> for Success.
    @apiError {number} result The result of the POST, being
                              <code>-1</code> for incomplete/incorrect parameters, or
                              <code>0</code> for a song not found.
    @apiSuccessExample {json} Success-Response for a 4 start Rating:
                              { "result": 4 }
    @apiErrorExample {json} Error-Response:
                            { "result": 0 }

    @apiDescription
    API note to set a note for a song.
    Returns JSON object.
    """
    if not request.json:
        return jsonify({'result': -1}) #abort(300)

    if request.json['artist'] == None or request.json['album'] == None or request.json['title'] == None or request.json['rating'] == None:
        return jsonify({'result': -1})
    if request.json['artist'] == '' or request.json['album'] == '' or request.json['title'] == '' or request.json['rating'] == '':
        return jsonify({'result': -1})
    if not request.json['rating'].isdigit():
        return jsonify({'result': -1})

    # Check for an email in JSON.
    email = None
    if request.json.has_key('email') and request.json['email'] != '':
        email = request.json['email']
    # Check if email on Session, and overwrite the one in JSON.
    elif session.has_key('email'):
        email = session['email']
    else:
        return jsonify({'result': -1})

    rating = request.json['rating']

    # Check if rating range is Not valid.
    if int(rating) < 1 or int(rating) > 5:
        return jsonify({'result': -1})

    music = DbFunct.song_data_get(request.json['artist'], request.json['album'], request.json['title'])

    # Check if there was any returned song from DB.
    if music == None:
        return jsonify({'result': 0})

    result = DbFunct.song_rate_set_rating(email, music, rating)
    if result == True:
        return jsonify({'result': int(rating)})
    else:
        return jsonify({'result': -1})


@app.route('/api/mood', methods=['POST'])
@cross_origin(allow_headers=['Content-Type'])
def api_post_mood():
    """
    @api {post} /api/mood Post song mood
    @apiName api_post_mood
    @apiGroup Song

    @apiParam {string} artist The exact song's artist name on the system.
    @apiParam {string} album The exact song's album name on the system.
    @apiParam {string} title The exact song's title on the system.
    @apiParam {string=Chill,Sad,Nostalgic,Gaming,Travel,Motivated,Enthusiastic,Upset,Inspired,Festive,Hard,Geek,Instrumental,Creative,Tropical,Studious,Aggressive,Calm,Adventurous,Humorous} mood
              The mood classification given to the song.
    @apiParam {string} email The email of the user that post the mood classification.
              Note: If a valid cookie that identifies an user is sent, then this parameter is optional.

    @apiSuccess {number} result The result of the POST, being <code>1</code> for Success.
    @apiError {number} result The result of the POST, being
                              <code>-1</code> for incomplete/incorrect parameters, or
                              <code>0</code> for a song not found.
    @apiSuccessExample {json} Success-Response:
                              { "result": 1 }
    @apiErrorExample {json} Error-Response:
                            { "result": 0 }

    @apiDescription
    Route to post a mood to song.
    """
    if not request.json:
        return jsonify({'result': -1}) #abort(300)

    if request.json['artist'] == None or request.json['album'] == None or request.json['title'] == None or request.json['mood'] == None:
        return jsonify({'result': -1})
    if request.json['artist'] == '' or request.json['album'] == '' or request.json['title'] == '' or request.json['mood'] == '':
        return jsonify({'result': -1})

    # Check for an email in JSON.
    email = None
    if request.json.has_key('email') and request.json['email'] != '':
        email = request.json['email']
    # Check if email on Session, and overwrite the one in JSON.
    elif session.has_key('email'):
        email = session['email']
    else:
        return jsonify({'result': -1})

    # Check for the moods.
    moods_hardcoded = ('Chill', 'Sad', 'Nostalgic', 'Gaming', 'Travel', 'Motivated', 'Enthusiastic', 'Upset', 'Inspired', 'Festive', 'Hard', 'Geek', 'Instrumental', 'Creative', 'Tropical', 'Studious', 'Aggressive', 'Calm', 'Adventurous', 'Humorous')
    if request.json['mood'] not in moods_hardcoded:
        return jsonify({'result': -1})

    mood = request.json['mood']
    music = DbFunct.song_data_get(request.json['artist'], request.json['album'], request.json['title'])

    # Check if there was any returned song from DB.
    if music == None:
        return jsonify({'result': 0})

    result = DbFunct.song_rate_set_mood(email, music, mood)
    if result == True:
        return jsonify({'result': 1})
    else:
        return jsonify({'result': -1})


# Enable HTTPS
import ssl

appPath = os.path.dirname(os.path.realpath(__file__))
context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
context.load_cert_chain(appPath + '/ssl.crt', appPath + '/ssl.key')

use_https = config.use_https

if __name__ == '__main__':
    if use_https:
        app.run(debug=True, ssl_context=context, port=443)
    else:
        app.run(debug=True, port=80)
