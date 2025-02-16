#!/usr/bin/env ./.venv/bin/python

from trader import Trader

if __name__ == "__main__":

    trader = Trader()

    trader.fetch_data()

    trader.calculate_sma()

    trader.calculate_sma_prev()
    trader.calculate_sma_signal()

    # trader.calculate_ema()

    # trader.calculate_rsi()
    # trader.calculate_rsi_signal()

    print(trader.data)
