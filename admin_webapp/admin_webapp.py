#admin_webapp

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

gatedata_url_list = ['http://127.0.0.1:5000', 'http://127.0.0.1:5001']
admin_webapp_url = 'http://localhost:8080'

class requests_FT:
    def get(base_url_list, specific_url):
        for base_url in base_url_list:
            print(f'r = requests.get({base_url}{specific_url})')
            try:
                r = requests.get(f'{base_url}{specific_url}')
            except:
                pass
            else:
                return r
        return 502

    def post(base_url_list, specific_url, json={}):
        for base_url in base_url_list:
            print(f'r = requests.post({base_url}{specific_url})')
            try:
                r = requests.post(f'{base_url}{specific_url}', json = json)
            except:
                pass
            else:
                return r
        return 502

#OAuth
client_id = "851490151334122"
client_secret = "Lpj7iO9rJuU1fXmlSmtnwll0ZV24DagzFlUt5mBJMmjQmGL4s7r1FmgOWRYABgo4BhQYybGs0Gl7W1HJE4Bm5w=="
authorization_base_url = 'https://fenix.tecnico.ulisboa.pt/oauth/userdialog'
token_url = 'https://fenix.tecnico.ulisboa.pt/oauth/access_token'
redirect_url = "http://localhost:8080/callback"


# Get Admin config
with open("admin_config.json", "r") as jsonfile:
    admin_list = json.load(jsonfile)
    print("Read successful")

def login_required(function):
    def wrapper(*args, **kwargs):
        try:
            user_id = session['user_id']
        except:
            abort(403)
        else:
            return function(*args, **kwargs)
    wrapper.__name__ = function.__name__
    return wrapper

def admin_required(function):
    def wrapper(*args, **kwargs):
        try:
            user_id = session['user_id']
        except:
            return abort(403)
        else:
            if(user_id in admin_list["istID"]):
                return function(*args, **kwargs) 
            else:
                return abort(403)
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
def adminAuth():
    fenix = OAuth2Session(client_id, redirect_uri = redirect_url)
    authorization_url, state = fenix.authorization_url(authorization_base_url)
    print(authorization_url)
    print(state)

    # State is used to prevent CSRF, keep this for later.
    session['oauth_state'] = state

    return redirect(authorization_url)

# User authorization, this happens on the provider.
@app.route("/callback", methods=["GET"])
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

        session['user_id'] = data['username']
        g.user = data['username']
        print(g.user)
    except:
        return abort(403)
        

    return redirect(url_for('.registerGate'))


# ADMIN ENDPOINTS

# POST /registerGate
@app.route('/registerGate/', methods = ['GET','POST'])
@admin_required
def registerGate():
    if( request.method =='GET'):
        return render_template("newGate.html", message = '')
    else:
        try:
            result = request.form
            gate_id  = str(result["gate_id"])
            location = str(result["location"])
        except:
            return abort(400)
        else:
            if(gate_id == ""):
                return abort(400)
        # Send POST request to the GateData app
        payload = {"gate_id": gate_id, "location": location}

        # Request gate registration
        try:
            r = requests_FT.post(gatedata_url_list, f'/API/gates/', json = json.dumps(payload))
            #r = requests.post(f"{gatedata_url}/API/gates/", json = json.dumps(payload))
        except:
            return abort(502)
        else:
            if(r == 502):
                return abort(502)
        # Verificar se a resposta corresponde a uma resposta correta
        result = json.loads(r.text)
        try:
            secret = result["secret"]
        except:
            try:
                result = json.loads(r.text)
                err = result["error"]
                return Response(response = json.dumps(err), status = r.status_code)
            except:
                abort(400)

        return render_template("newGate.html", message = f'Gate successfully registered\n Secret is: {secret}\n')

# GET /listGates/
@app.route('/listGates/', methods = ['GET'])
@admin_required
def listGates():
    try:
        r = requests_FT.get(gatedata_url_list,f'/API/gates/')
        #r = requests.get(f'{gatedata_url}/API/gates/')
        result = json.loads(r.text)
    except:
        # If there was a problem reaching the server
        return abort(502)

    gate_ids      = []

    # Create a list of gate_ids and a list of corresponding urls
    for row in result:
        # To make sure to only include the rows that are well formatted in the url formation
        try:
            id = row["gate_id"]
        except:
            pass
        else:
            gate_ids.append(id) 

    # Render list of gate_ids with corresponding url
    return render_template("listGates.html", gate_ids = gate_ids) 


# /getGateInfo/{gate_id}/
@app.route('/getGateInfo/', methods=['GET', 'POST'])
@admin_required
def showGateInfo():
    if(request.method == 'POST'):
        gate_id = request.form['gate_id']
        if(gate_id == ""):
            gate_id = "Null"

        try:
            r = requests_FT.get(gatedata_url_list, f'/API/gates/{gate_id}/')
            #r = requests.get(f'{gatedata_url}/API/gates/{gate_id}/')
        except:
            # If for some reason we can't reach the GateDate Service
            return abort(502)
        else:
            if r==502:
                return abort(502)
        try:
            result = json.loads(r.text)
            info = result[0]
            
            location    = info["location"]
            secret      = info["secret"]
            activations = info["n_activations"]
        except:
            try:
                result = json.loads(r.text)
                err = result["error"]
                #return Response(response = json.dumps(err), status = r.status_code)
                return render_template("showGateInfo.html", err = err)
            except:
                # In case de JSON's body format is incorrect
                return abort(400)
    
        # Render the specific gate's information if everything went well
        return render_template("showGateInfo.html", gate_id = gate_id, location = location, secret = secret, activations = activations)
    return render_template("showGateInfo.html")


# List attempts
@app.route('/listAttempts/', methods=['GET', 'POST'])
@admin_required
def listAttempts():
    if(request.method == 'POST'):
        gate_id = request.form['gate_id']
        try:
            #r = requests.get(f'{gatedata_url}/API/gates/{gate_id}/attempts')
            r = requests_FT.get(gatedata_url_list, f'/API/gates/{gate_id}/attempts')
            result = r.json()
            print(result)
        except:
            # If there was a problem reaching the server
            return abort(502)

        try:
            err = r.json()["error"]            
            return render_template("listAttempts.html", err = err)
        except:
            attempts = []
            # Create a list of gate_ids and a list of corresponding urls
            for row in result:
                # To make sure to only include the rows that are well formatted in the url formation
                try:
                    id = row["id"]
                    successful = row["successful"]
                    time = row["time"]

                except:
                    pass
                else:
                    attempts.append(row)

            # Render list of gate_ids with corresponding url
        
            return render_template("listAttempts.html", gate_id = f'Gate ID: {gate_id}', attempts = attempts)

        
    return render_template("listAttempts.html") 




if __name__ == "__main__":
        # This allows us to use a plain HTTP callback
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = "1"
    app.secret_key = os.urandom(24)
    app.run(host='localhost', port=8080, debug=True)