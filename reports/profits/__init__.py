import datetime
import logging

from . import storage
from . import report
from . import email

import azure.functions as func

def get_ticker_data():
    logging.info('get_ticker_data()')
    data = { }
    for ticker in storage.get_all_tickers():
        data[ticker] = storage.get_signals(ticker)
    for key in data:
        data[key] = sorted(data[key], key=lambda x: int(x['rowKey']))
    return data

def create_report(data):
    logging.info('create_report()')
    return str(report.create_html(data))

def email_report(report):
    logging.info('email_report()')
    email.send_email(report)

def execute():
    logging.info('execute()')
    data = get_ticker_data()
    logging.info(str(data))
    report = create_report(data)
    logging.debug(report)
    email_report(report)

def main(mytimer: func.TimerRequest):
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()

    logging.info('starting profit report at %s', utc_timestamp)

    if mytimer.past_due:
        logging.warn('the timer is past due!')

    try:
        execute()
    except Exception as ex:
        logging.error(str(ex))
        raise ex
    finally:
        logging.info('finished profit report')
