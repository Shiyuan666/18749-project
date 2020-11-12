import asyncio
import pickle
import socket

from types import MethodType
from reliableRPC.node import Node
from reliableRPC.common import *
from reliableRPC.util import *
from reliableRPC.exceptions import *


def make_rpc(func):
    rpc_name = func.__name__

    @wraps(func)
    async def rpc(node, *args, **kwargs):
        caller = node._owner
        exception_Q = asyncio.Queue()
        request = Request(rpc_name, caller.to_Node(),
                             node, args=args, kwargs=kwargs)
        call = caller.remote_call(
            request, exception_Q=exception_Q)
        try:
            ret = await asyncio.wait_for(call, timeout=caller.rpc_timeout)
        except asyncio.TimeoutError:
            try:
                err = exception_Q.get_nowait()
                raise err
            except asyncio.QueueEmpty:
                pass
            raise RPCTimeoutError(
                f"RPC '{rpc_name}' timeout after {caller.rpc_timeout}s", node=node)
        if ret.exception:
            raise ret.exception
        return ret.result
    rpc._rpc = True
    return rpc


def make_reliable_rpc(func):
    rpc_name = func.__name__

    @wraps(func)
    async def rpc(node_type, *args, **kwargs):
        caller = node_type._owner
        exception_Q = asyncio.Queue(1)
        call = caller.reliable_remote_call(
            node_type, rpc_name, args, kwargs, exception_Q=exception_Q)
        try:
            ret = await asyncio.wait_for(call, timeout=caller.rpc_timeout)
        except asyncio.TimeoutError as e:
            try:
                while True:
                    err = exception_Q.get_nowait()
                    print(err)
            except asyncio.QueueEmpty:
                pass
            raise RPCTimeoutError(
                f"Reliable RPC '{rpc_name}' timeout after {caller.rpc_timeout}s") from e
        if ret.exception:
            raise ret.exception
        return ret.result
    rpc._rpc = True
    return rpc


def make_group_rpc(func):
    rpc_name = func.__name__

    @wraps(func)
    async def rpc(node_type, *args, **kwargs):
        caller = node_type._owner
        exception_Q = asyncio.Queue(1)
        call = caller.group_remote_call(
            node_type, rpc_name, args, kwargs, exception_Q=exception_Q)
        try:
            ret = await asyncio.wait_for(call, timeout=caller.rpc_timeout)
        except asyncio.TimeoutError as e:
            try:
                while True:
                    err = exception_Q.get_nowait()
                    raise err
            except asyncio.QueueEmpty:
                pass
            raise RPCTimeoutError(
                f"Group RPC '{rpc_name}' timeout after {caller.rpc_timeout}s") from e
        try:
            while True:
                err = exception_Q.get_nowait()
                print(err)
        except asyncio.QueueEmpty:
            pass
        for res in ret:
            if res.exception:
                print(res.exception)
        return [{res.server.tag: res.result} for res in ret]
    rpc._rpc = True
    return rpc


class Server(Node):

    def __init__(self, tag=None, host=None, port=None, loop=None, config=None,
                 remote_node=False, listen=False):
        self.listener = None
        self.services = {}
        self._nodes = {}
        super().__init__(tag, host, port, loop, config)
        if remote_node:
            self._make_remote_node()
        if listen:
            self.listen()

    def __get__(self, instance, owner=None):
        #  Used as a remote node descriptor
        if not instance:
            return self
        if self._type != LOCAL and self._type != REMOTE:
            raise NodeException("Not a remote type")
        elif self._type == LOCAL:
            self._make_remote()
        self._owner = instance
        return self

    def _make_online(self):
        if self._type != LOCAL:
            return
        self._type = ONLINE
        self.services = {}
        for objname in dir(self.__class__):
            func = getattr(self.__class__, objname)
            if hasattr(func, "_service"):
                self.services[objname] = func
        return self

    def _make_remote(self):
        if self._type != LOCAL:
            return
        self._type = REMOTE
        for fname in dir(self.__class__):
            func = getattr(self.__class__, fname)
            if hasattr(func, "_service"):
                rpc = make_group_rpc(func)
                if hasattr(func, "_sync") and asyncio.iscoroutinefunction(rpc):
                    rpc = make_sync(rpc)
                setattr(self, fname, MethodType(rpc, self))
        return self

    def _make_remote_node(self):
        if self._type != LOCAL:
            return
        self._type = REMOTE_NODE
        for fname in dir(self.__class__):
            func = getattr(self.__class__, fname)
            if hasattr(func, "_service"):
                rpc = make_rpc(func)
                if hasattr(func, "_sync") and asyncio.iscoroutinefunction(rpc):
                    rpc = make_sync(rpc)
                setattr(self, fname, MethodType(rpc, self))
        return self

    @property
    def nodes(self):
        if self._type != REMOTE:
            print("Error: can only get nodes of a remote node type")
            return None
        return self._nodes

    def listen(self, port=None):
        if self._type != LOCAL and self._type != ONLINE:
            print("Error: remote node can't listen.")
            return
        self._make_online()
        # If we are changing port, close old listen socket
        if port:
            self.port = port
            if self.listener:
                self.listener.close()
        self.listener = self.loop.run_until_complete(
            asyncio.start_server(self._serve_remote_call, port=self.port, family=socket.AF_INET))
        self.sock = self.listener.sockets[0]
        print(f"{self.tag} Listening:", self.sock.getsockname())
        return self

    def on_service_called(self, request):
        req_desc = f"<{request.client.tag}, {self.tag}, {request.req_num}, {request.service}>"
        log(request.service, f"Received request {req_desc}")

    def on_service_return(self, response):
        if response.service not in ["heartbeat"]:
            res_desc = f"<{response.client.tag}, {self.tag}, {response.req_num}, {response.status}>"
            log("reply", f"Sending reply {res_desc}")

    async def _serve_remote_call(self, reader, writer):
        """ callback function of asyncio tcp server """
        try:
            #  sock = writer.get_extra_info("socket")
            while not reader.at_eof():
                #  Read and parse rpc packet
                request_bytes = await reader.readuntil(b"\r\n")
                request_bytes = request_bytes.strip(b"\r\n")
                request = pickle.loads(request_bytes)
                #  Serve request
                if request.service in self.services:
                    self.on_service_called(request)
                    #  service._desc = req_desc  # For service logging
                    #  Call service func/coro and send result back
                    service = self.services[request.service]
                    status = "success"
                    result = None
                    exception = None
                    try:
                        result = service(self, *request.args, **request.kwargs)
                        if asyncio.iscoroutine(result):
                            result = await result
                    except Exception as e:
                        result = e
                        exception = e
                        status = "exception"
                    response = Response(
                        request.service, request.client, self.to_Node(), request.req_num, status, result, exception)
                    response_bytes = pickle.dumps(response)
                    writer.write(response_bytes)
                    writer.write(b"\r\n")
                    #  Log
                    self.on_service_return(response)
                else:
                    print("Service", request.service, "not found")
            # EOF
            #  log("connection", "Connection dropped")
        except asyncio.CancelledError:
            writer.write_eof()
        except asyncio.IncompleteReadError:
            pass
        except ConnectionResetError as e:
            log("WARN", f"Connection dropped")
            return Response(exception=e)

    @sync
    @service
    def verify(self, node_type):
        if node_type.__name__ != self.__class__.__name__:
            raise NodeException("Invalid node.")
        return self.tag

    def add_node(self, node, verify=False):
        new_node = self._add_node(node)
        if verify:
            try:
                tag = new_node.verify(new_node.__class__)
                new_node.tag = tag
                node.tag = tag
            except RPCError as e:
                self.remove_node(node)
                log("error",
                    "Failed to add node because node can't be verified: " + str(e))
                return
        return new_node

    def _add_node(self, node):
        if self._type != REMOTE:
            print("Error: can only add node to remote node type")
            return
        new_node = self.__class__(
            tag=node.tag, host=node.host, port=node.port)._make_remote_node()
        new_node._owner = self._owner
        self._nodes[node.tag] = new_node
        return new_node

    def get_node(self, tag):
        if self._type != REMOTE:
            print("Error: can only get node from a remote node type")
            return
        return self._nodes.get(tag)

    def remove_node(self, node):
        if self._type != REMOTE:
            print("Error: remove_node: must be remote node type")
            return
        try:
            self._nodes.pop(node.tag)
        except:
            pass

    @service
    def heartbeat(self):
        pass


class ReliableServer(Server):

    def __init__(self, tag=None, host=None, port=None, loop=None, config=None,
                 cp_int=8, replicated=True,
                 remote_node=False, listen=False):
        self.is_replica = replicated
        self.is_primary = False
        self.cp_int = cp_int
        self.cp_count = 0
        super().__init__(tag, host, port, loop, config, remote_node, listen)

    def run(self):
        type(self).backups = type(self)(replicated=False)
        super().run()

    def _make_remote(self):
        if self._type != LOCAL:
            return
        self._type = REMOTE
        rpc_maker = make_reliable_rpc if self.is_replica else make_group_rpc
        for fname in dir(self.__class__):
            func = getattr(self.__class__, fname)
            if hasattr(func, "_service"):
                rpc = rpc_maker(func)
                if hasattr(func, "_sync") and asyncio.iscoroutinefunction(rpc):
                    rpc = make_sync(rpc)
                setattr(self, fname, MethodType(rpc, self))

    def set_checkpoint_interval(self, interval):
        self.cp_int = interval

    @service
    def set_primary(self, will_be_primary):
        if self.is_primary and not will_be_primary:
            self.checkpointing_task.cancel()
        if not self.is_primary and will_be_primary:
            self.checkpointing_task = self.create_task(self._checkpointing())
        self.is_primary = will_be_primary

    @service
    def add_backup(self, backup_node):
        if self.is_primary:
            self.backups.add_node(backup_node)

    @service
    def remove_backup(self, backup_node):
        if self.is_primary:
            self.backups.remove_node(backup_node)

    async def _checkpointing(self):
        while True:
            if self.backups.nodes:
                cp = self.get_checkpoint()
                if cp != None:
                    try:
                        await self.backups.checkpoint(cp, self.cp_count)
                        self.cp_count += 1
                    except RPCError as e:
                        print(e)
            await asyncio.sleep(self.cp_int)

    @service
    def checkpoint(self, state, checkpoint_num):
        log("checkpoint", f"Checkpoint {checkpoint_num}: {state}")
        self.put_checkpoint(state)

    def get_checkpoint(self):
        pass

    def put_checkpoint(self, state):
        pass
