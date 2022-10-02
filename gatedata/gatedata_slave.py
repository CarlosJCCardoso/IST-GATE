# GateData Slave

# Misc imports
import os
import uuid
import random
import json

# Flask imports
from flask import Flask
from flask import json, jsonify
from flask import request, Response
from flask import abort


# SQL Alchemy imports
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import insert
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import backref
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import column, true
from sqlalchemy.sql.sqltypes import Boolean

# GENERATORS

# Unique ID generator
def uuid_gen():
    return str(uuid.uuid4())

# Gate Secret Generator
def secret_gen():
    return str(random.randint(1000, 9999))

# DATABASE - SQL Alchemy
DATABASE_FILE = "gatedata_slave.sqlite"

engine = create_engine('sqlite:///%s'%(DATABASE_FILE), echo=False, connect_args={'check_same_thread': False}) #echo = True shows all SQL calls
Base = declarative_base()


# TABLES

# Gates table
# - gate_id (PK)
# - location
# - secret
# - number of activations
class Gates(Base):
    __tablename__ = 'gates'
    gate_id  = Column(String, primary_key = True)
    location = Column(String)
    secret   = Column(String, default = secret_gen)
    n_activations = Column(Integer, default = 0)

# Attempts table
# - id (PK)
# - gate_id
# - result
# - time
class Attempts(Base):
    __tablename__ = 'attempts'
    id            = Column(String, primary_key= True, default=uuid_gen)
    gate_id       = Column(String, ForeignKey('gates.gate_id'))
    successful    = Column(Boolean) # Successful or not
    time          = Column(DateTime(timezone=True), server_default=func.now())


Base.metadata.create_all(engine) #Create tables for the data models

Session = sessionmaker(bind=engine)
session = Session()

# INSERTS E UPDATES

# Insert or update gate
def insertGate(id, location):
    # Check if gate with gate_id already exists
    q = session.query(Gates).filter(Gates.gate_id == id).first()

    # If gate already exists update the location
    if(q):
        # Update gate
        session.query(Gates).filter(Gates.gate_id == id).update({Gates.location: location}) 

    # If gate doesn't exist, create the gate
    else:
        # Add gate
        gate = Gates(gate_id = id, location = location)
        session.add(gate)

    try:
        session.commit()
        status = 200
    except:
        session.rollback()
        status = 500
    return status

# Insert attempt
def insertAttempt(gate_id, successful):
    # Check if gate with gate_id exists
    q = session.query(Gates.gate_id).filter(Gates.gate_id == gate_id).first()

    if(q):
        attempt = Attempts(gate_id = gate_id, successful = successful)
        session.add(attempt)
        #try:
        session.commit()
        status = 200
        #except:
        #    session.rollback()
        #    status = 500
        return status

    else:
        return 404



# Aplicação - Flask
app = Flask(__name__)

@app.errorhandler(404)
def resource_not_found(e):
    return jsonify(error=str(e)), 404


@app.route('/')
def index():
    return

# Register gate
# POST /API/gates/
@app.route('/API/gates/', methods = ['POST'])
def registerGate():
    content = request.get_json()
    data = json.loads(content)
    try:
        # Verify if json content has the correct form
        gate_id  = data["gate_id"]
        location = data["location"]
    except:
        return abort(400)
    else:
        print("InsertGate: " + gate_id + " " + location)
        
        ig_status = insertGate(gate_id, location)

        if(ig_status == 200):
            # Query for secret 
            result = session.query(Gates.secret).filter(Gates.gate_id == gate_id).first()
            secret = {"secret": str(result.secret)}
            return jsonify(secret)

        else: #ig_status == 500
            #print("Insert/update error")
            err = {"error":"Insert/Update error"}
            return Response(response = json.dumps(err), status = 500)

# List gates
# GET /API/gates/
@app.route('/API/gates/', methods = ['GET'])
def listGates():
    # Query the database for all the gates
    gates = session.query(Gates.gate_id, Gates.location, Gates.secret, Gates.n_activations).all()
    
    # Check if there are gates
    if(gates):
        serializable_res = [r._asdict() for r in gates]
        return jsonify(serializable_res)
    else:
        return jsonify("")

# Show gate info
# GET /API/gates/{gate_id}/
@app.route('/API/gates/<path:gate_id>/', methods = ['GET'])
def gateInfo(gate_id):
    # Query the database for the gate with the specific gate_id 
    gate = session.query(Gates.gate_id, Gates.location, Gates.secret, Gates.n_activations
                        ).filter(Gates.gate_id == gate_id).all()
    
    # Check if such gate exists
    if(gate):
        serializable_res = [r._asdict() for r in gate]
        return jsonify(serializable_res)
    else:
        # return json with error details
        err = {"error": "Gate with the given Gate ID does not exist"}
        return Response(response = json.dumps(err), status = 404)

# Increment a gate's number of activations
#POST /API/gates/{gate_id}/activations
@app.route('/API/gates/<path:gate_id>/activations/', methods = ['POST'])
def incrementActivations(gate_id):
    # Query the database for the specific gate
    q = session.query(Gates.n_activations).filter(Gates.gate_id == gate_id).first()
    
    # Verify that the gate with gate_id exists
    if(q):
        curr_activations = q[0] + 1

        session.query(Gates).filter(Gates.gate_id == gate_id).update({Gates.n_activations: curr_activations})
        
        try:
            session.commit()
        except:
            session.rollback()
            err = {"error": "Database Error"}
            return Response(response = json.dumps(err), status = 500)

        return jsonify(curr_activations)

    # In case there is no gate with the specific gate_id
    else:
        # return json with error details
        err = {"error": "Gate with the given Gate ID does not exist"}
        return Response(response = json.dumps(err), status = 404)


# Validate gate secret
# GET /API/gates/{gate_id}/secrets/{secret}
@app.route('/API/gates/<path:gate_id>/secrets/<path:secret>/', methods = ["GET"])
def validateSecret(gate_id, secret):
    # Verify that the specified gate exists
    q_gate = session.query(Gates).filter(Gates.gate_id == gate_id).first()
    if(q_gate):
       pass
    else:
        err = {"error": f"Gate with Gate ID {gate_id} does not exist"}
        return Response(response = json.dumps(err), status = 404)

    # Verify the secret corresponds to the specified gate's secret
    q_secret = session.query(Gates.secret
                     ).filter(Gates.gate_id == gate_id
                     ).first()
    
    if(q_secret.secret == secret):
        return jsonify(True)
    else:
        return jsonify(False)


# Register Attempt
# POST /API/gates/{gate_id}/attempts/
@app.route('/API/gates/<path:gate_id>/attempts/', methods = ['POST'])
def registerAttempt(gate_id):
    data = json.loads(request.get_json())
    try:
        result = data["successful"]
    except:
        return abort(400)
    else:
        if(isinstance(result, bool)):
            print(gate_id)
            status = insertAttempt(gate_id, result)
            if(status!=200):
                return abort(status)
        else:
            return abort(400)

    return jsonify("")

# List Attempts
# GET /API/gates/{gate_id}/attempts/
@app.route('/API/gates/<path:gate_id>/attempts/', methods = ['GET'])
def listAttempts(gate_id):
    # Query the database for all the attempts with gate_id
    attempts = session.query(Attempts.id, Attempts.successful, Attempts.time).filter(Attempts.gate_id == gate_id).all()
    
    # Check if there are gates
    if(attempts):
        serializable_res = [r._asdict() for r in attempts]
        return jsonify(serializable_res)
    else:
        err = {"error": f"Gate with Gate ID {gate_id} does not exist"}
        return Response(response = json.dumps(err), status = 404)

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5001, debug=True)