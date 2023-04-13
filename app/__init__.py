from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow 
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_cors import CORS
from app.klines import KLineFactory
from flask_socketio import SocketIO


app = Flask(__name__)
CORS(app)
# app.config['SQLALCHEMY_DATABASE_URI'] ='mysql+mysqlconnector://desaulne:B0ILmZNZEtRujjcA@desaulne.mysql.pythonanywhere-services.com/desaulne$cats'  #Database configuration 
app.config['SQLALCHEMY_DATABASE_URI'] ='sqlite:///catstrading'  #Database configuration 

app.config['SECRET_KEY']= '0c1d6ed2ec3c5f30bb293a1c59f057a7'
socketio = SocketIO(app, ping_interval = 5, ping_timeout = 100, logger=True, cors_allowed_origins="*", async_mode = "threading") #Required for client-server socket comm

# padbpw ->  B0ILmZNZEtRujjcA


db = SQLAlchemy(app) #Create the database connection 
ma = Marshmallow(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
factory = KLineFactory()


from app import controller, klines, models, forms, dispatcher

# create db if does not exists.
with app.app_context():
    db.create_all()
