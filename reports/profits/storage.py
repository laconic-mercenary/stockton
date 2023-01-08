
import config
import httpc
import logging
import json

__AZURE_FUNC_AUTH_HEADER='x-functions-key'

def __get(target):
    auth = config.get_storage_auth_key()
    code, response = httpc.make_get_request(target, headers = { __AZURE_FUNC_AUTH_HEADER : auth })
    if code != 200:
        logging.error('target: %s, code: %d, response: %s', target, code, response)
        raise Exception('error when querying tickers')
    json_rx = json.loads(response)
    assert 'results' in json_rx
    return json_rx['results']

def get_all_tickers():
    target = config.get_tickers_url()
    return __get(target)

def get_signals(ticker: str) -> list[str]:
    target = config.get_signals_url(ticker)
    return __get(target)
