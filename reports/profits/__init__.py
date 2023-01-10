import datetime
import logging

from . import storage
from . import report
from . import email

import azure.functions as func

def get_ticker_data():
    logging.debug('get_ticker_data()')
    data = { }
    for ticker in storage.get_all_tickers():
        data[ticker] = storage.get_signals(ticker)
    return data

def create_report(data):
    logging.debug('create_report()')
    return str(report.create_html(data))

def email_report(report):
    logging.debug('email_report()')
    email.send_email(report)

def execute():
    logging.debug('execute()')
    data = get_ticker_data()
    logging.debug(str(data))
    report = create_report(data)
    logging.debug(report)
    email_report(report)

def main(mytimer: func.TimerRequest):
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()

    logging.debug('starting profit report at %s', utc_timestamp)

    if mytimer.past_due:
        logging.warn('the timer is past due!')

    try:
        execute()
    except Exception as ex:
        logging.error(str(ex))
        raise ex
    finally:
        logging.info('finished profit report')
