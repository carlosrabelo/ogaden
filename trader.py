import time

from broker import Broker


class Trader:

    def __init__(self, broker: Broker):

        self._base_balance = 0.0
        self._quote_balance = 0.0

        self._base_quote_balance = 0.0

        self._expected_balance = 0.0

        self._current_price = 0.0
        self._purchase_price = 0.0
        self._expected_price = 0.0

        self._signal = "NONE"

        self.broker = broker
        self.config = broker.config

    @property
    def BASE_BALANCE(self):
        return self._base_balance

    @property
    def QUOTE_BALANCE(self):
        return self._quote_balance

    @property
    def BASE_QUOTE_BALANCE(self):
        self._base_quote_balance = self._base_balance * self._current_price
        return self._base_quote_balance

    @property
    def CURRENT_PRICE(self):
        return self._current_price

    @property
    def PURCHASE_PRICE(self):
        return self._purchase_price

    @property
    def EXPECTED_BALANCE(self):
        self._expected_balance = self._base_balance * self._current_price + self._quote_balance
        return self._expected_balance

    @BASE_BALANCE.setter
    def BASE_BALANCE(self, value):
        self._base_balance = value
        self._base_quote_balance = self._base_balance * self._current_price

    @QUOTE_BALANCE.setter
    def QUOTE_BALANCE(self, value):
        self._quote_balance = value

    @CURRENT_PRICE.setter
    def CURRENT_PRICE(self, value):
        self._current_price = value
        self._base_quote_balance = self._base_balance * self._current_price

    @PURCHASE_PRICE.setter
    def PURCHASE_PRICE(self, value):
        self._purchase_price = value

    def initialize(self):

        self.broker.BASE_BALANCE = 0.0
        self.broker.QUOTE_BALANCE = 20.0

    def update_state(self):

        self.BASE_BALANCE = self.broker.BASE_BALANCE
        self.QUOTE_BALANCE = self.broker.QUOTE_BALANCE
        self.CURRENT_PRICE = self.broker.CURRENT_PRICE

    def display_status(self):

        print()
        print(f"BASE_ASSET         : {self.config.BASE_ASSET}")
        print(f"QUOTE_ASSET        : {self.config.QUOTE_ASSET}")
        print(f"BASE_BALANCE       : {self.BASE_BALANCE:.6f}")
        print(f"QUOTE_BALANCE      : {self.QUOTE_BALANCE:.6f}")
        print(f"BASE_QUOTE_BALANCE : {self.BASE_QUOTE_BALANCE:.6f}")
        print(f"EXPECTED_BALANCE   : {self.EXPECTED_BALANCE:.6f}")
        print(f"CURRENT_PRICE      : {self.broker.CURRENT_PRICE:.6f}")
        print(f"PURCHASE_PRICE     : {self.PURCHASE_PRICE:.6f}")
        print(f"SIGNAL             : {self._signal}")

    def execute_cycle(self):

        self.broker.fetch_market_data()

        self.broker.calculate_rsi()
        self.broker.rsi_signal()

        last = self.broker._market_data.iloc[-1]

        self._signal = last["signal_rsi"]

    def wait(self, seconds: int = 60):

        time.sleep(seconds)

    def execute_buy(self):

        if self.broker.execute_buy():
            self.PURCHASE_PRICE = self.broker.CURRENT_PRICE

    def execute_sell(self):

        if self.broker.execute_sell():
            self.PURCHASE_PRICE = self.broker.CURRENT_PRICE
