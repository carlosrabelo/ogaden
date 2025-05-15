import time

from datetime import datetime
from zoneinfo import ZoneInfo

from pymemcache.client import base

from broker import Broker


class Trader(Broker):

    def __init__(self):

        super().__init__()

        self.memcache = base.Client(server=(self.MEMCACHED_HOST, self.MEMCACHED_PORT), key_prefix="ogaden")

        self._purchase_price = 0.0

        self._difference_price_v = 0.0
        self._difference_price_p = 0.0

        self._base_quote_balance = 0.0
        self._expected_balance = 0.0
        self._trailing_balance = 0.0

        self.POSITION = "BUY"

        self.RSI = 0.0

        self.SIGNAL_EMA = "HOLD"
        self.SIGNAL_RSI = "HOLD"
        self.SIGNAL_EMA_TREND = "HOLD"

    # region

    @property
    def PURCHASE_PRICE(self):
        return self._purchase_price

    @property
    def DIFFERENCE_PRICE_V(self):
        return self._difference_price_v

    @property
    def DIFFERENCE_PRICE_P(self):
        return self._difference_price_p

    @property
    def BASE_QUOTE_BALANCE(self):
        return self._base_quote_balance

    @property
    def EXPECTED_BALANCE(self):
        return self._expected_balance

    @property
    def TRAILING_BALANCE(self):
        return self._trailing_balance

    # endregion

    # region

    @PURCHASE_PRICE.setter
    def PURCHASE_PRICE(self, value):
        self._purchase_price = value

    @DIFFERENCE_PRICE_V.setter
    def DIFFERENCE_PRICE_V(self, value):
        self._difference_price_v = value

    @DIFFERENCE_PRICE_P.setter
    def DIFFERENCE_PRICE_P(self, value):
        self._difference_price_p = value

    @BASE_QUOTE_BALANCE.setter
    def BASE_QUOTE_BALANCE(self, value):
        self._base_quote_balance = value

    @EXPECTED_BALANCE.setter
    def EXPECTED_BALANCE(self, value):
        self._expected_balance = value

    @TRAILING_BALANCE.setter
    def TRAILING_BALANCE(self, value):
        self._trailing_balance = value

    # endregion

    def setup(self):

        if self.SANDBOX:
            self.BASE_BALANCE = self.BASE_BALANCE_DEFAULT
            self.QUOTE_BALANCE = self.QUOTE_BALANCE_DEFAULT

        self.status()

    def execute(self):

        self.fetch_vars()

        self.fetch_data()

        self.calculate_rsi()
        self.calculate_rsi_signal()

        self.calculate_ema()
        self.calculate_ema_signal()

        self.calculate_ema_trend()
        self.calculate_ema_signal_trend()

        self.RSI = self.data["rsi"].iloc[-1]

        self.SIGNAL_EMA = self.data["signal_ema"].iloc[-1]
        self.SIGNAL_RSI = self.data["signal_rsi"].iloc[-1]

        self.SIGNAL_EMA_TREND = self.data["signal_ema_trend"].iloc[-1]

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

        return (self.SIGNAL_EMA == "BUY" or self.SIGNAL_RSI == "BUY") and self.SIGNAL_EMA_TREND == "BUY"

    def can_sell(self):

        if self.POSITION != "SELL":
            return False

        if self.PROFIT_ENABLE:
            if self.DIFFERENCE_PRICE_P > self.PROFIT_THRESHOLD:
                return True

        if self.LOSS_ENABLE:
            if self.DIFFERENCE_PRICE_P < self.LOSS_THRESHOLD:
                return True

        if self.TRAILING_ENABLE:
            if self.TRAILING_BALANCE > self.EXPECTED_BALANCE:
                return True

        return (self.SIGNAL_EMA == "SELL" or self.SIGNAL_RSI == "SELL") and self.SIGNAL_EMA_TREND == "SELL"

    def execute_buy(self):

        if super().execute_buy():

            self.PURCHASE_PRICE = self.CURRENT_PRICE

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

        self.EXPECTED_BALANCE = self.QUOTE_BALANCE + self.BASE_QUOTE_BALANCE

        if self.POSITION == "BUY":

            self.TRAILING_BALANCE = 0.0

            self.DIFFERENCE_PRICE_V = 0.0
            self.DIFFERENCE_PRICE_P = 0.0

        if self.POSITION == "SELL":

            trailing_balance = self.EXPECTED_BALANCE * self.TRAILING_THRESHOLD

            if trailing_balance > self.TRAILING_BALANCE:
                self.TRAILING_BALANCE = trailing_balance

            self.DIFFERENCE_PRICE_V = self.CURRENT_PRICE - self.PURCHASE_PRICE
            self.DIFFERENCE_PRICE_P = self.DIFFERENCE_PRICE_V / self.PURCHASE_PRICE * 100.0

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
        print(f"SIGNAL             : {self.SIGNAL_EMA} / {self.SIGNAL_EMA_TREND} / {self.SIGNAL_RSI}")
        print(f"BASE_BALANCE       : {self.BASE_BALANCE:.8f}")
        print(f"QUOTE_BALANCE      : {self.QUOTE_BALANCE:.8f}")
        print(f"BASE_QUOTE_BALANCE : {self.BASE_QUOTE_BALANCE:.8f}")
        print(f"EXPECTED_BALANCE   : {self.EXPECTED_BALANCE:.8f}")
        print(f"TRAILING_BALANCE   : {self.TRAILING_BALANCE:.8f}")
        print(f"CURRENT_PRICE      : {self.CURRENT_PRICE:.8f}")
        print(f"PURCHASE_PRICE     : {self.PURCHASE_PRICE:.8f}")
        print(f"DIFFERENCE_PRICE   : {self.DIFFERENCE_PRICE_V:.8f} / {self.DIFFERENCE_PRICE_P:.4f}")

        data = {
            "update_time": update_time,
            "symbol": self.SYMBOL,
            "interval": self.INTERVAL,
            "position": self.POSITION,
            "signal": f"{self.SIGNAL_EMA} / {self.SIGNAL_EMA_TREND} / {self.SIGNAL_RSI}",
            "base_balance": f"{self.BASE_BALANCE:.8f}",
            "quote_balance": f"{self.QUOTE_BALANCE:8f}",
            "base_quote_balance": f"{self.BASE_QUOTE_BALANCE:.8f}",
            "expected_balance": f"{self.EXPECTED_BALANCE:.8f}",
            "trailing_balance": f"{self.TRAILING_BALANCE:.8f}",
            "current_price": f"{self.CURRENT_PRICE:.8f}",
            "purchase_price": f"{self.PURCHASE_PRICE:.8f}",
            "difference_price": f"{self.DIFFERENCE_PRICE_V:.8f} / {self.DIFFERENCE_PRICE_P:.4f}"
        }

        self.memcache.set_many(values=data, expire=120)
