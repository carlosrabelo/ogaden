#!/usr/bin/env ./.venv/bin/python

from config import Config
from broker import Broker
from trader import Trader

if __name__ == "__main__":

    config = Config()

    broker = Broker(config)

    trader = Trader(broker)

    trader.initialize()
    trader.execute_cycle()
    trader.update_state()
    trader.display_status()
