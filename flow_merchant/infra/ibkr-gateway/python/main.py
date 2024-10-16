
import threading
import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import config
import logging
import server
import ib_insync

def run_main():
    logging.info("Starting...")
    ib = ib_insync.IB()
    asyncio_loop = asyncio.new_event_loop()

    def start_asyncio_loop():
        asyncio.set_event_loop(asyncio_loop)
        ib.connect(config.ibkr_api_addr(), config.ibkr_api_port(), clientId=config.ibkr_client_id())
        asyncio_loop.run_forever()

    asyncio_thread = threading.Thread(target=start_asyncio_loop, daemon=True)
    asyncio_thread.start()

    gateway_handler = server.create_request_handler(ib, asyncio_loop)
    server_address = ("", config.server_port())
    httpd = ThreadingHTTPServer(server_address, gateway_handler)
    try:
        logging.info("Started server on port %s", config.server_port())
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received, shutting down the server")
        pass
    finally:
        logging.info("Cleaning up...")
        httpd.server_close()
        ib.disconnect()
        asyncio_loop.call_soon_threadsafe(asyncio_loop.stop())
        logging.info("Shutdown complete")


if __name__ == "__main__":
    run_main()