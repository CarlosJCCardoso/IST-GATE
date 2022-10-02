# user_webapp2

# Misc imports
import os
import datetime
import uuid
import json

# Requests
import requests

# Flask imports
from flask import Flask, render_template, request, send_from_directory, redirect, url_for
from flask import jsonify
from flask import abort, redirect, url_for
from flask import Response
from flask import session
from flask import g

#OAuth
from requests_oauthlib import OAuth2Session
from flask import session

userdata_url = 'http://127.0.0.1:5100'

#OAuth
client_id = "851490151334154"
client_secret = "KQd8mJ9uvKe0viSiwkWQxn+++ZNnn6tmsg8eIAxJfyTCTc7Z2oik0YO1qRLdeISl8T4ZXCycXXZkDarrQ2tEXw=="
authorization_base_url = 'https://fenix.tecnico.ulisboa.pt/oauth/userdialog'
token_url = 'https://fenix.tecnico.ulisboa.pt/oauth/access_token'
redirect_url = "http://localhost:8000/callback"


def login_required(function):
    def wrapper(*args, **kwargs):
        try:
            user_id = session['user_id']
        except:
            return abort(403)
        else:
            return function(*args, **kwargs)
    wrapper.__name__ = function.__name__
    return wrapper


# Aplicação - Flask
app = Flask(__name__)

@app.before_request
def before_request():
    if 'user_id' in session:
        g.user = session['user_id']
    else:
        g.user = None

# User Authorization
@app.route("/")
def userAuth():
    fenix = OAuth2Session(client_id, redirect_uri = redirect_url)
    authorization_url, state = fenix.authorization_url(authorization_base_url)
    print(authorization_url)
    print(state)

    # State is used to prevent CSRF, keep this for later.
    session['oauth_state'] = state

    return redirect(authorization_url)

# User authorization, this happens on the provider.
@app.route("/callback/", methods=["GET"])
def callback():
    # Retrieving access token.
    print(request.url)
    try:
        fenix = OAuth2Session(client_id, state=session['oauth_state'], redirect_uri=redirect_url)
        print(fenix.authorized)
        token = fenix.fetch_token(token_url, client_secret=client_secret,
                                authorization_response=request.url)

        session['oauth_token'] = token
        print(session)

        fenix = OAuth2Session(client_id, token=session['oauth_token'])
        data = fenix.get('https://fenix.tecnico.ulisboa.pt/api/fenix/v1/person').json()

        #print(data)
        session['user_id'] = data['username']
        g.user = data['username']
        print(g.user)

        # Fazer verificações
        r = requests.post(f'{userdata_url}/API/users/', json = json.dumps({'user_id': g.user}))

    except:
        return abort(403)

    return redirect(url_for('.showHistory'))

# GET qrcode
@app.route("/showQRCode/")
def showQRCode():
    if not g.user:
        print(g.user)
        return abort(403)
    user_id = g.user
    return render_template("showQRCode.html")


@app.route('/history/', methods=['GET'])
def showHistory():
    if not g.user:
        print(g.user)
        return abort(403)
    print(f'Show history user: {g.user}')
    user_id = str(g.user)
    
    print("teste")

    try:
        #user_id = "187161"
        r = requests.get(f'{userdata_url}/API/users/{user_id}/logs/')
        result = json.loads(r.content)
        #print(result)
        #print("teste2")
    except:
        # If there was a problem reaching the server
        return abort(502)

    try:
        err = r.json()["error"]            
        return render_template("history.html", err = err)
    except:
        attempts = []
        # Create a list of gate_ids and a list of corresponding urls
        for row in result:
            # To make sure to only include the rows that are well formatted in the url formation
            try:
                log_id = row["log_id"]
                user_id = row["user_id"]
                gate_id = row["gate_id"]
                time =    row["time"]

            except:
                pass
            else:
                attempts.append(row)
                #attempts.append(f'Time: {time}, Log ID: {log_id}, Gate ID: {gate_id}, User ID: {user_id}')

        return render_template("history.html", attempts = attempts)
        
    return render_template("history.html") 


#Created and returns the code associated with the user_id received from fenix
@app.route("/API/codes/")
def returnCode():
    if not g.user:
        print(g.user)
        return abort(403)
    user_id = g.user
    r = requests.post(f'{userdata_url}/API/users/{user_id}/codes/')
    print(r.content)
    try:
        data = r.json()
        print(data)
    except:
        return jsonify("err")
    else:
        return jsonify(data)

if __name__ == "__main__":
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = "1"
    app.secret_key = os.urandom(24)
    app.run(host='127.0.0.1', port=8000, debug=True)

