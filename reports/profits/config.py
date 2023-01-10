
import os

ENV_GET_TICKERS_URL='GET_TICKERS_URL'
ENV_GET_SIGNALS_URL='GET_SIGNALS_URL'
ENV_STORAGE_TICKERS_AZ_FN_KEY='STORAGE_TICKERS_AZ_FN_KEY'
ENV_STORAGE_SIGNALS_AZ_FN_KEY='STORAGE_SIGNALS_AZ_FN_KEY'
ENV_TO_EMAIL='TO_EMAIL'
ENV_FROM_EMAIL='FROM_EMAIL'
ENV_EMAIL_PASSWORD='EMAIL_PASSWORD'
ENV_EMAIL_SUBJECT='EMAIL_SUBJECT'

def __assert_env_exists(env):
    if not env in os.environ:
        raise Exception(env + ' - a required environment variable is not specified')

def __get_or_die(env):
    __assert_env_exists(env)
    return os.environ[env]

def get_tickers_url():
    return __get_or_die(ENV_GET_TICKERS_URL)

def get_signals_url(ticker):
    url = __get_or_die(ENV_GET_SIGNALS_URL)
    return url + "/" + ticker

def get_storage_signals_az_fn_key():
    return __get_or_die(ENV_STORAGE_SIGNALS_AZ_FN_KEY)

def get_storage_tickers_az_fn_key():
    return __get_or_die(ENV_STORAGE_TICKERS_AZ_FN_KEY)

def get_to_email():
    return __get_or_die(ENV_TO_EMAIL)

def get_from_email():
    return __get_or_die(ENV_FROM_EMAIL)

def get_email_subject():
    return __get_or_die(ENV_EMAIL_SUBJECT)

def get_email_password():
    return __get_or_die(ENV_EMAIL_PASSWORD)
