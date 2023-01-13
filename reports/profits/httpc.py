
import urllib
import urllib.request
import logging

__REQUEST_TIMEOUT=10.0

def make_get_request(target, headers={}):
    logging.debug('make_get_request()')
    req = urllib.request.Request(target, headers = headers)
    response = urllib.request.urlopen(req, timeout=__REQUEST_TIMEOUT).read()
    return response