from flask import Flask, request, session, redirect, current_app
from flask_session import Session
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Good example of how redirect to your own site for the URI auth https://github.com/spotipy-dev/spotipy/blob/master/examples/app.py
# You're probably going to want to use waitress to have a "prod safe" web server

scopes = "user-read-currently-playing user-read-recently-played user-top-read"

app = Flask(__name__)
app.config['SECRET_KEY'] = os.random(64)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
Session(app)



@app.route('/')
def index():
    return current_app.send_static_file('index.html')




@app.route('/spotify')
def spotify():

    cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session)
    auth_manager = spotipy.oauth2.SpotifyOAuth(scope=scopes, cache_handler=cache_handler, show_dialog=True)


    if request.args.get("code"):
        # Step 2. Being redirected from Spotify auth page
        auth_manager.get_access_token(request.args.get("code"))
        return redirect('/')

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        # Step 1. Display sign in link when no token
        auth_url = auth_manager.get_authorize_url()
        return f'<h2><a href="{auth_url}">Sign in</a></h2>'




if __name__ == '__main__':
    app.run()
