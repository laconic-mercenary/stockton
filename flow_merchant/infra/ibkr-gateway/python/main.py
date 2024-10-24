import asyncio
import nest_asyncio
import logging
from aiohttp import web
import config
import server
import ib_insync
import ibkr

async def handle_health_check(request):
    logging.debug("health_check")
    if server.is_in_geofence(request.remote):
        return server.response_ok("ok")
    return server.response_not_found()

async def handle_test(request):
    logging.info("test")
    if not server.is_in_geofence(request.remote):
        return server.response_not_found()
    if not server.is_authorized(request.headers):
        return server.response_unauthorized()
    ib = request.app["ib"]
    ib_asst = ibkr.Assistant(ib)
    result = { }
    result["positions"] = ib_asst.positions()
    result["openOrders"] = ib_asst.get_open_orders()
    result["unrealizedPnl"] = ib_asst.get_unrealized_pnl()
    result["availableFunds"] = ib_asst.get_available_funds()
    result["buyingPower"] = ib_asst.get_buying_power()
    result["equityWithLoan"] = ib_asst.get_equity_with_loan()
    
    ib_asst.place_stock_bracket_order(
        ticker="AAPL",
        currency=config.order_currency(),
        limit_price=236.0,
        take_profit=238.0,
        stop_loss=235.0,
        quantity=5.0,
        onOrderStatus=lambda trade: logging.info(f"trade status update: {trade}")
    )

    return web.json_response(result)

async def handle_orders(request):
    if not server.is_in_geofence(request.remote):
        return server.response_not_found()
    if not server.is_authorized(request.headers):
        return server.response_unauthorized()
    ib = request.app["ib"]
    
    merchant_order_data = request.json()
    logging.info(f"Received order from flowmerchant: {merchant_order_data}")
    
    attributes = merchant_order_data["attributes"]

    if not "net.revanchist.flowmerchant.IBKROrder" in attributes["type"]:
        logging.error(f"Unknown order type: {attributes["type"]}")
        return server.response_bad_request("invalid attribute type")
    if not "/api/flow_merchant" in attributes["source"]:
        logging.error(f"Unknown order source: {attributes["source"]}")
        return server.response_bad_request("invalid attribute source")
    if not "data" in merchant_order_data:
        logging.error(f"Unknown order type: {attributes["type"]}")
        return server.response_bad_request("missing data")

    data = merchant_order_data["data"]
    if not "orders" in merchant_order_data["data"]:
        logging.error(f"Unknown order type: {attributes["type"]}")
        return server.response_bad_request("missing orders")
    
    orders = data["orders"]
    if not "market_order" in orders:
        logging.error(f"Unknown order type: {attributes["type"]}")
        return server.response_bad_request("missing market_order")
    if not "stop_loss_order" in orders:
        logging.error(f"Unknown order type: {attributes["type"]}")
        return server.response_bad_request("missing stop_loss_order")
    if not "take_profit_order" in orders:
        logging.error(f"Unknown order type: {attributes["type"]}")
        return server.response_bad_request("missing take_profit_order")
    if not "ticker" in orders["market_order"]:
        logging.error(f"Unknown order type: {attributes["type"]}")
        return server.response_bad_request("missing ticker")
    if not "contracts" in orders["market_order"]:
        logging.error(f"Unknown order type: {attributes["type"]}")
        return server.response_bad_request("missing contracts")
    if not "limit_price" in orders["market_order"]:
        logging.error(f"Unknown order type: {attributes["type"]}")
        return server.response_bad_request("missing limit_price")
    if not "stop_loss_price" in orders["stop_loss_order"]:
        logging.error(f"Unknown order type: {attributes["type"]}")
        return server.response_bad_request("missing stop_loss_price")
    if not "take_profit_price" in orders["take_profit_order"]:
        logging.error(f"Unknown order type: {attributes["type"]}")
        return server.response_bad_request("missing take_profit_price")
    
    ticker = orders["market_order"]["ticker"]
    limit_price = orders["market_order"]["limit_price"]
    contracts = orders["market_order"]["contracts"]
    stop_loss = orders["stop_loss_order"]["stop_loss_price"]
    take_profit = orders["take_profit_order"]["take_profit_price"]

    ib_asst = ibkr.Assistant(ib)
    try:
        ib_asst.place_stock_bracket_order(
            ticker=ticker,
            currency=config.order_currency(),
            limit_price=limit_price,
            take_profit=take_profit,
            stop_loss=stop_loss,
            quantity=contracts,
            onOrderStatus=lambda trade: logging.info(f"[TRADE STATUS] trade status update: {trade}")
        )
    except Exception as e:
        logging.error(f"error on order placement: {e}",  exc_info=True)
        return server.response_server_err("order-placement-error")
    return server.response_ok("order-placed")

async def start_server():
    logging.info("Starting server...")
    ib = ib_insync.IB()
    await ib.connectAsync(
        host=config.ibkr_api_addr(),
        port=config.ibkr_api_port(),
        clientId=config.ibkr_client_id(rand=True),
        timeout=10,
        readonly=False
    )

    app = web.Application()
    app["ib"] = ib  # Store IB instance in the app
    app.add_routes([web.get("/healthz", handle_health_check), web.post("/orders", handle_orders)])

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "", config.server_port(), ssl_context=server.ssl_context())
    await site.start()

    client_pass = config.gateway_password()
    logging.info("API clients must use key %s with header %s", client_pass[:2] + "*" * (len(client_pass) - 2), server.HEADER_GATEWAY_PASSWORD())

    logging.info("Server started on port %s", config.server_port())
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received, shutting down")
    finally:
        await runner.cleanup()
        ib.disconnect()
        logging.info("Shutdown complete")

def set_gateway_password():
    import os
    import sys

    gateway_password = None
    for arg in sys.argv[1:]:
        if arg.startswith("gateway-password="):
            gateway_password = arg.split("=")[1]
            break
    if gateway_password:
        os.environ[config.ENV_GATEWAY_PASSWORD()] = gateway_password
    else:
        raise ValueError("gateway-password parameter not provided")
    
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    set_gateway_password()
    nest_asyncio.apply()
    asyncio.run(start_server())
