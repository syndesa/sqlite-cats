from app import app, socketio
from flaskwebgui import FlaskUI



if __name__ == '__main__':
    # socketio.run(app, debug=True)
    FlaskUI(app=app, socketio=socketio, server="flask_socketio").run()
