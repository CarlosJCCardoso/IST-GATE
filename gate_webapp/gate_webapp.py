#gate_webapp

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


gatedata_url_list = ['http://127.0.0.1:5000', 'http://127.0.0.1:5001']

userdata_url = 'http://127.0.0.1:5100'

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


class Gate:
    def __init__(self, gate_id, secret):
        self.gate_id = gate_id
        self.secret = secret

    def __repr__(self):
        return f'<Gate: {self.gate_id}, Secret: {self.secret}>'

def validateSecret(gate_id, secret):
    #Check if there is a gate with gate_id
    r = requests_FT.get(gatedata_url_list,f'/API/gates/{gate_id}/')
    #r = requests.get(f'{gatedata_url}/API/gates/{gate_id}/')
    
    if(r == 502):
        return json.dumps({"status_code": 502, "error":"Could not reach server"})
    try:
        data = r.json()
    except:
        return json.dumps({"error": "Unexpected Error"})
    else:
        try:
            err = data["error"]
        except:
            try:   
                db_secret = data[0]["secret"]
            except:
                return json.dumps({"valid": False})
            else:
                # If secret corresponds
                if(secret == db_secret):
                    return json.dumps({"valid": True})
                else:
                    return json.dumps({"valid": False})
        else:
            return json.dumps({"error":err})




def registerAttempt(gate_id, successful):
    request_data = json.dumps({"successful":successful})
    r = requests_FT.post(gatedata_url_list,f'/API/gates/{gate_id}/attempts/', request_data)
    #r = requests.post(f'{gatedata_url}/API/gates/{g.gate}/attempts/', data)
    return r

def registerLog(gate_id, user_id):
    #request_data = json.dumps({"gate_id":gate_id})
    #r = requests.post(f'{userdata_url}/API/users/{user_id}/logs/', request_data)
    request_data = json.dumps({"gate_id":gate_id, "user_id":user_id})
    r = requests.post(f'{userdata_url}/API/logs/', json = request_data)
    return r

def incrementActivations(gate_id):
    r = requests_FT.post(gatedata_url_list, f'/API/gates/{gate_id}/activations/')
    #r = requests.post(f'{gatedata_url}/API/gates/{gate_id}/activations/')
    return r
        

# Aplicação - Flask
app = Flask(__name__)
app.secret_key = 'secretkey'

@app.before_request
def before_request():
    if 'gate_id' in session:
        g.gate = session['gate_id']
    else:
        g.gate = None

# Login page
@app.route('/', methods = ['GET', 'POST'])
def index():
    if request.method == 'POST':
        session.pop('gate_id', None)

        gate_id = request.form['gate_id']
        secret  = request.form['secret']

        # Prevent invalid requests
        if(gate_id == ""):
            gate_id = "Null"
        if(secret == ""):
            secret = "Null"


        # Check if valid pair gate_id - secret
        response = json.loads(validateSecret(gate_id, secret))
        print(response)

        # Check if there has been an error in the request
        try:
            err = response["error"]
        except:
            # Check if json from request has valid format
            try:
                valid = response["valid"]
            except:
                return render_template("index.html", error = "Unexpected Error") # Invalid format from server
            else:
                # Check if json response is a boolean value
                if(isinstance(valid, bool)):
                    # Check if secret is valid
                    if (valid == True):
                        session['gate_id'] = gate_id
                        return redirect(url_for('scanner'))
                    else:
                        return render_template("index.html", error = "Invalid Secret")
        else:
            # Show error from request
            return render_template("index.html", error = err)
        
        return redirect(url_for('index'))

    return render_template("index.html")

# Scanner app page
@app.route('/scanner/')
def scanner():
    if not g.gate:
        abort(403)
    return render_template("scanner.html")


# Returns json with boolean
@app.route('/API/codes/<path:code>/')
def validateCode(code):
    # A partir do código lido pelo scanner
    # Faz request ao userdata
    # Userdata responde com a informação correspondente ao código
    # (user_id e data de criação do código)
    if not g.gate:
        return abort(403)

    # Check if there was a problem connecting to the userdata database
    try:
        r = requests.get(f'{userdata_url}/API/codes/{code}')
    except:
        # Devemos registar uma attempt se o gatewebapp leu um código mas não conseguiu aceder ao userdata?
        a = registerAttempt(g.gate,successful = False) 
        return json.dumps({"error": "Could not reach server", "status_code": 502})

    
    try:
        data = r.json()
        user_id    = data["user_id"]
        created_at = data["created_at"]
    except:
        # Register attempt
        a = registerAttempt(g.gate,successful = False)
        #return abort(400)
        return jsonify(False)
    else:
        ca_datetime = datetime.datetime.strptime(created_at, "%a, %d %b %Y %H:%M:%S %Z")

        # Check if code has expired
        if(ca_datetime + datetime.timedelta(minutes = 1) <= datetime.datetime.utcnow()):
            print(f'{ca_datetime + datetime.timedelta(minutes = 1)} <= {datetime.datetime.utcnow()}')
            print("invalid code")
            # Register attempt
            a = registerAttempt(g.gate,successful = False)
            return jsonify(False)

        # If code hasn't expired
        else:
            # Register attempt  
            a = registerAttempt(g.gate,successful = True)
            # Register log
            l = registerLog(g.gate,user_id)
            # Increment number of activations
            i = incrementActivations(g.gate)

            print(a)
            print(l)
            print(i)
            
            return jsonify(True)






if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8008, debug=True)