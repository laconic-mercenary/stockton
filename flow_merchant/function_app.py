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
            auth_level=func.AuthLevel.ANONYMOUS)
def merchant_api(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    if req.method not in ["GET", "POST"]:
        return func.HttpResponse(f"Invalid operation", status_code=405)
    if req.method == "GET":
        if 'health' in req.params:
            return func.HttpResponse("OK", status_code=200)
        if 'events_test' in req.params:
            try:
                default_event_logger().log_event("events_test")
                return func.HttpResponse("OK", status_code=200)
            except Exception as e:
                logging.error(f"error logging event, {e}")
                return func.HttpResponse(f"error logging event, {e}", status_code=500)
        with TableServiceClient.from_connection_string(os.environ['storageAccountConnectionString']) as table_service:
            table_client = table_service.get_table_client(table_name="flowmerchant")
            entities = table_client.list_entities()
            rows = [dict(entity) for entity in entities]
            return func.HttpResponse(json.dumps(rows), mimetype="application/json")
    elif req.method == "POST":
        body = req.get_body().decode('utf-8')
        headers = dict(req.headers)
        logging.info(f"received merchant signal: {body}")
        logging.info(f"headers: {headers}")
        with TableServiceClient.from_connection_string(os.environ['storageAccountConnectionString']) as table_service:
            broker = default_broker()
            event_logger = default_event_logger()
            try:
                event_logger.log_notice(f"received market signal - {body}")
                message_body = json.loads(body)
                signal = MerchantSignal.parse(message_body)
                merchant = Merchant(table_service, broker, event_logger)
                merchant.handle_market_signal(signal)
            except Exception as e:
                logging.error(f"error handling market signal {body}, {e}", exc_info=True)
                event_logger.log_error(f"error handling market signal {body}, {e}")
                                    
##
# Merchant Consumer
##

@app.function_name(name="merchant_consumer")
@app.queue_trigger(arg_name="msg", 
                    queue_name="merchantsignals",
                    connection="storageAccountConnectionString")
def merchant_consumer(msg: func.QueueMessage) -> None:
    body = msg.get_body().decode('utf-8')
    logging.info("received merchant signal: {body}")
    with TableServiceClient.from_connection_string(os.environ['storageAccountConnectionString']) as table_service:
        broker = default_broker()
        event_logger = default_event_logger()
        try:
            event_logger.log_notice(f"received market signal - {body}")
            message_body = json.loads(body)
            signal = MerchantSignal.parse(message_body)
            merchant = Merchant(table_service, broker, event_logger)
            merchant.handle_market_signal(signal)
        except Exception as e:
            logging.error(f"error handling market signal {body}, {e}", exc_info=True)
            event_logger.log_error(f"error handling market signal {body}, {e}")
        
"""
UTILS
"""
def unix_timestamp() -> int:
    return int(time.time())

"""
DISCORD LOGGER
"""

from abc import ABC, abstractmethod
import requests
import datetime

def DISCORD_ENV_WEBHOOK_URL():
    return "DISCORD_WEBHOOK_URL"

class EventLoggable(ABC):
    @abstractmethod
    def log_event(self, message):
        pass
    @abstractmethod
    def log_notice(self, message):
        pass
    @abstractmethod
    def log_error(self, message):
        pass
    @abstractmethod
    def log_success(self, message):
        pass

class ConsoleLogger(EventLoggable):
    def log_event(self, message):
        print(message)
    def log_notice(self, message):
        print(message)
    def log_error(self, message):
        print(message)
    def log_success(self, message):
        print(message)

class DiscordClient(EventLoggable):
    def __init__(self):
        self.base_url = os.environ[DISCORD_ENV_WEBHOOK_URL()]

    def log_event(self, message):
        self.log_notice(message)

    def log_notice(self, message):
        message = {
            "embeds": [
                {
                    "title": "Flow Merchant - NOTICE",
                    "description": message,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
            ]
        }
        self.send_message(message)

    def log_error(self, message):
        message = {
            "embeds": [
                {
                    "title": "Flow Merchant - ERROR",
                    "description": message,
                    "color": 15158332,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
            ]
        }
        self.send_message(message)

    def log_success(self, message):
        message = {
            "embeds": [
                {
                    "title": "Flow Merchant - SUCCESS",
                    "description": message,
                    "color": 3066993,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
            ]
        }
        self.send_message(message)

    def send_message(self, message):
        url = f"{self.base_url}"
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers, json=message, timeout=7)
        if response.status_code > 302:
            logging.error(f"Failed to send message: {response.text}")

def default_event_logger() -> EventLoggable:
    return DiscordClient()

"""
BROKER
"""

from abc import ABC, abstractmethod

class MarketOrderable(ABC):
    @abstractmethod
    def place_buy_market_order(self, ticker: str, contracts: float, take_profit: float, stop_loss: float) -> None:
        pass

class IBKRBroker(MarketOrderable):
    def place_buy_market_order(self, ticker: str, contracts: float, take_profit: float, stop_loss: float) -> None:
        logging.info(f"IBKRBroker.place_buy_market_order({ticker}, {contracts}, {take_profit}, {stop_loss})")

def default_broker() -> MarketOrderable:
    return IBKRBroker()

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

##
# Keys that are stored in the merchant state (Azure Storage)

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

def M_STATE_KEY_REST_INTERVAL():
    return "rest_interval_minutes"

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

##
# Keys found in the trading view alerts JSON

def S_ALERT_KEY_ACTION():
    return "action"

def S_ALERT_KEY_TICKER():
    return "ticker"

def S_ALERT_KEY_CLOSE():
    return "close"

def S_ALERT_KEY_HIGH():
    return "high"

def S_ALERT_KEY_LOW():
    return "low"

def S_ALERT_KEY_SUGGESTED_STOPLOSS():
    return "suggested_stoploss"

def S_ALERT_KEY_HIGH_INTERVAL():
    return "high_interval"

def S_ALERT_KEY_LOW_INTERVAL():
    return "low_interval"

def S_ALERT_KEY_TAKEPROFIT_PERCENT():
    return "takeprofit_percent"

def S_ALERT_KEY_NOTES():
    return "notes"

def S_ALERT_KEY_CONTRACTS():
    return "contracts"

def S_ALERT_KEY_VERSION():
    return "version"

def S_ALERT_REST_INTERVAL():
    return "rest_interval_minutes"

class MerchantSignal:
    def __init__(self, msg_body):
        if not msg_body:
            raise ValueError("Message body cannot be null")
        self.msg = msg_body
        self.notes = self._parse_notes()
        self.TABLE_NAME = "flowmerchant"
        self._id = str(uuid.uuid4())

    @staticmethod
    def parse(msg_body):
        if not msg_body:
            raise ValueError("Message body cannot be null")
        if msg_body[S_ALERT_KEY_ACTION()] not in [S_ACTION_BUY(), S_ACTION_SELL()]:
            logging.error(f"Invalid action: {msg_body[S_ALERT_KEY_ACTION()]}")
            raise ValueError("Invalid action")
        if not msg_body[S_ALERT_KEY_TICKER()]:
            logging.error(f"Ticker is null: {msg_body[S_ALERT_KEY_TICKER()]}")
            raise ValueError("Ticker cannot be null")
        if not msg_body[S_ALERT_KEY_TICKER()]:
            logging.error(f"Invalid ticker: {msg_body[S_ALERT_KEY_TICKER()]}")
            raise ValueError("Ticker must be a string")
        if not msg_body[S_ALERT_KEY_CLOSE()]:
            logging.error(f"Close is null: {msg_body[S_ALERT_KEY_CLOSE()]}")
            raise ValueError("Close cannot be null")
        if not msg_body[S_ALERT_KEY_CLOSE()]:
            logging.error(f"Invalid close: {msg_body[S_ALERT_KEY_CLOSE()]}")
            raise ValueError("Close must be a number")
        if not isinstance(msg_body[S_ALERT_KEY_CLOSE()], float):
            logging.error(f"Invalid close: {msg_body[S_ALERT_KEY_CLOSE()]}")
            raise ValueError("Close must be a number")
        if not msg_body[S_ALERT_KEY_NOTES()]:
            logging.error(f"Notes are null: {msg_body[S_ALERT_KEY_NOTES()]}")
            raise ValueError("Notes cannot be null")
        if not msg_body[S_ALERT_KEY_CONTRACTS()]:
            logging.error(f"Contracts are null: {msg_body[S_ALERT_KEY_CONTRACTS()]}")
            raise ValueError("Contracts cannot be null")
        if not isinstance(msg_body[S_ALERT_KEY_CONTRACTS()], int):
            logging.error(f"Invalid contracts: {msg_body[S_ALERT_KEY_CONTRACTS()]}")
            raise ValueError("Contracts must be an integer")
        return MerchantSignal(msg_body)

    def action(self):
        return self.get(S_ALERT_KEY_ACTION())
    
    def ticker(self):
        return self.get(S_ALERT_KEY_TICKER())
    
    def close(self):
        return self.get(S_ALERT_KEY_CLOSE())
        
    def interval(self):
        return self.notes.get(S_ALERT_KEY_CLOSE())
    
    def high_interval(self):
        return self.notes.get(S_ALERT_KEY_HIGH_INTERVAL())
    
    def low_interval(self):
        return self.notes.get(S_ALERT_KEY_LOW_INTERVAL())

    def suggested_stoploss(self):
        return self.notes.get(S_ALERT_KEY_SUGGESTED_STOPLOSS())
    
    def high(self):
        return self.notes.get(S_ALERT_KEY_HIGH())
    
    def low(self):
        return self.notes.get(S_ALERT_KEY_LOW())
    
    def takeprofit_percent(self):
        return self.notes.get(S_ALERT_KEY_TAKEPROFIT_PERCENT())
    
    def contracts(self):
        return self.notes.get(S_ALERT_KEY_CONTRACTS())

    def version(self):
        return self.notes.get(S_ALERT_KEY_VERSION())
    
    def rest_interval(self):
        return self.notes.get(S_ALERT_REST_INTERVAL())

    def id(self):
        return self._id

    def _parse_notes(self):
        notes = self.get(S_ALERT_KEY_NOTES())
        parsed_notes = {}
        if notes:
            pairs = notes.split(';')
            for pair in pairs:
                if '=' in pair:
                    key, value = pair.split('=')
                    key = key.strip()
                    value = value.strip()
                    if key in [S_ALERT_KEY_VERSION(), S_ALERT_KEY_SUGGESTED_STOPLOSS(), S_ALERT_KEY_HIGH(),  S_ALERT_KEY_LOW(), S_ALERT_KEY_TAKEPROFIT_PERCENT()]:
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
    def __init__(self, table_service: TableServiceClient, broker: MarketOrderable, events_logger: EventLoggable) -> None:
        if table_service is None:
            raise ValueError("TableService cannot be null")
        if broker is None:
            raise ValueError("Broker cannot be null")
        if events_logger is None:
            raise ValueError("EventsLogger cannot be null")
        self.state = None
        self.table_service = table_service
        self.broker = broker
        self.events_logger = events_logger
        self.TABLE_NAME = "flowmerchant"
        table_service.create_table_if_not_exists(table_name=self.TABLE_NAME)

    def handle_market_signal(self, signal: MerchantSignal) -> None:
        logging.debug(f"handle_market_signal() - {signal.id()}")
        logging.info(f"received signal - id={signal.id()} - {signal.info()}")
        self.events_logger.log_event(f"received signal - {signal.ticker()} {signal.interval()} {signal.action()}")
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
        client = self.table_service.get_table_client(table_name=self.TABLE_NAME)
        rows = list(client.query_entities(query_filter))
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
                client.create_entity(entity=self.state)

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
        self.state[M_STATE_KEY_PARTITIONKEY()] = f"stockton-{signal.ticker()}-{signal.low_interval()}-{signal.high_interval()}-{signal.version()}"
        self.state[M_STATE_KEY_ROWKEY()] = f"stockton-{signal.ticker()}-{signal.id()}"
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
        self.state[M_STATE_KEY_INTERVAL()] = signal.interval()
        self.state[M_STATE_KEY_REST_INTERVAL()] = signal.rest_interval()
        self.state[M_STATE_KEY_LAST_ACTION_TIME()] = unix_timestamp()
        
    def _handle_signal_when_shopping(self, signal: MerchantSignal) -> None:
        logging.debug(f"_handle_signal_when_shopping()")
        if signal.low_interval() == signal.high_interval():
            ### if low and high are the same, then we assume we're ok with just buying a single trading view alert
            ### in this case we go straight to buying (shopping -> buying is for confluence)
            logging.warning(f"low and high are the same, going straight to buying")
            self._start_buying()
            self._handle_signal_when_buying(signal)
        else:
            if signal.interval() == self.high_interval():
                if signal.action() == S_ACTION_BUY():
                    self._start_buying()
                
    def _handle_signal_when_buying(self, signal: MerchantSignal) -> None:
        self.log_debug(f"_handle_signal_when_buying()")
        if signal.interval() == self.low_interval():
            if signal.action() == S_ACTION_BUY():
                self._place_order(signal)
                self._start_selling()
        elif signal.interval() == self.high_interval():
            if signal.action() == S_ACTION_SELL():
                self._start_shopping()
            
    def _handle_signal_when_selling(self, signal: MerchantSignal) -> None:
        ### what to do here? just allow tne take profits and stop loss to trigger
        ### at least for now. This will become useful later when we include bearish and bullish bias
        self.log_debug(f"_handle_signal_when_selling()")
        if signal.interval() == self.low_interval():
            if signal.action() == S_ACTION_SELL():
                ## do nothing - allow take profit and stop loss to trigger
                self._start_resting()
        elif signal.interval() == self.high_interval():
            if signal.action() == S_ACTION_SELL():
                ## do nothing - allow take profit and stop loss to trigger
                self._start_resting()
                ###self.broker.sell_all_orders_for(signal.ticker())
                ###self._start_shopping()

    def _handle_signal_when_resting(self) -> None:
        self.log_debug(f"_handle_signal_when_resting()")
        now_timestamp_ms = unix_timestamp()
        rest_interval_ms = self.rest_interval_minutes() * 60 * 1000
        if (now_timestamp_ms > self.last_action_time() + rest_interval_ms):
            self._start_shopping()
        else:
            time_left_in_seconds = now_timestamp_ms - (self.last_action_time() + rest_interval_ms)
            time_left_in_seconds = time_left_in_seconds / 1000.0
            self.log_info(f"Resting for another {time_left_in_seconds} seconds")

    def _start_buying(self) -> None:
        self.log_debug(f"_start_buying()")
        self.state[M_STATE_KEY_STATUS()] = M_STATE_BUYING()
        self.state[M_STATE_KEY_LAST_ACTION_TIME()] = unix_timestamp()
        self._sync_with_storage()
        self.events_logger.log_notice(f"{self.merchant_id()} started buying")

    def _start_shopping(self) -> None:
        self.log_debug(f"_start_shopping()")
        self.state[M_STATE_KEY_STATUS()] = M_STATE_SHOPPING()
        self.state[M_STATE_KEY_LAST_ACTION_TIME()] = unix_timestamp()
        self._sync_with_storage()
        self.events_logger.log_notice(f"{self.merchant_id()} started shopping")

    def _start_selling(self) -> None:
        self.log_debug(f"_start_selling()")
        self.state[M_STATE_KEY_STATUS()] = M_STATE_SELLING()
        self.state[M_STATE_KEY_LAST_ACTION_TIME()] = unix_timestamp()
        self._sync_with_storage()
        self.events_logger.log_notice(f"{self.merchant_id()} started selling")

    def _start_resting(self) -> None:
        self.log_debug(f"_start_resting()")
        self.state[M_STATE_KEY_STATUS()] = M_STATE_RESTING()
        self.state[M_STATE_KEY_LAST_ACTION_TIME()] = unix_timestamp()
        self._sync_with_storage()
        self.events_logger.log_notice(f"{self.merchant_id()} started resting")

    def _sync_with_storage(self) -> None:
        self.log_debug(f"_sync_with_storage()")
        client = self.table_service.get_table_client(table_name=self.TABLE_NAME)
        client.update_entity(entity=self.state)

    def _place_order(self, signal: MerchantSignal) -> None:
        self.log_debug(f"_place_order()")

        def calculate_take_profit(signal: MerchantSignal) -> float:
            return signal.close() + (signal.close() * signal.takeprofit_percent())
        
        def calculate_stop_loss(signal: MerchantSignal) -> float:
            ## subjective ... may change based on evolving experience
            if signal.suggested_stoploss() > 0.3:
                raise ValueError(f"Suggested stoploss {signal.suggested_stoploss()} is greater than 30%")
            return signal.close() - (signal.close() * signal.suggested_stoploss())

        def safety_check(close, take_profit, stop_loss, quantity) -> None:
            if signal.close() < signal.suggested_stoploss():
                raise ValueError(f"Close price {signal.close()} is less than suggested stoploss {signal.suggested_stoploss()}")
            if signal.close() > signal.takeprofit_percent():
                raise ValueError(f"Close price {signal.close()} is greater than take profit {signal.suggested_stoploss()}")

        take_profit = calculate_take_profit(signal)
        stop_loss = calculate_stop_loss(signal)
        quantity = signal.contracts()
        safety_check(signal.close(), take_profit, stop_loss, quantity)
        self.events_logger.log_success(f"Placing order for {quantity} {signal.ticker()} at {signal.close()} with take profit {take_profit} and stop loss {stop_loss}")
        self.broker.place_buy_market_order(signal.ticker(), quantity, take_profit, stop_loss)
                

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
    
    def rest_interval_minutes(self) -> int:
        ## this should come from merchant config
        return int(self.state.get(M_STATE_KEY_REST_INTERVAL()))
    

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
