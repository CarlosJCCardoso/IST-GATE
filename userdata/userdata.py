# userdata2.py

# SQL Alchemy imports
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Flask imports
from flask import Flask
from flask import request
from flask import abort
from flask import jsonify
from flask import Response

# Misc Imports
import uuid
import os
import datetime
import json


# Unique ID generator
def uuid_gen():
    return str(uuid.uuid4())

DATABASE_FILE = "userdata.sqlite"
db_exists = False
if os.path.exists(DATABASE_FILE):
    db_exists = True
    print("\t database already exists")

engine = create_engine('sqlite:///%s'%(DATABASE_FILE), echo=False, connect_args={'check_same_thread': False}) #echo = True shows all SQL calls

Base = declarative_base()

# TABLES

# Users table
# - user_id (PK)
# - role
# - code_id
# - created_at - datetime of creation of code
class Users(Base):
    __tablename__  = 'users'
    user_id        = Column(String, primary_key = True)
    code_id        = Column(String)
    code_created_at     = Column(DateTime(timezone=True)
                             , default=datetime.datetime.utcnow())

# Logs table
# - log_id (PK)
# - gate_id
# - time
# - user_id (FK)
class Logs(Base):
    __tablename__ = 'logs'
    log_id   = Column(String, primary_key = True, default = uuid_gen)
    gate_id  = Column(String)
    time     = Column(DateTime(timezone=True)
                             , default=datetime.datetime.utcnow()) 
    user_id  = Column(String, ForeignKey('users.user_id'))


Base.metadata.create_all(engine) #Create tables for the data models

Session = sessionmaker(bind=engine)
session = Session()

# INSERTS

# Insert user
def insertUser(id):
    # Check if gate with gate_id already exists
    q = session.query(Users).filter(Users.user_id == id).first()

    # If user already exists
    if(q):
        pass
    # If user doesn't exist, create the user
    else:
        # Add user
        user = Users(user_id = id)
        session.add(user)

    try:
        session.commit()
        status = 200
    except:
        session.rollback()
        status = 500
    return status

# Insert code
def insertCode(user_id):
    # Check if user exists
    q = session.query(Users).filter(Users.user_id == user_id).first()

    # If user exists insert new code/ update code
    if(q):
        q = session.query(Users).filter(Users.user_id == user_id
                    ).update({Users.code_id: uuid_gen(), 
                              Users.code_created_at:datetime.datetime.utcnow()})
        try:
            session.commit()  
        except:
            session.rollback()
            status_code = 500
            response = {"err":"Insert/Update error", "status":status_code}
        else:
            status_code = 200
            q = session.query(Users.code_id).filter(Users.user_id == user_id).first()
            code = q.code_id
            response = {"status": status_code, "code": code}

    # User with user_id not found
    else:
        status_code = 404
        response = {"err":"User with user_id not found", "status":status_code}

    print(response)
    return response

# Insert Log
def insertLog(user_id, gate_id):
    q = session.query(Users).filter(Users.user_id == user_id).first()

    # Check if user with user_id exists
    if(q):
        log = Logs(user_id = user_id, gate_id = gate_id)
        session.add(log)
        try:
            session.commit()
        except:
            session.rollback()
            status_code = 500
            response = {"err":"Insert/Update error", "status":status_code}
        else:
            status_code = 200
            response = {"status":status_code}

    # If user with user_id does not exist
    else:
        status_code = 404
        response = {"err":"User with user_id not found", "status":status_code}
    return response


# Aplicação - Flask
app = Flask(__name__)    

@app.route('/')
def index():
    return

# Register new user
# POST /API/users
@app.route('/API/users/', methods=['POST'])
def registerUser():
    content = request.get_json()
    data = json.loads(content)
    try:
        # Verify if json content has the correct format
        user_id = str(data["user_id"])
    except:
        return abort(400)
    else:
        print("InsertUser: " + user_id + " ")
        status = insertUser(user_id)

        if(status == 200):
            return jsonify("")
        else:
            if(status == 500):
                err = {"error":"Insert/Update error"}
            else: # status == 404
                err = {"error": f'User with user_id {user_id} does not exist'}
            return Response(response = json.dumps(err), status = status)

# Create new user code
@app.route('/API/users/<path:user_id>/codes/', methods = ["POST"])
def newUserCode(user_id):
    # Try to insert new code
    response = insertCode(user_id)
    try: 
        code = response["code"]
    except:
        try: 
            error = response["err"]
        except:
            return jsonify("An unexpected error occured")
        else:
            return jsonify(error)
    else:
        return jsonify(code)

# Return user_id from code
# GET /API/codes/{code_id}
@app.route('/API/codes/<path:code_id>')
def returnCodeInfo(code_id):
    q = session.query(Users.user_id, Users.code_created_at
              ).filter(Users.code_id == code_id
              ).first()
    # If user with code equal to code_id exists return user_id
    if(q):
        user_id = q.user_id
        created_at = q.code_created_at
        print(created_at)
        code_info = {"user_id": user_id, "created_at": created_at}
        return jsonify(code_info)
    # If there is no user with code equal to code_id return 404
    else:
        return abort(404)


# Register Log
@app.route('/API/logs/', methods = ["POST"])
def registerLog():
    try:
        content = json.loads(request.get_json())
        # Verify if json content has the correct form
        user_id  = str(content["user_id"])
        gate_id = str(content["gate_id"])
    except:
        return abort(400)

    response = insertLog(user_id, gate_id)
    if(response["status"] == 200):
        return jsonify(200)
    else:
        return jsonify(response)


# Show Logs by user
@app.route('/API/users/<path:user_id>/logs/')
def listLogs(user_id):
    # Check if user with user_id exists
    user = session.query(Users).filter(Users.user_id == user_id).first()

    if(user):
        # Check if there are any logs associated with user with user_id
        logs = session.query(Logs.log_id, Logs.user_id, Logs.gate_id, Logs.time
                ).filter(Logs.user_id == user_id
                ).all()
        if(logs):
            serializable_res = [l._asdict() for l in logs]
            return jsonify(serializable_res)
        else:
            return jsonify("")
    else:
        return abort(404)



if __name__ == "__main__":
    app.run(host='127.0.0.1', port = 5100, debug=True)


    

        
    

    
        
