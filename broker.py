from config import Config

from binance.client import Client


class Broker:

    def __init__(self, config: Config):

        self._base_balance = 0.0
        self._quote_balance = 0.0

        self._current_price = 0.0

        self.config = config

        self.binance = Client(config.API_KEY, config.API_SECRET)

    @property
    def BASE_BALANCE(self):
        if self.config.SANDBOX:
            return self._base_balance
        return self.get_asset_balance(self.config.BASE_ASSET)

    @property
    def QUOTE_BALANCE(self):
        if self.config.SANDBOX:
            return self._quote_balance
        return self.get_asset_balance(self.config.QUOTE_ASSET)

    @property
    def CURRENT_PRICE(self):
        self._current_price = self.get_current_price(self.config.SYMBOL)
        return self._current_price

    @BASE_BALANCE.setter
    def BASE_BALANCE(self, value):
        self._base_balance = value

    @QUOTE_BALANCE.setter
    def QUOTE_BALANCE(self, value):
        self._quote_balance = value

    @CURRENT_PRICE.setter
    def CURRENT_PRICE(self, value):
        self._current_price = value

    def get_asset_balance(self, asset) -> float:
        try:
            account_info = self.binance.get_account()
            return float(next((balance["free"] for balance in account_info["balances"] if balance["asset"] == asset), 0.0))
        except Exception as e:
            print(f"Error getting balance for {asset}: {e}")
            return 0.0

    def get_current_price(self, symbol) -> float:
        try:
            ticker = self.binance.get_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        except Exception as e:
            print(f"Error getting current price for {symbol}: {e}")
            return 0.0
