#!/usr/bin/env ./.venv/bin/python

from trader import Trader

if __name__ == "__main__":

    trader = Trader()

    trader.setup()

    while True:
        trader.execute()
