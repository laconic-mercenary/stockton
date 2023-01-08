
import os

__ENV_GET_TICKERS_URL='GET_TICKERS_URL'
__ENV_GET_SIGNALS_URL='GET_SIGNALS_URL'
__ENV_STORAGE_AUTH_KEY='STORAGE_AUTH_KEY'

def __assert_env_exists(env):
    assert env in os.environ

def __get_or_die(env):
    __assert_env_exists(env)
    return os.environ[env]

def get_tickers_url():
    return __get_or_die(__ENV_GET_TICKERS_URL)

def get_signals_url(ticker):
    return __get_or_die(__ENV_GET_SIGNALS_URL)

def get_storage_auth_key():
    return __get_or_die(__ENV_STORAGE_AUTH_KEY)

