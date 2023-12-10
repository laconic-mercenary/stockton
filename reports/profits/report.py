
import logging
import datetime

from domonic.html import *

def __get_ticker_status(signals):
    return 'profit' if __get_ticker_profit_loss(signals) > 0.0 else 'loss'

def __get_win_percentage(signals):
    logging.info("__get_win_percentage")
    ## calculates the win percentage of all trades for a security
    ## it uses the position size reported by tradingview as the way to determine
    ## if a setup was profitable or not. Recall that there are 4 types of actions
    ## ENTRY, STOP-LOSS, PARTIAL TAKE PROFIT, FULL TAKE PROFIT
    win_count = 0.0
    loss_count = 0.0
    trade_entry_qty = __get_trade_entry_size(signals)
    trade_stop_qty = 0.0
    trade_balance = 0.0
    logging.info(">> START: signals={}, entry_size={}".format(len(signals), trade_entry_qty))
    trade_counter = 0
    sorted_signals = sorted(signals, key=lambda x: int(x['rowKey']))
    for signal in sorted_signals:
        trade_counter += 1
        ## note: posSize refers to the number of shares owned AFTER the trade executed
        ##  for example quantity could be 2 or 3 etc, but posSize could ne 0
        position_size = __extract_position_size(signal)
        price = float(signal["close"])
        quantity = float(signal["contracts"])
        action = signal["action"]
        timestamp = int(signal["rowKey"])
        datetime = __ts_to_datetime(timestamp)
        total_price = (price * quantity)
        logging.info("Trade({}): price={}, pos_size={}, qty={}, action={}, datetime={}".format(trade_counter, price, position_size, quantity, action, datetime))
        if position_size == trade_entry_qty:
            ## trade entered, must be a BUY
            if action != "buy":
                raise Exception("expected a BUY entry, the max quantity assumes that it is a BUY")
            trade_balance -= total_price
        elif position_size == trade_stop_qty:
            ## trade finished - either stop loss or final take profit, must be a SELL
            if action != "sell":
                raise Exception("expected a sell entry, such as a stop-loss or full take profit")
            trade_balance += total_price
            if trade_balance > 0.0: # I consider break-even a loss
                win_count += 1.0 
            else:
                loss_count += 1.0
            logging.info("Trade({}): END - balance={}".format(trade_counter, trade_balance))
            trade_balance = 0.0
        else:
            ## NOTE: a trade in the context of this function ignores the fact that a partial take
            ## profit is actually a TRADE. The term "setup" for multiple trades, makes more sense
            ## a minor take profit, must be a SELL
            if action != "sell":
                raise Exception("expected a sell entry, such as a partial take profit")
            trade_balance += total_price
    logging.info(">> END: win_count={}, loss_count={}".format(win_count, loss_count))
    total_count = win_count + loss_count
    if total_count > 0.0:
        return (win_count / total_count)
    else:
        return total_count ## this means we are still in the setup

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

def __ts_to_datetime(timestamp):
    return datetime.datetime.fromtimestamp(timestamp / 1000.0).isoformat()

def __get_ticker_since(signals):
    sorted_signals = sorted(signals, key=lambda x: int(x['rowKey']))
    unix_stamp = int(sorted_signals[0]['rowKey'])
    return __ts_to_datetime(unix_stamp)

def __get_ticker_latest(signals):
    sorted_signals = sorted(signals, key=lambda x: int(x['rowKey']))
    unix_stamp = int(sorted_signals[-1]['rowKey'])
    return __ts_to_datetime(unix_stamp)

def __extract_position_size(signal):
    if not "notes" in signal:
        raise Exception("notes key was not in signal: " + str(signal))
    notes = signal["notes"]
    if not "posSize" in notes:
        raise Exception("posSize key was not in signal notes: " + notes)
    key_value_pairs = notes.split(';')
    for pair in key_value_pairs:
        key_value = pair.split('=')
        if len(key_value) == 2:
            key, value = key_value
            if key == 'posSize':
                return float(value)
    raise Exception("unable to extract the value for posSize in notes: " + notes)

def __get_trade_entry_size(signals):
    ## gets the number of contracts bought when the trade was entered
    ## find the maximum quantity, because all take profits will be less than the buy amount
    max_contracts = 0.0
    for signal in signals:
        quantity = float(signal["contracts"])
        max_contracts = max(max_contracts, quantity)
    return max_contracts

def __get_ticker_timeframe(signals):
    return '?'

def __ticker_row(ticker, signals):
    logging.info("__ticker_row: ticker={}, signal_count={}".format(ticker, len(signals)))
    status = __get_ticker_status(signals)
    profit_loss = __get_ticker_profit_loss(signals)
    win_percentage = __get_win_percentage(signals)
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
        td(win_percentage * 100.0),
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
    logging.info('create_html()')
    return  html(
                body(
                    div(
                        table(
                            thead(
                                tr(
                                    th('[Overall]'),
                                    __overall_header(data)
                                ),
                                tr(
                                    th('NAME'),
                                    th('STATUS'),
                                    th('PROFIT/LOSS'),
                                    th('TRADES'),
                                    th('WIN %'),
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