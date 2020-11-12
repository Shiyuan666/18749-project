from datetime import datetime
import time


def timestamp():
    return time.time_ns()
    #  return datetime.now().isoformat(timespec='milliseconds')


def log(event, msg):
    print("{: <12} {} {}".format(f"[{event}]", timestamp(), msg))


def dump_address(addr):
    return addr[0] + ":" + addr[1]


def load_address(addr_str):
    return tuple(addr_str.split(":"))
