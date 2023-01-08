
import urllib

__REQUEST_TIMEOUT=10

def make_get_request(target, headers={}):
    req = urllib.request.Request(target, headers = headers)
    response = urllib.request.urlopen(req).read()
