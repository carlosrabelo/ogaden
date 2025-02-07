#!/usr/bin/env ./.venv/bin/python

from config import Config
from broker import Broker
from trader import Trader

if __name__ == "__main__":

    config = Config()

    broker = Broker(config)

    trader = Trader(broker)
