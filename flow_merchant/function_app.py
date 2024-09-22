import json
import logging
import os
import uuid
import time

import azure.functions as func
from azure.data.tables import TableServiceClient

app = func.FunctionApp()

def unix_timestamp() -> int:
    return int(time.time())

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

def M_STORAGE_STATUS_CLOSED():
    return "closed"

def M_STORAGE_STATUS_OPEN():
    return "open"

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

def M_STATE_KEY_HIGH_INTERVAL():
    return "high_interval"

def M_STATE_KEY_LOW_INTERVAL():
    return "low_interval"

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
        self.id = str(uuid.uuid4())

    def action(self):
        return self.get('action')
    
    def ticker(self):
        return self.get('ticker')
    
    def close(self):
        return self.get('close')
        
    def interval(self):
        return self.notes.get('interval')

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
        return self.id

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
                    if key in ["suggested_stoploss", "high",  "low", "takeprofit_percent"]:
                        parsed_notes = float(value)
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
            raise ValueError("Table service cannot be null")
        if broker is None:
            raise ValueError("Broker cannot be null")
        self.state = None
        self.table_service = table_service
        self.broker = broker
        self.TABLE_NAME = "flowmerchant"
        table_service.create_table_if_not_exists(table_name=self.TABLE_NAME)

    def handle_market_signal(self, signal: MerchantSignal) -> None:
        self.log_debug(f"handle_market_signal() - {signal.id()}")
        self.log_info(f"received signal - id={signal.id()} - {signal.info()}")
        try:
            self.load_config()
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
            self.log_info(f"finished handling signal - id={signal.id()}")
    
    def load_state_from_storage(self) -> None:
        self.log_debug(f"load_state_from_storage()")
        query_filter = f"{M_STATE_KEY_PARTITIONKEY()} eq '{self.merchant_id()}' and {M_STATE_KEY_STATUS()} eq '{M_STORAGE_STATUS_OPEN()}'"
        rows = self.table_service.query_entities(query_filter=query_filter)
        if len(rows) > 1:
            raise ValueError(f"Multiple open merchants found for {self.merchant_id()}")
        else:
            """
            Table Rows
            - position_data (json)
                - entry_price
                - entry_time
                - contracts
            - ticker
            - high_interval
            - low_interval
            - bias
            - merchant_id
            - merchant_state
            - merchant_lastaction_time
            - RowKey
            - PartitionId
            """
            if len(rows) == 1:
                self.log_debug(f"found existing merchant - id={self.merchant_id()}")
                row = rows[0]
                merchant_state = { }
                merchant_state[M_STATE_KEY_PARTITIONKEY()] = row.get(M_STATE_KEY_PARTITIONKEY())
                merchant_state[M_STATE_KEY_ROWKEY()] = row.get(M_STATE_KEY_ROWKEY())
                merchant_state[M_STATE_KEY_POSITION_DATA()] = json.loads(row.get(M_STATE_KEY_POSITION_DATA())),
                merchant_state[M_STATE_KEY_STATUS()] = row.get(M_STATE_KEY_STATUS()),
                merchant_state[M_STATE_KEY_LAST_ACTION_TIME()] = row.get(M_STATE_KEY_LAST_ACTION_TIME()),
                merchant_state[M_STATE_KEY_TICKER()] = row.get(M_STATE_KEY_TICKER()),
                merchant_state[M_STATE_KEY_HIGH_INTERVAL()] = row.get(M_STATE_KEY_HIGH_INTERVAL())
                merchant_state[M_STATE_KEY_LOW_INTERVAL()] = row.get(M_STATE_KEY_LOW_INTERVAL())
                self.state = merchant_state
            else:
                self.log_debug(f"no open merchants found for {self.merchant_id()}, creating new...")
                merchant_state = { }
                merchant_state[M_STATE_KEY_PARTITIONKEY()] = self.merchant_id()
                merchant_state[M_STATE_KEY_ROWKEY()] = unix_timestamp()
                merchant_state[M_STATE_KEY_POSITION_DATA()] = json.dumps({})
                merchant_state[M_STATE_KEY_STATUS()] = M_STATE_SHOPPING()
                merchant_state[M_STATE_KEY_LAST_ACTION_TIME()] = unix_timestamp()
                merchant_state[M_STATE_KEY_TICKER()] = self.merchant_id()
                merchant_state[M_STATE_KEY_HIGH_INTERVAL()] = "-"
                merchant_state[M_STATE_KEY_LOW_INTERVAL()] = "-"
                self.table_service.insert_entity(table_name=self.table_name, entity=merchant_state)
                self.state = merchant_state


    def load_config(self) -> None:
        self.log_debug(f"load_config()")
        # low_interval = os.environ.get(M_CFG_LOW_INTERVAL())
        # if not low_interval:
        #     raise ValueError(f"Environment variable {M_CFG_LOW_INTERVAL()} not set")
        # self.low_interval = low_interval

    def _handle_signal_when_shopping(self, signal: MerchantSignal) -> None:
        self.log_debug(f"_handle_signal_when_shopping()")
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
            else:
                raise ValueError(f"Unknown action {signal.action()}")
        elif signal.interval() == self.high_interval():
            if signal.action() == S_ACTION_SELL():
                self._start_shopping()
            
    def _handle_signal_when_selling(self, signal: MerchantSignal) -> None:
        self.log_debug(f"_handle_signal_when_selling()")
        if signal.interval() == self.low_interval():
            if signal.action() == S_ACTION_SELL():
                ## do nothing - allow take profit and stop loss to trigger
                pass
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
        self.log_debugg_debug(f"_start_selling()")
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
        self.table_client.update_entity(entity=self.state)

    def _log_preamble(self) -> str:
        return f"[{self.merchant_id()}, {self.state}, +{self.high_interval()}, -{self.low_interval()}]"

    def log_info(self, message) -> None:
        logging.info(f"{self._log_preamble()} >> {message}")

    def log_debug(self, message) -> None:
        logging.debug(f"{self._log_preamble()} >> {message}")

    ## properties
    def merchant_id(self) -> str:
        ## this should come from tradingview
        return f"{self.ticker()}-{self.interval()}"

    def loaded(self) -> bool:
        return self.state is not None
    
    def status(self) -> str:
        ## this should come from storage
        return self.state.get('status')
    
    def high_interval(self) -> str:
        ## this should come from merchant config
        return self.state.get('high_interval')
    
    def low_interval(self) -> str:
        ## this should come from merchant config
        return self.state.get('low_interval')
        
    def last_action_time(self) -> int:
        ## this should come from storage
        return int(self.state.get('last_action_time'))
    
    def rest_interval_ms(self) -> int:
        ## this should come from merchant config
        return int(self.state.get('rest_interval'))
    
