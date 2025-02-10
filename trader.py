import time

from pymemcache.client import base

from broker import Broker


class Trader(Broker):

    def __init__(self):

        super().__init__()

        self.memcache = base.Client(server=(self.MEMCACHED_HOST, self.MEMCACHED_PORT), key_prefix="ogaden")

        self._base_quote_balance = 0.0

        self._purchase_price = 0.0

        self.position = "BUY"
        self.signal = "HOLD"

    @property
    def BASE_QUOTE_BALANCE(self):
        self._base_quote_balance = self._base_balance * self._current_price + self._quote_balance
        return self._base_quote_balance

    @property
    def PURCHASE_PRICE(self):
        return self._purchase_price

    @BASE_QUOTE_BALANCE.setter
    def BASE_QUOTE_BALANCE(self, value):
        self._base_quote_balance = value

    @PURCHASE_PRICE.setter
    def PURCHASE_PRICE(self, value):
        self._purchase_price = value

    def setup(self):

        if self.SANDBOX:
            self.BASE_BALANCE = 0.0
            self.QUOTE_BALANCE = 10.0

        self.status()

    def execute(self):

        self.fetch_vars()

        self.fetch_data()

        self.calculate_rsi()
        self.calculate_rsi_signal()

        if self.can_buy():

            self.execute_buy()

        elif self.can_sell():

            self.execute_sell()

        else:

            self.execute_hold()

        self.status()

        time.sleep(60)

    def execute_buy(self):

        if super().execute_buy():
            self.PURCHASE_PRICE = self.CURRENT_PRICE
            self.position = "SELL"

    def execute_sell(self):

        if super().execute_sell():
            self.PURCHASE_PRICE = 0.0
            self.position = "BUY"

    def execute_hold(self):

        print()
        print("HOLD")

    def can_buy(self):
        if self.position != "BUY":
            return False

        self.signal = self.data["signal_rsi"].iloc[-1]

        return self.signal == "BUY"

    def can_sell(self):
        if self.position != "SELL":
            return False

        self.signal = self.data["signal_rsi"].iloc[-1]

        return self.signal == "SELL"

    def status(self):

        print()
        print(f"SYMBOL             : {self.SYMBOL}")
        print(f"POSITION / SIGNAL  : {self.position} / {self.signal}")
        print(f"BASE_BALANCE       : {self.BASE_BALANCE:.8f}")
        print(f"QUOTE_BALANCE      : {self.QUOTE_BALANCE:.8f}")
        print(f"BASE_QUOTE_BALANCE : {self.BASE_QUOTE_BALANCE:.8f}")
        print(f"CURRENT_PRICE      : {self.CURRENT_PRICE:.8f}")
        print(f"PURCHASE_PRICE     : {self.PURCHASE_PRICE:.8f}")

        data = {
            "symbol": self.SYMBOL,
            "position": self.position,
            "signal": self.signal,
            "base_balance": f"{self.BASE_BALANCE:.8f}",
            "quote_balance": f"{self.QUOTE_BALANCE:8f}",
            "base_quote_balance": f"{self.BASE_QUOTE_BALANCE:.8f}",
            "current_price": f"{self.CURRENT_PRICE:.8f}",
            "purchase_price": f"{self.PURCHASE_PRICE:.8f}",
        }

        self.memcache.set_many(data)
