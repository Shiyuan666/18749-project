import asyncio
import json
import socket
import pickle
import threading
import queue

from enum import Enum
from functools import wraps
from types import MethodType
from reliableRPC.util import log
from reliableRPC.common import *
from reliableRPC.exceptions import *


class Node:
    def __init__(self, tag=None, host=None, port=None, loop=None, config=None):
        self.tag = tag or "##"
        self.host = host
        self.port = port
        self._type = LOCAL
        if config:
            self.tag = config["tag"]
            self.host = config["host"]
            self.port = config["port"]
        self.loop = loop or asyncio.get_event_loop()
        self.loop.set_exception_handler(self.loop_exception_handler)
        self.init()

    def init(self):
        pass

    def clean_up(self):
        pass

    #  Create tasks to run later
    def create_task(self, coro):
        if asyncio.iscoroutine(coro):
            self.loop.create_task(coro)

    def run(self):
        self.loop.set_debug(True)
        self._tasks = []
        for objname in dir(self.__class__):
            func = getattr(self.__class__, objname)
            if hasattr(func, "_task"):
                self._tasks.append(self.loop.create_task(func(self)))
        try:
            self.loop.run_forever()
        except (KeyboardInterrupt, NodeStopException):
            print("")
            for task in self._tasks:
                task.cancel()
            #  self.loop.stop()
            self._clean_up()
            print("Stopping.")
            return

    def _clean_up(self):
        proc = self.clean_up()
        if asyncio.iscoroutine(proc):
            self.loop.run_until_complete(proc)

    #  For pickling
    def __getstate__(self):
        return {"tag": self.tag, "host": self.host, "port": self.port}

    #  For printing
    def __repr__(self):
        return f"{self.tag}({self.host}, {self.port})"

    def __eq__(self, other):
        if isinstance(other, Node):
            return self.tag == other.tag
        return False

    def __hash__(self):
        return hash((self.tag, self.host, self.port))

    def loop_exception_handler(self, loop, context):
        try:
            exception = context["exception"]
            if isinstance(exception, NodeStopException):
                print("Stopping")
                self.loop.stop()
                return
            #  if isinstance(exception, RPCError):
            #      return
        except:
            pass
        loop.default_exception_handler(context)

    def to_Node(self):
        return Node(tag=self.tag, host=self.host, port=self.port)

    @classmethod
    def from_dict(cls, dict):
        node = cls(tag=dict["tag"], host=dict["host"], port=dict["port"])
        return node
