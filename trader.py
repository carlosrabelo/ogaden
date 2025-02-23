import time

from datetime import datetime
from zoneinfo import ZoneInfo

from pymemcache.client import base

from broker import Broker


class Trader(Broker):

    def __init__(self):

        super().__init__()

        self.memcache = base.Client(server=(self.MEMCACHED_HOST, self.MEMCACHED_PORT), key_prefix="ogaden")

        self._base_quote_balance = 0.0
        self._expected_balance = 0.0

        self._purchase_price = 0.0

        self._trailing_price = 0.0

        self._diff_price_v = 0.0
        self._diff_price_p = 0.0

        self.POSITION = "BUY"

        self.SIGNAL_SMA = "HOLD"
        self.SIGNAL_RSI = "HOLD"

    # region

    @property
    def BASE_QUOTE_BALANCE(self):
        return self._base_quote_balance

    @property
    def EXPECTED_BALANCE(self):
        return self._expected_balance

    @property
    def PURCHASE_PRICE(self):
        return self._purchase_price

    @property
    def TRAILING_PRICE(self):
        return self._trailing_price

    @property
    def DIFF_PRICE_V(self):
        return self._diff_price_v

    @property
    def DIFF_PRICE_P(self):
        return self._diff_price_p

    # endregion

    # region

    @BASE_QUOTE_BALANCE.setter
    def BASE_QUOTE_BALANCE(self, value):
        self._base_quote_balance = value

    @PURCHASE_PRICE.setter
    def PURCHASE_PRICE(self, value):
        self._purchase_price = value

    @TRAILING_PRICE.setter
    def TRAILING_PRICE(self, value):
        self._trailing_price = value

    @EXPECTED_BALANCE.setter
    def EXPECTED_BALANCE(self, value):
        self._expected_balance = value

    @DIFF_PRICE_V.setter
    def DIFF_PRICE_V(self, value):
        self._diff_price_v = value

    @DIFF_PRICE_P.setter
    def DIFF_PRICE_P(self, value):
        self._diff_price_p = value

    # endregion

    def setup(self):

        if self.SANDBOX:
            self.BASE_BALANCE = self.BASE_BALANCE_DEFAULT
            self.QUOTE_BALANCE = self.QUOTE_BALANCE_DEFAULT

        self.status()

    def execute(self):

        self.fetch_vars()
        self.fetch_data()

        self.calculate_sma()
        self.calculate_rsi()

        self.calculate_sma_signal()
        self.calculate_rsi_signal()

        last = self.data.iloc[-1]

        self.SIGNAL_SMA = last["signal_sma"]
        self.SIGNAL_RSI = last["signal_rsi"]

        if self.can_buy():

            self.execute_buy()

        elif self.can_sell():

            self.execute_sell()

        else:

            self.execute_hold()

        self.update_vars()

        self.status()

        time.sleep(60)

    def can_buy(self):

        if self.POSITION != "BUY":
            return False

        return self.SIGNAL_SMA == "BUY"

    def can_sell(self):

        if self.POSITION != "SELL":
            return False

        if self.TRAILING_ENABLE:
            if self.CURRENT_PRICE < self.TRAILING_PRICE:
                return True

        if self.PROFITING_ENABLE:
            if self.DIFF_PRICE_P > self.PROFITING_THRESHOLD:
                return True

        return self.SIGNAL_SMA == "SELL"

    def execute_buy(self):

        if super().execute_buy():

            self.PURCHASE_PRICE = self.CURRENT_PRICE

            trailing_price = self.PURCHASE_PRICE * (1.0 - self.TRAILING_THRESHOLD / 100.0)

            if trailing_price > self.TRAILING_PRICE:
                self.TRAILING_PRICE = trailing_price

            self.POSITION = "SELL"

    def execute_sell(self):

        if super().execute_sell():

            self.PURCHASE_PRICE = 0.0

            self.POSITION = "BUY"

    def execute_hold(self):

        print()
        print("HOLD")

    def update_vars(self):

        self.BASE_QUOTE_BALANCE = self.BASE_BALANCE * self.CURRENT_PRICE

        self.EXPECTED_BALANCE = self.BASE_BALANCE * self.CURRENT_PRICE + self.QUOTE_BALANCE

        self.DIFF_PRICE_V = self.CURRENT_PRICE - self.PURCHASE_PRICE if self.PURCHASE_PRICE != 0.0 else 0.0
        self.DIFF_PRICE_P = self.DIFF_PRICE_V / self.PURCHASE_PRICE * 100.0 if self.PURCHASE_PRICE != 0.0 else 0.0

    def status(self):

        def get_time(timezone_str: str) -> str:
            timezone = ZoneInfo(timezone_str)
            update_time = datetime.now(timezone).strftime("%d/%m/%Y %H:%M:%S")
            return update_time

        update_time = get_time(self.TIMEZONE)

        print()
        print(f"UPDATE TIME        : {update_time}")
        print(f"SYMBOL             : {self.SYMBOL}")
        print(f"INTERVAL           : {self.INTERVAL}")
        print(f"POSITION           : {self.POSITION}")
        print(f"SIGNAL             : {self.SIGNAL_SMA} / {self.SIGNAL_RSI}")
        print(f"BASE_BALANCE       : {self.BASE_BALANCE:.8f}")
        print(f"QUOTE_BALANCE      : {self.QUOTE_BALANCE:.8f}")
        print(f"BASE_QUOTE_BALANCE : {self.BASE_QUOTE_BALANCE:.8f}")
        print(f"EXPECTED_BALANCE   : {self.EXPECTED_BALANCE:.8f}")
        print(f"CURRENT_PRICE      : {self.CURRENT_PRICE:.8f}")
        print(f"PURCHASE_PRICE     : {self.PURCHASE_PRICE:.8f}")
        print(f"DIFF_PRICE_V       : {self.DIFF_PRICE_V:.8f}")
        print(f"DIFF_PRICE_P       : {self.DIFF_PRICE_P:.2f}")
        print(f"TRAILING_PRICE     : {self.TRAILING_PRICE:.8f}")

        data = {
            "update_time": update_time,
            "symbol": self.SYMBOL,
            "interval": self.INTERVAL,
            "position": self.POSITION,
            "signal": f"{self.SIGNAL_SMA} / {self.SIGNAL_RSI}",
            "base_balance": f"{self.BASE_BALANCE:.8f}",
            "quote_balance": f"{self.QUOTE_BALANCE:8f}",
            "base_quote_balance": f"{self.BASE_QUOTE_BALANCE:.8f}",
            "expected_balance": f"{self.EXPECTED_BALANCE:.8f}",
            "current_price": f"{self.CURRENT_PRICE:.8f}",
            "purchase_price": f"{self.PURCHASE_PRICE:.8f}",
            "trailing_price": f"{self.TRAILING_PRICE:.8f}",
            "diff_price_v": f"{self.DIFF_PRICE_V:.8f}",
            "diff_price_p": f"{self.DIFF_PRICE_P:.2f}",
        }

        self.memcache.set_many(values=data, expire=120)
