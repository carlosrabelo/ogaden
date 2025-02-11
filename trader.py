import time

from pymemcache.client import base

from broker import Broker


class Trader(Broker):

    def __init__(self):

        super().__init__()

        self.memcache = base.Client(server=(self.MEMCACHED_HOST, self.MEMCACHED_PORT), key_prefix="ogaden")

        self._base_quote_balance = 0.0
        self._expected_balance = 0.0

        self._purchase_price = 0.0

        self._difference_price_v = 0.0
        self._difference_price_p = 0.0

        self.POSITION = "BUY"
        self.SIGNAL = "HOLD"

    @property
    def BASE_QUOTE_BALANCE(self):
        return self._base_quote_balance

    @property
    def PURCHASE_PRICE(self):
        return self._purchase_price

    @property
    def EXPECTED_BALANCE(self):
        return self._expected_balance

    @property
    def DIFFERENCE_PRICE_V(self):
        return self._difference_price_v

    @property
    def DIFFERENCE_PRICE_P(self):
        return self._difference_price_p

    @BASE_QUOTE_BALANCE.setter
    def BASE_QUOTE_BALANCE(self, value):
        self._base_quote_balance = value

    @PURCHASE_PRICE.setter
    def PURCHASE_PRICE(self, value):
        self._purchase_price = value

    @EXPECTED_BALANCE.setter
    def EXPECTED_BALANCE(self, value):
        self._expected_balance = value

    @DIFFERENCE_PRICE_V.setter
    def DIFFERENCE_PRICE_V(self, value):
        self._difference_price_v = value

    @DIFFERENCE_PRICE_P.setter
    def DIFFERENCE_PRICE_P(self, value):
        self._difference_price_p = value

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

        self.update_position()

        self.status()

        time.sleep(60)

    def execute_buy(self):

        if super().execute_buy():
            self.PURCHASE_PRICE = self.CURRENT_PRICE
            self.POSITION = "SELL"

    def can_buy(self):

        if self.POSITION != "BUY":
            return False

        self.SIGNAL = self.data["signal_rsi"].iloc[-1]

        return self.SIGNAL == "BUY"

    def can_sell(self):

        if self.POSITION != "SELL":
            return False

        self.SIGNAL = self.data["signal_rsi"].iloc[-1]

        return self.SIGNAL == "SELL"

    def execute_sell(self):

        if super().execute_sell():
            self.PURCHASE_PRICE = 0.0
            self.POSITION = "BUY"

    def execute_hold(self):

        print()
        print("HOLD")

    def update_position(self):

        self.BASE_QUOTE_BALANCE = self.BASE_BALANCE * self.CURRENT_PRICE

        self.EXPECTED_BALANCE = self.BASE_BALANCE * self.CURRENT_PRICE + self.QUOTE_BALANCE

        self.DIFFERENCE_PRICE_V = self.CURRENT_PRICE - self.PURCHASE_PRICE if self.PURCHASE_PRICE != 0.0 else 0.0
        self.DIFFERENCE_PRICE_P = self.DIFFERENCE_PRICE_V / self.PURCHASE_PRICE * 100.0 if self.PURCHASE_PRICE != 0.0 else 0.0

    def status(self):

        print()
        print(f"SYMBOL             : {self.SYMBOL}")
        print(f"INTERVAL           : {self.INTERVAL}")
        print(f"POSITION / SIGNAL  : {self.POSITION} / {self.SIGNAL}")
        print(f"BASE_BALANCE       : {self.BASE_BALANCE:.8f}")
        print(f"QUOTE_BALANCE      : {self.QUOTE_BALANCE:.8f}")
        print(f"BASE_QUOTE_BALANCE : {self.BASE_QUOTE_BALANCE:.8f}")
        print(f"EXPECTED_BALANCE   : {self.EXPECTED_BALANCE:.8f}")
        print(f"CURRENT_PRICE      : {self.CURRENT_PRICE:.8f}")
        print(f"PURCHASE_PRICE     : {self.PURCHASE_PRICE:.8f}")
        print(f"DIFFERENCE_PRICE_V : {self.DIFFERENCE_PRICE_V:.8f}")
        print(f"DIFFERENCE_PRICE_P : {self.DIFFERENCE_PRICE_P:.2f}%")

        data = {
            "symbol": self.SYMBOL,
            "interval": self.INTERVAL,
            "position": self.POSITION,
            "signal": self.SIGNAL,
            "base_balance": f"{self.BASE_BALANCE:.8f}",
            "quote_balance": f"{self.QUOTE_BALANCE:8f}",
            "base_quote_balance": f"{self.BASE_QUOTE_BALANCE:.8f}",
            "expected_balance": f"{self.EXPECTED_BALANCE:.8f}",
            "current_price": f"{self.CURRENT_PRICE:.8f}",
            "purchase_price": f"{self.PURCHASE_PRICE:.8f}",
            "difference_price": f"{self.DIFFERENCE_PRICE_V:.8f} ( {self.DIFFERENCE_PRICE_P:.2f}% )",
        }

        self.memcache.set_many(values=data, expire=120)
