from abc import ABC, abstractmethod
from binance.client import Client



class KLine(ABC):
    def __init__(self) -> None:
        self.client = Client()

    @abstractmethod
    def get_historical_data():
        pass

    @abstractmethod
    def kline_interval():
        pass

class KLineETH(KLine):
    
    def __init__(self, ticker, time_interval) -> None:
        self.client = Client()
        self.ticker = ticker
        self.time_interval = time_interval

    def get_historical_data(self, volume:str = False) -> list: 
        candles = self.client.get_historical_klines(self.ticker, getattr(Client, self.time_interval))
        return KLineETH.parse_klines(candles, volume=True) if volume else KLineETH.parse_klines(candles)

    def kline_interval():
        pass

    @staticmethod
    def parse_klines(candles, volume:str=False):
        n = ['time', 'open', 'high', 'low', 'close', 'value']
        # parsed = [{n[0]:c[0]/1000, n[1]:c[1], n[2]:c[2], n[3]:c[3], n[4]:c[4]}  for c in candles]
        parsed = [{n[0]:c[0]/1000, n[5]:c[5]}  for c in candles] if volume else [{n[0]:c[0]/1000, n[1]:c[1], n[2]:c[2], n[3]:c[3], n[4]:c[4]}  for c in candles]
        return parsed

class KLineBTC(KLine):
    
    def __init__(self, ticker, time_interval) -> None:
        super().__init__()
        self.ticker = ticker
        self.time_interval = time_interval

    def get_historical_data(self, volume:str = False) -> list: 
        candles = self.client.get_historical_klines(self.ticker, getattr(Client, self.time_interval))
        return KLineBTC.parse_klines(candles, volume=True) if volume else KLineBTC.parse_klines(candles)
        

    
    def kline_interval():
        pass

    @staticmethod
    def parse_klines(candles, volume:str=False):
        n = ['time', 'open', 'high', 'low', 'close', 'value']
        # parsed = [{n[0]:c[0]/1000, n[1]:c[1], n[2]:c[2], n[3]:c[3], n[4]:c[4]}  for c in candles]
        parsed = [{n[0]:c[0]/1000, n[5]:c[5]}  for c in candles] if volume else [{n[0]:c[0]/1000, n[1]:c[1], n[2]:c[2], n[3]:c[3], n[4]:c[4]}  for c in candles]
        return parsed



class KLineFactory():
    _instance = None
    _TIME_CONSTANTS = { "1m": 'KLINE_INTERVAL_1MINUTE',
                        "15m": 'KLINE_INTERVAL_15MINUTE',
                        "1h": 'KLINE_INTERVAL_1HOUR',
                        "1d": 'KLINE_INTERVAL_1DAY'}

    def __new__(cls):
        if not cls._instance: 
            cls._instance = object.__new__(cls)
        return cls._instance
    
    def create_kline_object(self, ticker:str, time_interval:int) -> KLine:
        if ticker.upper() == 'BTC': return KLineBTC('BTCUSDT', KLineFactory._TIME_CONSTANTS[f'{time_interval}'])
        elif ticker.upper() == 'ETH': return KLineETH('ETHUSDT', KLineFactory._TIME_CONSTANTS[f'{time_interval}'])
        else: raise KeyError


