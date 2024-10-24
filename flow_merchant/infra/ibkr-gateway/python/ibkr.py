import ib_insync

class Assistant:
    def __init__(self, ib_api: ib_insync.IB):
        assert ib_api is not None, "ib_api is required"
        self.__ib_api = ib_api

    def place_stock_bracket_order(
            self, 
            ticker: str, 
            currency: str, 
            limit_price: float, 
            take_profit: float, 
            stop_loss: float, 
            quantity: float,
            onOrderStatus: callable = None,
            simulate=False
            ):
        contract = ib_insync.Stock(ticker, "SMART", currency)
        bracket = self.__ib_api.bracketOrder(
            "BUY",
            quantity,
            limitPrice=limit_price,
            takeProfitPrice=take_profit,
            stopLossPrice=stop_loss
        )
        for order in bracket:
            order.whatIf = simulate
            trade = self.__ib_api.placeOrder(contract, order)
            trade.statusEvent += onOrderStatus
        
    def get_open_orders(self) -> list:
        return self.__ib_api.openOrders()

    def get_unrealized_pnl(self) -> float:
        return float(self.__search_account_values("UnrealizedPnL"))
    
    def get_available_funds(self) -> float:
        return float(self.__search_account_values("AvailableFunds"))
    
    def get_buying_power(self) -> float:
        return float(self.__search_account_values("BuyingPower"))
    
    def get_equity_with_loan(self) -> float:
        return float(self.__search_account_values("EquityWithLoanValue"))
    
    def positions(self) -> list:
        return self.__ib_api.positions()    

    def __search_account_values(self, key: str) -> any:
        key_index = 1
        value_index = 2
        for account_value in self.__ib_api.accountValues():
            if account_value[key_index] == key:
                return account_value[value_index]
        raise ValueError(f"Account value not found: {key}")