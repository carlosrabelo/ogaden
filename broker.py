from binance.client import Client

import pandas as pd
import numpy as np

from loader import Loader


class Broker(Loader):

    def __init__(self):

        super().__init__()

        self.binance = Client(self.API_KEY, self.API_SECRET)

        self._base_balance = 0.0
        self._quote_balance = 0.0

        self._min_notional = 0.0
        self._step_size = 0.0
        self._min_quantity = 0.0

        self._current_price = 0.0

        self.data = pd.DataFrame()

    # region

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
    def MIN_NOTIONAL(self):
        return self._min_quantity

    @property
    def STEP_SIZE(self):
        return self._step_size

    @property
    def MIN_QUANTITY(self):
        return self._min_quantity

    # endregion

    # region

    @BASE_BALANCE.setter
    def BASE_BALANCE(self, value):
        self._base_balance = value

    @QUOTE_BALANCE.setter
    def QUOTE_BALANCE(self, value):
        self._quote_balance = value

    @CURRENT_PRICE.setter
    def CURRENT_PRICE(self, value):
        self._current_price = value

    @MIN_NOTIONAL.setter
    def MIN_NOTIONAL(self, value):
        self._min_notional = value

    @STEP_SIZE.setter
    def STEP_SIZE(self, value):
        self._step_size = value

    @MIN_QUANTITY.setter
    def MIN_QUANTITY(self, value):
        self._min_quantity = value

    # endregion

    def fetch_vars(self):

        if not self.SANDBOX:
            self.BASE_BALANCE = self.fetch_balance(self.BASE_ASSET)
            self.QUOTE_BALANCE = self.fetch_balance(self.QUOTE_ASSET)

        self.CURRENT_PRICE = self.fetch_current_price(self.SYMBOL)
        self.MINIMUM_NOTIONAL = self.fetch_minimum_notional(self.SYMBOL)
        self.STEP_SIZE = self.fetch_step_size(self.SYMBOL)
        self.MINIMUM_QUANTITY = self.fetch_minimum_quantity(self.SYMBOL)

    def fetch_balance(self, asset) -> float:

        try:
            account_info = self.binance.get_account()
            return float(next((balance["free"] for balance in account_info["balances"] if balance["asset"] == asset), 0.0))
        except Exception as e:
            print(f"Error getting balance for {asset}: {e}")
            return 0.0

    def fetch_current_price(self, symbol) -> float:

        try:
            ticker = self.binance.get_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        except Exception as e:
            print(f"Error getting current price for {symbol}: {e}")
            return 0.0

    def fetch_minimum_notional(self, symbol) -> float:

        try:
            symbol_info = self.binance.get_symbol_info(symbol=symbol)
            return float(next(f["minNotional"] for f in symbol_info["filters"] if f["filterType"] == "NOTIONAL"))
        except Exception as e:
            print(f"Error getting minimum notional for {symbol}: {e}")
            return float("0.0")

    def fetch_step_size(self, symbol) -> float:

        try:
            symbol_info = self.binance.get_symbol_info(symbol)
            return float(next(f["stepSize"] for f in symbol_info["filters"] if f["filterType"] == "LOT_SIZE"))
        except Exception as e:
            print(f"Error getting step size for {symbol}: {e}")
            return 0.0

    def fetch_minimum_quantity(self, symbol) -> float:

        try:
            symbol_info = self.binance.get_symbol_info(symbol)
            return float(next(f["minQty"] for f in symbol_info["filters"] if f["filterType"] == "LOT_SIZE"))
        except Exception as e:
            print(f"Error getting minimum quantity for {symbol}: {e}")
            return 0.0

    def fetch_data(self):

        try:

            dict = self.binance.get_klines(symbol=self.SYMBOL, interval=self.INTERVAL, limit=self.LIMIT)

            if not dict:
                raise ValueError("No klines data found for the specified SYMBOL and interval.")

            df = pd.DataFrame(
                dict,
                columns=[
                    "open_time",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "close_time",
                    "quote_asset_volume",
                    "number_of_trades",
                    "taker_buy_base_asset_volume",
                    "taker_buy_quote_asset_volume",
                    "ignore",
                ],
            )

            df = df[["close_time", "close"]]

            df["close"] = df["close"].astype(float)

            df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True).dt.tz_convert(self.TIMEZONE).dt.floor("s").dt.tz_localize(None)

            self.data = df

        except Exception as e:

            self.data = pd.DataFrame()

            print(f"Error fetching candle data: {e}")

    def calculate_sma(self):

        self.data["fast_sma"] = self.data["close"].rolling(window=self.FAST_SMA).mean()
        self.data["slow_sma"] = self.data["close"].rolling(window=self.SLOW_SMA).mean()

    def calculate_ema(self):

        self.data["fast_ema"] = self.data["close"].ewm(span=self.FAST_EMA, adjust=False).mean()
        self.data["slow_ema"] = self.data["close"].ewm(span=self.SLOW_EMA, adjust=False).mean()

    def calculate_sma_signal(self):

        def get_sma_signal(row):

            if pd.isna(row["fast_sma"]) or pd.isna(row["slow_sma"]):
                return "HOLD"

            if row["fast_sma"] > row["slow_sma"]:
                return "BUY"
            elif row["fast_sma"] < row["slow_sma"]:
                return "SELL"
            else:
                return "HOLD"

        self.data["signal_sma"] = self.data.apply(get_sma_signal, axis=1)

    def calculate_ema_signal(self):

        def get_ema_signal(row):

            if pd.isna(row["fast_ema"]) or pd.isna(row["slow_ema"]):
                return "HOLD"

            if row["fast_ema"] > row["slow_ema"]:
                return "BUY"
            elif row["fast_ema"] < row["slow_ema"]:
                return "SELL"
            else:
                return "HOLD"

        self.data["signal_ema"] = self.data.apply(get_ema_signal, axis=1)

    def calculate_rsi(self):

        delta = self.data["close"].diff()

        gain = delta.where(delta > 0.0, 0.0)
        loss = -delta.where(delta < 0.0, 0.0)

        avg_gain = gain.ewm(span=self.RSI_PERIOD, adjust=False).mean()
        avg_loss = loss.ewm(span=self.RSI_PERIOD, adjust=False).mean()

        rs = np.where(avg_loss == 0, 0, avg_gain / avg_loss)

        rsi = 100.0 - (100.0 / (1.0 + rs))

        self.data["rsi"] = rsi

    def calculate_rsi_signal(self):

        def get_signal(row) -> str:

            if pd.isna(row["rsi"]):
                return "HOLD"

            rsi = row["rsi"]

            if rsi == 0.0:
                return "HOLD"

            rsi_buy_threshold = self.RSI_BUY_THRESHOLD
            rsi_sell_threshold = self.RSI_SELL_THRESHOLD

            if rsi < rsi_buy_threshold:
                return "BUY"
            elif rsi > rsi_sell_threshold:
                return "SELL"
            else:
                return "HOLD"

        self.data["signal_rsi"] = self.data.apply(get_signal, axis=1)

    def execute_buy(self) -> bool:

        available_quote = self.QUOTE_BALANCE

        min_notional = self.MIN_NOTIONAL

        if available_quote < min_notional:
            print(f"Insufficient quote balance: {available_quote} is below the minimum notional value of {min_notional}.")
            return False

        current_price = self.CURRENT_PRICE

        calculated_quantity = available_quote / current_price

        step_size = self.STEP_SIZE

        calculated_quantity = (calculated_quantity // step_size) * step_size

        minimum_quantity = self.MINIMUM_QUANTITY

        if calculated_quantity < minimum_quantity:
            print(f"Calculated quantity ({calculated_quantity}) is below the minimum allowed ({minimum_quantity}).")
            return False

        if self.SANDBOX:
            total_cost = calculated_quantity * current_price
            fee = total_cost * 0.001

            self.BASE_BALANCE += calculated_quantity
            self.QUOTE_BALANCE -= total_cost - fee

        else:
            self.binance.order_market_buy(symbol=self.SYMBOL, quantity=calculated_quantity)

        print()
        print(f"Executed purchase: {calculated_quantity:.6f} {self.BASE_ASSET} at {current_price}")

        return True

    def execute_sell(self) -> bool:

        available_base = self.BASE_BALANCE

        minimum_quantity = self.MINIMUM_QUANTITY

        if available_base < minimum_quantity:
            print(f"Insufficient base balance: {available_base} is below the minimum allowed quantity of {minimum_quantity}.")
            return False

        step_size = self.STEP_SIZE

        calculated_quantity = (available_base // step_size) * step_size

        if calculated_quantity < minimum_quantity:
            print(f"Calculated quantity ({calculated_quantity}) is below the minimum allowed ({minimum_quantity}).")
            return False

        current_price = self.CURRENT_PRICE

        if self.SANDBOX:
            total_sale_value = calculated_quantity * current_price
            fee = total_sale_value * 0.001

            self.BASE_BALANCE -= calculated_quantity
            self.QUOTE_BALANCE += total_sale_value - fee

        else:
            self.binance.order_market_sell(symbol=self.SYMBOL, quantity=calculated_quantity)

        print()
        print(f"Executed sell: {calculated_quantity:.6f} {self.BASE_ASSET} at {current_price}")

        return True
