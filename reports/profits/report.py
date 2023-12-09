
import logging
import datetime

from domonic.html import *

def __get_ticker_status(signals):
    return 'profit' if __get_ticker_profit_loss(signals) > 0.0 else 'loss'

def __get_ticker_profit_loss(signals):
    balance = 0.0
    for signal in signals:
        price = float(signal["close"])
        action = signal["action"]
        quantity = float(signal["contracts"])
        total_price = (price * quantity)
        ## selling is assumed to add to the "balance"
        ## buying is assumed to subtract from the "balance"
        if action == "sell":
            balance += total_price
        elif action == "buy":
            balance -= total_price
        else:
            raise Exception('unknown action: ' + action)
    return round(balance, 2)

def __get_ticker_trades(signals):
    return len(signals)

def __get_ticker_since(signals):
    unix_stamp = int(signals[-1]['rowKey'])
    return datetime.datetime.fromtimestamp(unix_stamp / 1000.0).isoformat()

def __get_ticker_latest(signals):
    unix_stamp = int(signals[0]['rowKey'])
    return datetime.datetime.fromtimestamp(unix_stamp / 1000.0).isoformat()

def __get_ticker_timeframe(signals):
    return '?'

def __ticker_row(ticker, signals):
    status = __get_ticker_status(signals)
    profit_loss = __get_ticker_profit_loss(signals)
    trades = __get_ticker_trades(signals)
    since = __get_ticker_since(signals)
    latest = __get_ticker_latest(signals)
    timeframe = __get_ticker_timeframe(signals)
    trade_is_open = signals[0]['action'] == 'buy'
    return tr(
        td(ticker),
        td(status, _style='color:' + 'lime' if status == 'profit' else 'red'),
        td(profit_loss),
        td(trades),
        td(since),
        td(latest, _style='color:yellow' if trade_is_open else ''),
        td(timeframe)
    )

def __ticker_rows(data):
    results = []
    for ticker in data:
        results.append(__ticker_row(ticker, data[ticker]))
    return results

def __overall_header(data):
    profit_loss = 0.0
    for ticker in data:
        profit_loss += __get_ticker_profit_loss(data[ticker])
    return th(
                'loss' if profit_loss < 0.0 else 'profit',
                _style="color: " + 'red' if profit_loss < 0.0 else 'lime'
            )

def create_html(data):
    logging.debug('create_html()')
    return  html(
                body(
                    div(
                        table(
                            thead(
                                tr(
                                    th('Overall:'),
                                    __overall_header(data)
                                ),
                                tr(
                                    th('NAME'),
                                    th('STATUS'),
                                    th('PROFIT/LOSS'),
                                    th('TRADES'),
                                    th('SINCE'),
                                    th('LATEST'),
                                    th('TIMEFRAME')
                                )
                            ),
                            tbody(__ticker_rows(data)),
                            _class="overall-table"
                        )
                    )
                )
            )

### sample html result
"""
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">z
  </head>
  <body>
    <div>
      <table class="overall-table">
        <thead>
          <tr>
            <th>Overall:</th>
            <th style="color:lime">PROFIT</th>
          </tr>
          <tr>
            <th>NAME</th>
            <th>STATUS</th>
            <th>PROFIT/LOSS</th>
            <th>TRADES</th>
            <th>SINCE</th>
            <th>LATEST</th>
            <th>TIMEFRAME</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>NAME</th>
            <td>STATUS</th>
            <td>PROFIT/LOSS</th>
            <td>TRADES</td>
            <td>SINCE</td>
            <td>LATEST</td>
            <td>TIMEFRAME</td>
          </tr>
        </tbody>
      </table>
    </div>
  </body>
</html>
"""