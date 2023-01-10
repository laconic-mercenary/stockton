
from . import config
from . import httpc

import logging
import json

__AZURE_FUNC_AUTH_HEADER='x-functions-key'

def __get(target, az_fn_key):
    logging.info('Sending request to: ' + target)
    headers = {
        __AZURE_FUNC_AUTH_HEADER : az_fn_key
    }
    response = httpc.make_get_request(target, headers = headers)
    json_rx = json.loads(response)
    assert 'results' in json_rx
    return json_rx['results']

def get_all_tickers():
    logging.debug('get_all_tickers()')
    target = config.get_tickers_url()
    tickers_auth = config.get_storage_tickers_az_fn_key()
    return __get(target, tickers_auth)

def get_signals(ticker: str):
    logging.debug('get_signals()')
    target = config.get_signals_url(ticker)
    signals_auth = config.get_storage_signals_az_fn_key()
    return __get(target, signals_auth)
