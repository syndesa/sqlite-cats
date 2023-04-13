from app import socketio, db, app
from app.websocket import USDTWebSocket
from app.models import Trade, trade_schema
from abc import ABC, abstractmethod
from queue import Queue
# import _thread
# import eventlet
import threading
import heapq


user_sid = {}
sid_user = {} 
user_active_trades = {}
user_pending_trades = {}


class TradeDispatcher():

    def __init__(self, asset) -> None:
        print('td init')
        self.asset = asset
        self._active_longs = []
        self._active_shorts = []
        self._pending_longs = []
        self._pending_shorts = []
        self._socket = USDTWebSocket(f'{self.asset}')
        # eventlet.spawn(self.monitor)
        threading.Thread(target=self.monitor).start()
        # socketio.start_background_task(target=self.monitor)  # Run as a flask-socketio thread to emit events to the client
        # _thread.start_new_thread(self.monitor, ())  #Create monitor thread
        
    def monitor(self):
        print(f'Starting {self.asset} dispatcher background task')
        while True:
            # print(f'({self.asset}USDT) ->  Active Longs: {self._active_longs} | Pending Longs: {self._pending_longs} | Active Shorts: {self._active_shorts} | Pending Shorts: {self._pending_shorts}')
            if self._active_longs:
                try:
                    if self._active_longs[0].liq > float(self._socket.price):
                        liquidated = heapq.heappop(self._active_longs)
                        liquidated.status = 'liquidated'
                        socketio.emit('closeTrade', trade_schema.dump(liquidated), to = user_sid[liquidated.user_id])
                        user_active_trades[liquidated.user_id][liquidated.contract].remove(liquidated)
                        trade_chain.add_to_queue(liquidated)
                        print(f'{liquidated} ({liquidated.contract} Long) is Liquidated!')
                except TypeError:
                    heapq.heappop(self._active_longs)

            if self._active_shorts:
                try:
                    if self._active_shorts[0].liq < float(self._socket.price):
                        liquidated = heapq.heappop(self._active_shorts)
                        liquidated.status = 'liquidated'
                        socketio.emit('closeTrade', trade_schema.dump(liquidated), to = user_sid[liquidated.user_id])
                        trade_chain.add_to_queue(liquidated)
                        print(f'{liquidated} ({liquidated.contract} Short) is Liquidated!')
                except TypeError:
                    heapq.heappop(self._active_shorts)

            if self._pending_longs:
                try:
                    if self._pending_longs[0].open > float(self._socket.price):
                        active = heapq.heappop(self._pending_longs)
                        active.status = 'active'
                        socketio.emit('closeTrade', trade_schema.dump(active), to=user_sid[active.user_id])
                        user_pending_trades[active.user_id][active.contract].remove(active)
                        trade_chain.add_to_queue(active)
                        print(f'{active} ({active.contract} Long) order purchased!')
                except TypeError:
                    heapq.heappop(self._pending_longs)

            if self._pending_shorts:
                try:
                    if self._pending_shorts[0].open < float(self._socket.price):
                        active = heapq.heappop(self._pending_shorts)
                        active.status = 'active'
                        socketio.emit('closeTrade', trade_schema.dump(active), to=user_sid[active.user_id])
                        user_pending_trades[active.user_id][active.contract].remove(active)
                        trade_chain.add_to_queue(active)
                        print(f'{active} ({active.contract} Short) order purchased!')
                except TypeError:
                    heapq.heappop(self._pending_shorts)


    def add_trade(self, trade: Trade) -> None:
        if trade.direction == 'Long':
            if trade.status == 'pending':
                heapq.heappush(self._pending_longs, trade)
            else: 
                heapq.heappush(self._active_longs, trade)
        else: 
            if trade.status =='pending':
                heapq.heappush(self._pending_shorts, trade)
            else:
                heapq.heappush(self._active_shorts, trade)






# Chain of Responsibility Behaviour Design Pattern
class TradeChain():
    _instance = None
    _trade_queue = Queue()
    
    def __init__(self) -> None:
        # _thread.start_new_thread(self.exec, ())  # Asynchronously monitor trade queue and propagate down the chain if any trades in queue
        # eventlet.spawn(self.exec)
        threading.Thread(target=self.exec).start()
    # Implement chain as a singleton (limit thread to one)
    def __new__(cls):
        if not cls._instance: 
            cls._instance = object.__new__(cls)
        return cls._instance

    def exec(self) -> None:
        while True:
            if not self._trade_queue.empty():
                ClosedTradeHandler().handle(self._trade_queue.get())

    def add_to_queue(self, trade):
        self._trade_queue.put(trade)


class ITradeHandler(ABC):
    @abstractmethod
    def set_next(self, handler):
        pass

    @abstractmethod
    def handle(self, request):
        pass

    @abstractmethod
    def average_trade(self, t1, t2):
        pass
    

class AbstractTradeHandler(ITradeHandler):
    _next_handler = None

    def set_next(self, handler):
        self._next_handler = handler()

    @abstractmethod
    def handle(self, trade):
        if self._next_handler:
            self._next_handler.handle(trade)
    
    @staticmethod
    def recalculate_trade(trade):
        mmr = {'BTCUSDT': 0.005, 'ETHUSDT': 0.01}
        imr = 1/float(trade.leverage)
        trade.liq = round(float(trade.open)*(1-imr+mmr[trade.contract]), 2) if trade.direction == 'Long' else round(float(trade.open)*(1+imr-mmr[trade.contract]), 2)
        trade.qty = round(float(trade.value)/float(trade.leverage), 4) #When changing the leverage of a trade recalculate the inital margin (qty)

        if trade.status == 'active' and trade.contract == 'BTCUSDT':
            print(f'Reheapifying {trade.contract} Active {trade.direction}')
            heapq.heapify(bitcoin_dispatcher._active_longs) if trade.direction == 'Long' else heapq.heapify(bitcoin_dispatcher._active_shorts)
        elif trade.status == 'active' and trade.contract == 'ETHUSDT':
            print(f'Reheapifying {trade.contract} Active {trade.direction}')
            heapq.heapify(ethereum_dispatcher._active_longs) if trade.direction == 'Long' else heapq.heapify(ethereum_dispatcher._active_shorts)

    def average_trade(self, trade1, trade2):
        if float(trade1.leverage) != float(trade2.leverage):
            trade1.leverage = float(trade2.leverage)
            AbstractTradeHandler.recalculate_trade(trade1)
        
        if trade1.status == trade2.status:
            trade1.open = round((float(trade1.open)*float(trade1.qty) + float(trade2.open)*float(trade2.qty))/(float(trade1.qty)+ float(trade2.qty)), 2)
            trade1.value = round(float(trade1.value) + float(trade2.value), 4) 
            trade1.qty = round(float(trade1.qty) + float(trade2.qty), 4)
            del(trade2)
            if trade1.status == 'pending' and trade1.contract == 'BTCUSDT':
                heapq.heapify(bitcoin_dispatcher._pending_longs) if trade1.direction == 'Long' else heapq.heapify(bitcoin_dispatcher._pending_shorts)
            elif trade1.status == 'pending' and trade1.contract == 'ETHUSDT':
                heapq.heapify(ethereum_dispatcher._pending_longs) if trade1.direction == 'Long' else heapq.heapify(ethereum_dispatcher._pending_shorts)

            print(f'Updated Trade: {trade_schema.dump(trade1)}')

        with app.test_request_context('/'):
            socketio.emit('updateTrade', trade_schema.dump(trade1), to=user_sid[trade1.user_id])

        with app.app_context():
            db.session.merge(trade1)
            db.session.commit()
            return




class ClosedTradeHandler(AbstractTradeHandler):
    def handle(self, trade):
        self.set_next(ActiveTradeHandler)
        if trade.status == 'closed' or trade.status == 'liquidated':
            with app.app_context():
                db.session.merge(trade)
                db.session.commit()
            #Set the following variables to closed so the Dispatcher can ignore them
            if trade.status == 'closed':
                trade.open = trade.liq = 'closed'            
            # #If there's no pending or active trades for the user then delete user from hash maps
            # if not any(user_active_trades[trade.user_id].values() and user_pending_trades[trade.user_id].values()):
            #     del(user_active_trades[trade.user_id])
            #     del(user_pending_trades[trade.user_id])
            return
        else:
            # Pass the request to the next handler
            super().handle(trade)


class ActiveTradeHandler(AbstractTradeHandler):
    def handle(self, trade):
        self.set_next(PendingTradeHandler)

        active_trade = [t for t in user_active_trades[trade.user_id][trade.contract] if t.direction == trade.direction]
        if active_trade:
            print(f'ActiveTradeHandler: Active Trade {active_trade} Found!- Updating found trade')  
            self.average_trade(active_trade[0], trade)
        # No Active Trades Found & Incoming Trade is Active (Market): Add to db
        elif trade.status == 'active':
            print(f'ActiveTradeHandler: {trade.contract} ({trade.direction}) Market Order Placed! (Added to DB)')
            with app.app_context():
                db.session.add(trade)
                db.session.commit()
                user_active_trades[trade.user_id][trade.contract].append(trade)
                bitcoin_dispatcher.add_trade(trade) if trade.contract == 'BTCUSDT' else ethereum_dispatcher.add_trade(trade)
            with app.test_request_context('/'):
                socketio.emit('newTrade', trade_schema.dump(trade), to = user_sid[trade.user_id])
        # Pass the request to the next handler
        super().handle(trade)


class PendingTradeHandler(AbstractTradeHandler):
    def handle(self, trade):

        pending_trade = [t for t in user_pending_trades[trade.user_id][trade.contract] if t.direction == trade.direction]
        if pending_trade:
            print(f'PendingTradeHandler: Pending Limit Trade {pending_trade} Found ! - Updating found trade')
            self.average_trade(pending_trade[0], trade)
            return
        elif trade.status == 'pending':
            print('PendingTradeHandler: New Pending Limit Order Placed! (Added to DB)')
            with app.app_context():
                db.session.add(trade)
                db.session.commit()
                user_pending_trades[trade.user_id][trade.contract].append(trade)
                bitcoin_dispatcher.add_trade(trade) if trade.contract == 'BTCUSDT' else ethereum_dispatcher.add_trade(trade)
            with app.test_request_context('/'):
                socketio.emit('newTrade', trade_schema.dump(trade), to=user_sid[trade.user_id])
                print(user_sid)


bitcoin_dispatcher = socketio.start_background_task(TradeDispatcher, 'BTC') #Create trade dispatcher (monitors trades + spawns websocket for live prices) for Bitcoin 
ethereum_dispatcher = socketio.start_background_task(TradeDispatcher, 'ETH') #Create trade dispatcher (monitors trades + spawns websocket for live prices) for Ethereum

# ethereum_dispatcher = TradeDispatcher('ETH') #Create trade dispatcher (monitors trades + spawns websocket for live prices) for Ethereum

# trade_chain = TradeChain()rt_background_task(TradeChain)

trade_chain = socketio.start_background_task(TradeChain)
