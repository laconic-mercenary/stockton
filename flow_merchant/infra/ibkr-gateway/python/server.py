import logging
import config
import ssl

from aiohttp import web


import geoip2.database

from http.server import BaseHTTPRequestHandler
from ib_insync import IB, Stock

def HEADER_CONTENT_TYPE():
    return "Content-Type"

def HEADER_GATEWAY_PASSWORD():
    return "X-Gateway-Password"

def response_not_found(text='not found') -> web.Response:
    return web.Response(status=404, text=text)

def response_ok(text='ok') -> web.Response:
    return web.Response(status=200, text=text)

def response_json_ok(data: any) -> web.Response:
    return web.json_response(data=data)

def response_bad_request(text='bad request') -> web.Response:
    return web.Response(status=400, text=text)

def response_unauthorized(text='unauthorized') -> web.Response:
    return web.Response(status=401, text=text)

def response_server_err(text='server error') -> web.Response:
    return web.Response(status=500, text=text)

def is_in_geofence(ip_address: str) -> bool:
    if ip_address == "127.0.0.1" or ip_address == "localhost" or ip_address == "::1":
        return True
    with geoip2.database.Reader("/tmp/GeoLite2-City.mmdb") as reader:
        response = reader.city(ip_address)
        logging.debug(f"geoip2 response: {response}")
        return response.country.iso_code.lower() == "jp"
    
def is_authorized(headers: dict[str, str]) -> bool:
    if HEADER_GATEWAY_PASSWORD() in headers:
        return headers[HEADER_GATEWAY_PASSWORD()] == config.gateway_password()
    return False

def ssl_context() -> ssl.SSLContext:    
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile=config.tls_cert_file(), keyfile=config.tls_key_file())
    return ssl_context