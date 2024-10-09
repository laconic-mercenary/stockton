import json
import logging
import os
import uuid
import time

import azure.functions as func
from azure.data.tables import TableServiceClient

app = func.FunctionApp()

##
# Merchant API
##

@app.route(route="merchant_api", 
            auth_level=func.AuthLevel.FUNCTION)
def merchant_api(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    if req.method != "GET":
        return func.HttpResponse(f"Only GET requests are supported", status_code=405)
    with TableServiceClient.from_connection_string(os.environ['storageAccountConnectionString']) as table_service:
        table_client = table_service.get_table_client(table_name="flowmerchant")
        entities = table_client.list_entities()
        rows = [dict(entity) for entity in entities]
        return func.HttpResponse(json.dumps(rows), mimetype="application/json")

##
# Merchant Consumer
##

@app.function_name(name="merchant_consumer")
@app.queue_trigger(arg_name="msg", 
                    queue_name="merchantsignals",
                    connection="storageAccountConnectionString")
def merchant_consumer(msg: func.QueueMessage) -> None:
    message_body = json.loads(msg.get_body().decode('utf-8'))
    signal = MerchantSignal(message_body)
    
    logging.info(f"received merchant signal, id is {signal.id()}")

    with TableServiceClient.from_connection_string(os.environ['storageAccountConnectionString']) as table_service:
        try:
            merchant = Merchant(table_service)
            merchant.handle_market_signal(signal)
        except Exception as e:
            logging.error(f"error handling market signal {signal.id()}, {e}")
            return
        
"""
UTILS
"""
def unix_timestamp() -> int:
    return int(time.time())


"""
BROKER
"""

class Broker:
    def __init__(self):
        pass

    def place_market_order(self, ticker, take_profit=0.0, stop_loss=0.0):
        logging.info(f"Placing market order for {ticker} - take_profit={take_profit}, stop_loss={stop_loss}")

    def sell_all_orders_for(self, ticker):
        logging.info(f"Selling all orders for {ticker}")

"""
MERCHANT 
"""

def M_CFG_HIGH_INTERVAL():
    return "MERCHANT_HIGH_INTERVAL"

def M_CFG_LOW_INTERVAL():
    return "MERCHANT_LOW_INTERVAL"

def S_ACTION_BUY():
    return "buy"

def S_ACTION_SELL():
    return "sell"

def M_STATE_SHOPPING():
    return "shopping"

def M_STATE_BUYING():
    return "buying"

def M_STATE_SELLING():
    return "selling"

def M_STATE_RESTING():
    return "resting"

def M_STATE_KEY_PARTITIONKEY():
    return "PartitionKey"

def M_STATE_KEY_ROWKEY():
    return "RowKey"

def M_STATE_KEY_STATUS():
    return "status"

def M_STATE_KEY_POSITION_DATA():
    return "position_data"

def M_STATE_KEY_LAST_ACTION_TIME():
    return "merchant_lastaction_time"

def M_STATE_KEY_TICKER():
    return "ticker"

def M_STATE_KEY_INTERVAL():
    return "interval"

def M_STATE_REST_INTERVAL():
    return "rest_interval"

def M_STATE_KEY_HIGH_INTERVAL():
    return "high_interval"

def M_STATE_KEY_LOW_INTERVAL():
    return "low_interval"

def M_STATE_KEY_ID():
    return "id"

def M_STATE_KEY_VERSION():
    return "version"

def M_STATE_KEY_ACTION():
    return "action"

def M_STATE_KEY_TICKER():
    return "ticker"

def M_STATE_KEY_CLOSE():
    return "close"

def M_STATE_KEY_SUGGESTED_STOPLOSS():
    return "suggested_stoploss"

def M_STATE_KEY_HIGH():
    return "high"

def M_STATE_KEY_LOW():
    return "low"

def M_STATE_KEY_TAKEPROFIT_PERCENT():
    return "takeprofit_percent"

def M_BIAS_BULLISH():
    return "bullish"

def M_BIAS_BEARISH():
    return "bearish"

class MerchantSignal:
    def __init__(self, msg_body):
        if not msg_body:
            raise ValueError("Message body cannot be null")
        self.msg = msg_body
        self.notes = self._parse_notes()
        self.TABLE_NAME = "flowmerchant"
        self._id = str(uuid.uuid4())

    def action(self):
        return self.get('action')
    
    def ticker(self):
        return self.get('ticker')
    
    def close(self):
        return self.get('close')
        
    def interval(self):
        return self.notes.get('interval')
    
    def high_interval(self):
        return self.notes.get('high_interval')
    
    def low_interval(self):
        return self.notes.get('low_interval')

    def suggested_stoploss(self):
        return self.notes.get('suggested_stoploss')
    
    def high(self):
        return self.notes.get('high')
    
    def low(self):
        return self.notes.get('low')
    
    def takeprofit_percent(self):
        return self.notes.get('takeprofit_percent')
    
    def version(self):
        return self.notes.get('version')

    def id(self):
        return self._id

    def _parse_notes(self):
        notes = self.get('notes')
        parsed_notes = {}
        if notes:
            pairs = notes.split(';')
            for pair in pairs:
                if '=' in pair:
                    key, value = pair.split('=')
                    key = key.strip()
                    value = value.strip()
                    if key in ["version", "suggested_stoploss", "high",  "low", "takeprofit_percent"]:
                        parsed_notes[key] = float(value)
                    else:
                        parsed_notes[key] = value
        return parsed_notes

    def __str__(self) -> str:
        return json.dumps(self.msg)

    def info(self) -> str:
        return str(self)

    def get(self, key: str) -> any:
        if key not in self.msg:
            raise KeyError(f"Key '{key}' not found in message body")
        return self.msg[key]
    
##
# Merchant

class Merchant:
    def __init__(self, table_service: TableServiceClient, broker: Broker) -> None:
        if table_service is None:
            raise ValueError("TableService cannot be null")
        if broker is None:
            raise ValueError("Broker cannot be null")
        self.state = None
        self.table_service = table_service
        self.broker = broker
        self.TABLE_NAME = "flowmerchant"
        table_service.create_table_if_not_exists(table_name=self.TABLE_NAME)

    def handle_market_signal(self, signal: MerchantSignal) -> None:
        logging.debug(f"handle_market_signal() - {signal.id()}")
        logging.info(f"received signal - id={signal.id()} - {signal.info()}")
        try:
            self.load_config_from_signal(signal)
            self.load_config_from_env() # env should override signal configs
            self.load_state_from_storage()
            if self.status() == M_STATE_SHOPPING():
                self._handle_signal_when_shopping(signal)
            elif self.status() == M_STATE_BUYING():
                self._handle_signal_when_buying(signal)
            elif self.status() == M_STATE_SELLING():
                self._handle_signal_when_selling(signal)
            elif self.status() == M_STATE_RESTING():
                self._handle_signal_when_resting(signal)
            else:
                raise ValueError(f"Unknown state {self.status()}")
        finally:
            logging.info(f"finished handling signal - id={signal.id()}")
    
    def load_state_from_storage(self) -> None:
        self.log_debug(f"load_state_from_storage()")
        query_filter = f"{M_STATE_KEY_PARTITIONKEY()} eq '{self.merchant_id()}'"
        rows = self.table_service.query_entities(query_filter)
        if len(rows) > 1:
            raise ValueError(f"Multiple open merchants found for {self.merchant_id()}")
        else:
            if len(rows) == 1:
                logging.info(f"found existing merchant - id={self.merchant_id()}")
                row = rows[0]
                current_state = row[M_STATE_KEY_STATUS()]
                if not current_state in [M_STATE_SHOPPING(), M_STATE_BUYING(), M_STATE_SELLING(), M_STATE_RESTING()]:
                    raise ValueError(f"Unknown state found in storage {current_state}")
                self.state[M_STATE_KEY_STATUS()] = current_state
            else:
                logging.info(f"no open merchants found for {self.merchant_id()}, creating new...")
                self.state[M_STATE_KEY_STATUS()] = M_STATE_SHOPPING()
                self.table_service.insert_entity(table_name=self.TABLE_NAME, entity=self.state)

    def load_config_from_env(self) -> None:
        """
        currently no properties that need to be loaded from env. 
        env loaded config would be global to all merchant instances.
        so preferrable to config from the signal, unless there are security implications
        """
        logging.debug(f"load_config_from_env()")

    def load_config_from_signal(self, signal: MerchantSignal) -> None:
        logging.debug(f"load_config_from_signal()")
        if self.state is None:
            self.state = {}
        self.state[M_STATE_KEY_ID()] = signal.id()
        self.state[M_STATE_KEY_VERSION()] = signal.version()
        self.state[M_STATE_KEY_ACTION()] = signal.action()
        self.state[M_STATE_KEY_TICKER()] = signal.ticker()
        self.state[M_STATE_KEY_CLOSE()] = signal.close()
        self.state[M_STATE_KEY_SUGGESTED_STOPLOSS()] = signal.suggested_stoploss()
        self.state[M_STATE_KEY_HIGH()] = signal.high()
        self.state[M_STATE_KEY_LOW()] = signal.low()
        self.state[M_STATE_KEY_TAKEPROFIT_PERCENT()] = signal.takeprofit_percent()
        ## self.state[M_STATE_KEY_STATE()] = M_STATE_SHOPPING()
        self.state[M_STATE_KEY_HIGH_INTERVAL()] = signal.high_interval()
        self.state[M_STATE_KEY_LOW_INTERVAL()] = signal.low_interval()
        
    def _handle_signal_when_shopping(self, signal: MerchantSignal) -> None:
        logging.debug(f"_handle_signal_when_shopping()")
        if signal.interval() == self.high_interval():
            if signal.action() == S_ACTION_BUY():
                self._start_buying()
            
    def _handle_signal_when_buying(self, signal: MerchantSignal) -> None:
        self.log_debug(f"_handle_signal_when_buying()")
        if signal.interval() == self.low_interval():
            if signal.action() == S_ACTION_BUY():
                ## TODO
                take_profit = signal.close() + (signal.close() * signal.takeprofit_percent())
                self.broker.place_market_order(signal.ticker(), take_profit, signal.suggested_stoploss())
                self._start_selling()
        elif signal.interval() == self.high_interval():
            if signal.action() == S_ACTION_SELL():
                self._start_shopping()
            
    def _handle_signal_when_selling(self, signal: MerchantSignal) -> None:
        self.log_debug(f"_handle_signal_when_selling()")
        if signal.interval() == self.low_interval():
            if signal.action() == S_ACTION_SELL():
                ## do nothing - allow take profit and stop loss to trigger
                self._start_resting()
        elif signal.interval() == self.high_interval():
            if signal.action() == S_ACTION_SELL():
                self.broker.sell_all_orders_for(signal.ticker())
                self._start_shopping()

    def _handle_signal_when_resting(self) -> None:
        self.log_debug(f"_handle_signal_when_resting()")
        if (self.last_action_time() + self.rest_interval()) < unix_timestamp():
            self._start_shopping()
        else:
            time_left_in_seconds = unix_timestamp() - (self.last_action_time() + self.rest_interval_ms())
            time_left_in_seconds = time_left_in_seconds / 1000
            self.log_info(f"Resting for another {time_left_in_seconds} seconds")

    def _start_buying(self) -> None:
        self.log_debug(f"_start_buying()")
        self.state[M_STATE_KEY_STATUS()] = M_STATE_BUYING()
        self.state[M_STATE_KEY_LAST_ACTION_TIME()] = unix_timestamp()
        self._sync_with_storage()

    def _start_shopping(self) -> None:
        self.log_debug(f"_start_shopping()")
        self.state[M_STATE_KEY_STATUS()] = M_STATE_SHOPPING()
        self.state[M_STATE_KEY_LAST_ACTION_TIME()] = unix_timestamp()
        self._sync_with_storage()

    def _start_selling(self) -> None:
        self.log_debug(f"_start_selling()")
        self.state[M_STATE_KEY_STATUS()] = M_STATE_SELLING()
        self.state[M_STATE_KEY_LAST_ACTION_TIME()] = unix_timestamp()
        self._sync_with_storage()

    def _start_resting(self) -> None:
        self.log_debug(f"_start_resting()")
        self.state[M_STATE_KEY_STATUS()] = M_STATE_RESTING()
        self.state[M_STATE_KEY_LAST_ACTION_TIME()] = unix_timestamp()
        self._sync_with_storage()

    def _sync_with_storage(self) -> None:
        self.log_debug(f"_sync_with_storage()")
        self.table_service.update_entity(entity=self.state)

    def _log_preamble(self) -> str:
        return f"[{self.merchant_id()}, {self.state}, +{self.high_interval()}, -{self.low_interval()}]"

    def log_info(self, message) -> None:
        logging.info(f"{self._log_preamble()} >> {message}")

    def log_debug(self, message) -> None:
        logging.debug(f"{self._log_preamble()} >> {message}")

    ## properties
    def merchant_id(self) -> str:
        ## this should come from tradingview
        ticker = self.state.get(M_STATE_KEY_TICKER())
        interval = self.state.get(M_STATE_KEY_LOW_INTERVAL())
        if ticker is None or interval is None:
            raise ValueError("ticker and/or interval not set")
        return f"{ticker}-{interval}"

    def status(self) -> str:
        return self.state.get(M_STATE_KEY_STATUS())
    
    def high_interval(self) -> str:
        ## this should come from merchant config
        return self.state.get(M_STATE_KEY_HIGH_INTERVAL())
    
    def low_interval(self) -> str:
        ## this should come from merchant config
        return self.state.get(M_STATE_KEY_LOW_INTERVAL())
        
    def last_action_time(self) -> int:
        ## this should come from storage
        return int(self.state.get(M_STATE_KEY_LAST_ACTION_TIME()))
    
    def rest_interval_ms(self) -> int:
        ## this should come from merchant config
        return int(self.state.get(M_STATE_REST_INTERVAL()))
    

import unittest
from unittest.mock import Mock, patch

class TestFlowMerchant(unittest.TestCase):
    def setUp(self):
        pass

    def create_state(self, id, version, action, ticker, close, suggested_stoploss, high, low, takeprofit_percent, status, high_interval, low_interval):
        return {
            M_STATE_KEY_ID(): id,
            M_STATE_KEY_VERSION(): version,
            M_STATE_KEY_ACTION(): action,
            M_STATE_KEY_TICKER(): ticker,
            M_STATE_KEY_CLOSE(): close,
            M_STATE_KEY_SUGGESTED_STOPLOSS(): suggested_stoploss,
            M_STATE_KEY_HIGH(): high,
            M_STATE_KEY_LOW(): low,
            M_STATE_KEY_TAKEPROFIT_PERCENT(): takeprofit_percent,
            M_STATE_KEY_STATUS(): status,
            M_STATE_KEY_HIGH_INTERVAL(): high_interval,
            M_STATE_KEY_LOW_INTERVAL(): low_interval
        }

    def test_merchant_e2e(self):
        table_client_mock = Mock()        
        table_client_mock.query_entities.return_value = [ ]
        broker_mock = Mock()
        
        # Optionally, you can verify it was called with specific arguments
        # table_client_mock.query_entities.assert_called_with(some_arg1, some_arg2)

        # If you want to check how many times it was called
        # self.assertEqual(table_client_mock.query_entities.call_count, 1)
        signal_data = """
        {
            "action" : "buy",
            "ticker" : "AAPL",
            "key" : "STOCKTON_KEY",
            "notes" : "ver=20240922;high=105.0;low=95.0;exchange=NASDAQ;open=98.0;interval=1h;high_interval=1h;low_interval=1m;suggested_stoploss=0.05;takeprofit_percent=0.05;rest_interval=3000",
            "close" : 103.0,
            "contracts" : 1
        }
        """
        first_signal = MerchantSignal(json.loads(signal_data))
        flow_merchant = Merchant(table_client_mock, broker=broker_mock)
        flow_merchant.handle_market_signal(first_signal)

        table_client_mock.create_table_if_not_exists.assert_called()
        table_client_mock.query_entities.assert_called()

        assert flow_merchant.status() == M_STATE_BUYING()
        assert flow_merchant.last_action_time() > 0
        assert flow_merchant.high_interval() == "1h"
        assert flow_merchant.low_interval() == "1m"
        assert flow_merchant.merchant_id() == "AAPL-1m"

        second_signal_data = """
        {
            "action" : "buy",
            "ticker" : "AAPL",
            "key" : "STOCKTON_KEY",
            "notes" : "ver=20240922;high=105.0;low=95.0;exchange=NASDAQ;open=98.0;interval=1m;high_interval=1h;low_interval=1m;suggested_stoploss=0.05;takeprofit_percent=0.05;rest_interval=3000",
            "close" : 103.0,
            "contracts" : 1
        }
        """
        
        table_client_mock.query_entities.return_value = [
            {
                'PartitionKey': 'AAPL-1m', 
                'RowKey': unix_timestamp(), 
                'position_data': '{}', 
                'status': 'buying', 
                'merchant_lastaction_time': 1726990626, 
                'ticker': 'AAPL', 
                'high_interval': '1h', 
                'low_interval': '1m'
            }
        ]
        print(flow_merchant.state)
        second_signal = MerchantSignal(json.loads(second_signal_data))
        flow_merchant.handle_market_signal(second_signal)
        print(flow_merchant.state)

        assert flow_merchant.status() == M_STATE_SELLING()


        third_signal_data = """
        {
            "action" : "buy",
            "ticker" : "AAPL",
            "key" : "STOCKTON_KEY",
            "notes" : "ver=20240922;high=105.0;low=95.0;exchange=NASDAQ;open=98.0;interval=1m;high_interval=1h;low_interval=1m;suggested_stoploss=0.05;takeprofit_percent=0.05;rest_interval=3000",
            "close" : 103.0,
            "contracts" : 1
        }
        """

        table_client_mock.query_entities.return_value = [
            {
                'PartitionKey': 'AAPL-1m', 
                'RowKey': unix_timestamp(), 
                'position_data': '{}', 
                'status': 'selling', 
                'merchant_lastaction_time': 1727000626, 
                'ticker': 'AAPL', 
                'high_interval': '1h', 
                'low_interval': '1m'
            }
        ]

        third_signal = MerchantSignal(json.loads(third_signal_data))
        flow_merchant.handle_market_signal(third_signal)
        
        assert flow_merchant.status() == M_STATE_SELLING()

        forth_signal_data = """
        {
            "action" : "sell",
            "ticker" : "AAPL",
            "key" : "STOCKTON_KEY",
            "notes" : "ver=20240922;high=105.0;low=95.0;exchange=NASDAQ;open=98.0;interval=1m;high_interval=1h;low_interval=1m;suggested_stoploss=0.05;takeprofit_percent=0.05;rest_interval=3000",
            "close" : 103.0,
            "contracts" : 1
        }
        """

        table_client_mock.query_entities.return_value = [
            {
                'PartitionKey': 'AAPL-1m', 
                'RowKey': unix_timestamp(), 
                'position_data': '{}', 
                'status': 'selling', 
                'merchant_lastaction_time': 1727000626, 
                'ticker': 'AAPL', 
                'high_interval': '1h', 
                'low_interval': '1m'
            }
        ]

        forth_signal = MerchantSignal(json.loads(forth_signal_data))
        flow_merchant.handle_market_signal(forth_signal)
        
        assert flow_merchant.status() == M_STATE_RESTING()


if __name__ == '__main__':
    unittest.main()
