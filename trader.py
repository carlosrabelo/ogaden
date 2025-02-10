from broker import Broker


class Trader(Broker):

    def __init__(self):

        super().__init__()

        self._base_quote_balance = 0.0

        self._purchase_price = 0.0

        self.POSITION = "hold"

        self.SIGNAL = None

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

    def execute(self):

        if self.SANDBOX:
            self.BASE_BALANCE = 0.0
            self.QUOTE_BALANCE = 10.0

        print(f"BASE_BALANCE       : {self.BASE_BALANCE:.8f}")
        print(f"QUOTE_BALANCE      : {self.QUOTE_BALANCE:.8f}")
        print(f"BASE_QUOTE_BALANCE : {self.BASE_QUOTE_BALANCE:.8f}")

        self._current_price = self.fetch_current_price(self.SYMBOL)

        print(self.execute_buy())

        self._current_price = self.fetch_current_price(self.SYMBOL)

        print(f"BASE_BALANCE       : {self.BASE_BALANCE:.8f}")
        print(f"QUOTE_BALANCE      : {self.QUOTE_BALANCE:.8f}")
        print(f"BASE_QUOTE_BALANCE : {self.BASE_QUOTE_BALANCE:.8f}")

        self._current_price = self.fetch_current_price(self.SYMBOL) * 1.01

        print(self.execute_sell())

        print(f"BASE_BALANCE       : {self.BASE_BALANCE:.8f}")
        print(f"QUOTE_BALANCE      : {self.QUOTE_BALANCE:.8f}")
        print(f"BASE_QUOTE_BALANCE : {self.BASE_QUOTE_BALANCE:.8f}")
