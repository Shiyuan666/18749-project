import asyncio
import threading
import queue

from functools import wraps
from .exceptions import *

REMOTE = "remote"
LOCAL = "local"
ONLINE = "online"
REMOTE_NODE = "remote_node"

def service(f):
    f._service = True
    return f


def sync(f):
    f._sync = True
    return f


def task(f):
    @wraps(f)
    async def async_wrapper(self, *args, **kwargs):
        return f(self, *args, **kwargs)

    @wraps(f)
    def sync_wrapper(self, *args, **kwargs):
        return f(self, *args, **kwargs)
    wrapper = sync_wrapper if asyncio.iscoroutinefunction(f) else async_wrapper
    wrapper._task = True
    return wrapper


#  Adapt an async function for sync call
def make_sync(async_func):
    @wraps(async_func)
    def sync_func(*args, **kwargs):
        return sync_await(async_func(*args, **kwargs))
    return sync_func


#  Await a coroutine synchronously using another thread
def sync_await(coro):
    async def thread_await(coro, return_Q):
        try:
            ret = await coro
        except Exception as e:
            return_Q.put(e)
            return
        return_Q.put(ret)
    return_Q = queue.Queue()
    async_call = thread_await(coro, return_Q)
    thread = threading.Thread(target=asyncio.run, args=(async_call, ))
    thread.start()
    thread.join()
    ret = return_Q.get()
    if isinstance(ret, Exception):
        raise ret
    return ret


class Request:

    def __init__(self, service, client, server, req_num=None, args=(), kwargs={}):
        self.service = service
        self.client = client
        self.server = server
        self.req_num = req_num
        self.args = args
        self.kwargs = kwargs


class Response():

    def __init__(self, service=None, client=None, server=None, req_num=None, status="error", result=None, exception=None):
        self.service = service
        self.client = client
        self.server = server
        self.req_num = req_num
        self.status = status
        self.result = result
        self.exception = exception
