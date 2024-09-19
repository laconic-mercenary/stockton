import logging

class Broker:
    def __init__(self):
        pass

    def place_market_order(self, ticker, take_profit=0.0, stop_loss=0.0):
        logging.info(f"Placing market order for {ticker} - take_profit={take_profit}, stop_loss={stop_loss}")

    def sell_all_orders_for(self, ticker):
        logging.info(f"Selling all orders for {ticker}")