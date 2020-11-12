from datetime import datetime


def timestamp():
    return datetime.now().isoformat(timespec='milliseconds')


def log(event, msg):
    print("{: <12} {} {}".format(f"[{event}]", timestamp(), msg))
