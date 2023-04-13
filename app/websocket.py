import websocket
import threading
import json
from app import socketio


class USDTWebSocket():

    def __init__(self, asset) -> None:
        self.ws = websocket.WebSocketApp(f'wss://stream.binance.com:9443/ws/{asset.lower()}usdt@aggTrade',
                              on_open=self.on_open,
                              on_message=self.on_message,
                              on_error=self.on_error,
                              on_close=self.on_close)
        self.price = None
        threading.Thread(target=self.run).start()

    def on_message(self, ws, message):
        jsonmsg = json.loads(message)
        self.price = float(jsonmsg['p'])


    def on_error(self, ws, error):
        print(error)

    def on_close(self, ws, close_status_code, close_msg):
        self.run()

    def on_open(self, ws):
        print("Init websocket connection")
        
    def run(self):
        self.ws.run_forever()  




