import time

def unix_timestamp() -> int:
    return int(time.time() * 1000)
