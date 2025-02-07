from broker import Broker


class Trader:

    def __init__(self, broker: Broker):

        self._base_balance = 0.0
        self._quote_balance = 0.0

        self._current_price = 0.0
        self._purchase_price = 0.0

        self._base_quote_balance = 0.0

        self.broker = broker
        self.config = broker.config

    @property
    def BASE_BALANCE(self):
        return self._base_balance

    @property
    def QUOTE_BALANCE(self):
        return self._quote_balance

    @property
    def CURRENT_PRICE(self):
        return self._current_price

    @property
    def PURCHASE_PRICE(self):
        return self._purchase_price

    @property
    def BASE_QUOTE_BALANCE(self):
        self._base_quote_balance = self._base_balance * self._current_price
        return self._base_quote_balance

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

    def setup(self):

        self.broker.BASE_BALANCE = 40
        self.broker.QUOTE_BALANCE = 1.0

    def update(self):

        self.BASE_BALANCE = self.broker.BASE_BALANCE
        self.QUOTE_BALANCE = self.broker.QUOTE_BALANCE
        self.CURRENT_PRICE = self.broker.CURRENT_PRICE

    def display(self):

        print(f"BASE_ASSET         : {self.config.BASE_ASSET}")
        print(f"QUOTE_ASSET        : {self.config.QUOTE_ASSET}")
        print(f"BASE_BALANCE       : {self.BASE_BALANCE}")
        print(f"QUOTE_BALANCE      : {self.QUOTE_BALANCE}")
        print(f"BASE_QUOTE_BALANCE : {self.BASE_QUOTE_BALANCE}")
        print(f"CURRENT_PRICE      : {self.broker.CURRENT_PRICE}")
        print(f"PURCHASE_PRICE     : {self.PURCHASE_PRICE}")
