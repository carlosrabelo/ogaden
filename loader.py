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

        self.BASE_ASSET = os.getenv("BASE_ASSET", "BTC")
        self.QUOTE_ASSET = os.getenv("QUOTE_ASSET", "USDT")

        self.INTERVAL = os.getenv("INTERVAL", "1m")

        self.LIMIT = int(os.getenv("LIMIT", 1000))

        self.TIMEZONE = os.getenv("TIMEZONE", "America/Cuiaba")

        self.FAST_SMA = int(os.getenv("FAST_SMA", 7))
        self.SLOW_SMA = int(os.getenv("SLOW_SMA", 25))

        self.FAST_EMA = int(os.getenv("FAST_EMA", 7))
        self.SLOW_EMA = int(os.getenv("SLOW_EMA", 25))

        self.RSI_PERIOD = int(os.getenv("RSI_PERIOD", 14))

        self.RSI_BUY_THRESHOLD = int(os.getenv("RSI_BUY_THRESHOLD", 30))
        self.RSI_SELL_THRESHOLD = int(os.getenv("RSI_SELL_THRESHOLD", 70))

        self.SYMBOL = f"{self.BASE_ASSET}{self.QUOTE_ASSET}"
