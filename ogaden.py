#!/usr/bin/env ./.venv/bin/python

from trader import Trader

if __name__ == "__main__":

    trader = Trader()

    trader.fetch_data()

    trader.calculate_sma()
    trader.calculate_ema()
    trader.calculate_rsi()

    print(trader.data.head(15))
    print(trader.data.tail(15))
