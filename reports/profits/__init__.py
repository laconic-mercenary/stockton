import datetime
import logging

import storage

import azure.functions as func

def get_ticker_data():
    data = { }
    tickers = storage.get_all_tickers()
    for ticker in tickers:
        signals = storage.get_signals(ticker)
        data[ticker] = signals
    return data

def create_report(data):
    pass

def email_report(report):
    pass

def execute():
    data = get_ticker_data()
    logging.info(str(data))
    report = create_report(data)
    email_report(report)

def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()

    logging.debug('Executing...')

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)

    try:
        execute()
    except Exception as ex:
        logging.error(str(ex))
