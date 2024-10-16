import asyncio
import json
import logging
import urllib
import config

from http.server import BaseHTTPRequestHandler
from ib_insync import IB, Stock

def HEADER_CONTENT_TYPE():
    return "Content-Type"

def HEADER_GATEWAY_PASSWORD():
    return "X-Gateway-Password"

def create_request_handler(ib_api: IB, asyncio_loop: asyncio.AbstractEventLoop) -> type[BaseHTTPRequestHandler]:

    class IBKRGatewayHandler(BaseHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            if ib_api is None:
                raise ValueError("ib_api is required")
            if asyncio_loop is None:
                raise ValueError("asyncio_loop is required")
            self.__ib_api = ib_api
            self.__asyncio_loop = asyncio_loop
            super().__init__(*args, **kwargs)

        def do_GET(self):
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path
            if path == "/healthz":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"not found")

        def do_POST(self):
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path
            if path == "/orders":
                self.__handle_place_order()
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Endpoint not found")

        def __authorized(self) -> bool:
            if HEADER_GATEWAY_PASSWORD() in self.headers:
                client_password = self.headers.get(HEADER_GATEWAY_PASSWORD())
                if client_password == config.gateway_password():
                    logging.debug("request authorized")
                    return True
            return False

        def __handle_place_order(self):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                logging.error("Invalid JSON data", exc_info=True)
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"bad request")
                return
            
            if not self.__authorized():
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b"unauthorized")
                return

            future = asyncio.run_coroutine_threadsafe(
                self.place_order(data), self.__asyncio_loop
            )
            try:
                response = future.result()
            except Exception as e:
                logging.error(f"Error placing order {e}", exc_info=True)
                self.send_response(400)
                self.end_headers()
                self.wfile.write("bad request")
                return
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))

        async def place_order(self, data):
            symbol = data.get("symbol")
            action = data.get("action")
            quantity = data.get("quantity")
            take_profit = data.get("take_profit")
            stop_loss = data.get("stop_loss")

            if not all([symbol, action, quantity, take_profit, stop_loss]):
                return {"status": "Missing parameters"}

            contract = Stock(symbol, "SMART", "USD")

            order = self.__ib_api.bracketOrder(
                action,
                quantity,
                limitPrice=None,
                takeProfitPrice=take_profit,
                stopLossPrice=stop_loss
            )

            for o in order:
                self.__ib_api.placeOrder(contract, o)

            timeout = 10
            try:
                await asyncio.wait_for(
                    self.wait_for_order_filled(order[0].orderId), timeout
                )
            except asyncio.TimeoutError:
                return {"status": "Order placed, but no confirmation received within timeout"}

            return {"status": "Order placed", "order_id": order[0].orderId}

        async def wait_for_order_filled(self, orderId):
            while True:
                order = self.__ib_api.orders().get(orderId)
                if order is None:
                    break  # Order no longer exists
                elif order.orderStatus.status in ("Filled", "Cancelled", "Inactive"):
                    break
                await asyncio.sleep(1.0)

    return IBKRGatewayHandler