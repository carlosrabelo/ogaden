import os

from dotenv import load_dotenv


class Config:

    def __init__(self):

        load_dotenv()

        self.SANDBOX = os.getenv("SANDBOX", "false").lower() in ["true", "yes", "1"]

        self.MEMCACHED_HOST = os.getenv("MEMCACHED_HOST", "localhost")
        self.MEMCACHED_PORT = int(os.getenv("MEMCACHED_PORT", 11211))

        self.API_KEY = os.getenv("API_KEY")
        self.API_SECRET = os.getenv("API_SECRET")

        self.BASE_ASSET = os.getenv("BASE_ASSET", "BTC")
        self.QUOTE_ASSET = os.getenv("QUOTE_ASSET", "USDT")

        self.SYMBOL = self.BASE_ASSET + self.QUOTE_ASSET
