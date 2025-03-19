import os

from dotenv import load_dotenv


class Loader:

    def __init__(self):

        load_dotenv()

        self.SANDBOX = os.getenv("SANDBOX", "true").lower() in ["true", "yes", "1"]

        self.MEMCACHED_HOST = os.getenv("MEMCACHED_HOST", "localhost")
        self.MEMCACHED_PORT = int(os.getenv("MEMCACHED_PORT", 11211))

        self.API_KEY = os.getenv("API_KEY")
        self.API_SECRET = os.getenv("API_SECRET")

        self.BASE_BALANCE_DEFAULT = float(os.getenv("BASE_BALANCE", 0.0))
        self.QUOTE_BALANCE_DEFAULT = float(os.getenv("QUOTE_BALANCE", 10.0))

        self.BASE_ASSET = os.getenv("BASE_ASSET", "BTC")
        self.QUOTE_ASSET = os.getenv("QUOTE_ASSET", "USDT")

        self.INTERVAL = os.getenv("INTERVAL", "15m")

        self.TIMEZONE = os.getenv("TIMEZONE", "America/Cuiaba")

        self.FAST_SMA = int(os.getenv("FAST_SMA", 7))
        self.SLOW_SMA = int(os.getenv("SLOW_SMA", 25))

        self.FAST_EMA = int(os.getenv("FAST_EMA", 7))
        self.SLOW_EMA = int(os.getenv("SLOW_EMA", 25))

        self.RSI_PERIOD = int(os.getenv("RSI_PERIOD", 14))

        limit = self.SLOW_SMA * 2 + self.FAST_SMA

        self.LIMIT = int(os.getenv("LIMIT", limit))

        self.RSI_BUY_THRESHOLD = int(os.getenv("RSI_BUY_THRESHOLD", 30))
        self.RSI_SELL_THRESHOLD = int(os.getenv("RSI_SELL_THRESHOLD", 70))

        self.PROFIT_THRESHOLD = float(os.getenv("PROFIT_THRESHOLD", 0.0))

        self.TRAILING_THRESHOLD = float(os.getenv("TRAILING_THRESHOLD", 0.0))

        self.SYMBOL = f"{self.BASE_ASSET}{self.QUOTE_ASSET}"

        self.PROFIT_ENABLE = True if self.PROFIT_THRESHOLD != 0.0 else False

        self.TRAILING_ENABLE = True if self.TRAILING_THRESHOLD != 0.0 else False

        self.TRAILING_THRESHOLD = 1.0 - self.TRAILING_THRESHOLD / 100.0
