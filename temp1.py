
   def execute_buy(self):

        if super().execute_buy():
            self.PURCHASE_PRICE = self.CURRENT_PRICE

    def execute_sell(self):

        if super().execute_sell():
            self.PURCHASE_PRICE = 0.0

    def setup(self):

        self.BASE_BALANCE = 0.0
        self.QUOTE_BALANCE = 10.0

    def update(self):

        self.CURRENT_PRICE = self.fetch_current_price(self.SYMBOL)

        self.fetch_data()

        self.calculate_sma()
        self.calculate_rsi()

        self.rsi_signal()

        last = self._data.iloc[-1]

        self.SIGNAL = last["signal_rsi"]

    def execute(self):

        if self.can_buy():
            pass

        elif self.can_sell():
            pass

        else:
            self.hold()

        self.status()

        if self.execute_buy():
            self.PURCHASE_PRICE = self.CURRENT_PRICE

        self.status()

        if self.execute_sell():
            self.PURCHASE_PRICE = 0.0

        self.status()

    def status(self):

        print()
        print(f"SANDBOX            : {self.SANDBOX}")
        print(f"BASE_ASSET         : {self.BASE_ASSET}")
        print(f"QUOTE_ASSET        : {self.QUOTE_ASSET}")
        print(f"FAST_SMA           : {self.FAST_SMA}")
        print(f"SLOW_SMA           : {self.SLOW_SMA}")
        print(f"FAST_EMA           : {self.FAST_EMA}")
        print(f"SLOW_EMA           : {self.SLOW_EMA}")
        print(f"BASE_BALANCE       : {self.BASE_BALANCE:.8f}")
        print(f"QUOTE_BALANCE      : {self.QUOTE_BALANCE:.8f}")
        print(f"BASE_QUOTE_BALANCE : {self.BASE_QUOTE_BALANCE:.8f}")
        print(f"CURRENT_PRICE      : {self.CURRENT_PRICE:.8f}")
        print(f"PURCHASE_PRICE     : {self.PURCHASE_PRICE:.8f}")
        print(f"SIGNAL             : {self.SIGNAL}")
