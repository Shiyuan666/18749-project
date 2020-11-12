import asyncio
import pickle

from aioconsole import ainput
from reliableRPC.node import Node
from reliableRPC.util import log, load_address
from reliableRPC.exceptions import *
from reliableRPC.common import *


class Client(Node):

    def __init__(self, tag=None, host=None, port=None, loop=None, config=None,
                 rpc_timeout=3, network_timeout=3):
        self.req_num = 101
        self.rpc_timeout = rpc_timeout
        self.network_timeout = network_timeout
        super().__init__(tag, host, port, loop, config)

    async def _console(self):
        while True:
            try:
                cmdline = await ainput(">>> ")
                args = cmdline.split(" ")
                if not args:
                    continue
                ret = await self.main(args)
                if ret:
                    print("<<<", ret)
                await asyncio.sleep(1/100)
            except EOFError as e:
                raise NodeStopException from e
            except Exception as e:
                print(e)

    def console(self):
        self.loop.create_task(self._console())

    def main(self, args):
        print("main() not implemented.")
        pass

    #  Return with first response
    async def reliable_remote_call(self, node_type, fname, args, kwargs, exception_Q=None):
        responses = asyncio.Queue()
        if not node_type.nodes:
            return Response(fname, result="No node available for requested service.")
        for tag, node in node_type.nodes.items():
            request = Request(fname, self.to_Node(), node, self.req_num, args, kwargs)
            self.loop.create_task(self.remote_call(
                request, response_Q=responses, exception_Q=exception_Q))
        self.req_num += 1
        return await responses.get()

    #  Wait for all responses
    async def group_remote_call(self, node_type, fname, args, kwargs, exception_Q=None):
        responses = asyncio.Queue()
        if not node_type.nodes:
            return []
        results = []
        for tag, node in node_type.nodes.items():
            results.append(None)
            request = Request(fname, self.to_Node(), node, self.req_num, args, kwargs)
            self.req_num += 1
            self.loop.create_task(self.remote_call(
                request, response_Q=responses, exception_Q=exception_Q))
        for i in range(len(results)):
            results[i] = await responses.get()
        return results

    async def remote_call(self, request, response_Q=None, exception_Q=None):
        if not request.req_num:
            request.req_num = self.req_num
            self.req_num += 1
        # Generate connection with node
        node = request.server
        try:
            reader, writer = await asyncio.open_connection(
                host=node.host, port=node.port)
        except Exception:
            err = RPCConnectionError(
                f"Failed connecting to node {node}.", node=node)
            if exception_Q:
                await exception_Q.put(err)
            else:
                raise err
            return Response(exception=err)
        #  Send rpc request
        request_bytes = pickle.dumps(request)
        writer.write(request_bytes)
        writer.write(b"\r\n")
        self.on_rpc_call(request)
        #  Receive rpc response and close connection
        try:
            response_bytes = await asyncio.wait_for(reader.readuntil(b"\r\n"), timeout=self.network_timeout)
        except asyncio.TimeoutError:
            err = RPCConnectionTimeoutError(
                f"Timeout waiting for node {node.tag}.", node=node)
            if exception_Q:
                await exception_Q.put(err)
            else:
                raise err
            return err

        writer.write_eof()
        writer.close()
        #  Parse response
        response = pickle.loads(response_bytes.strip(b"\r\n"))
        result = response.result
        if response.exception:
            #  Remote function returned error
            if exception_Q:
                await exception_Q.put(response.exception)
            else:
                raise result
        #  Log
        self.on_rpc_returned(response)
        #  Write back result
        if response_Q:
            await response_Q.put(response)
            await writer.wait_closed()
        return response

    def on_rpc_call(self, request):
        req_desc = f"<{self.tag}, {request.server.tag}, {request.req_num}, {request.service}>"
        log("request", f"Sent request {req_desc}")
        #  super().on_rpc_call(request)

    def on_rpc_returned(self, response):
        #  super().on_rpc_returned(response)
        res_desc = f"<{self.tag}, {response.server.tag}, {response.req_num}, {response.status}>"
        log(response.status, f"Received {res_desc}")

    #  Set timeouts
    def set_rpc_timeout(self, timeout):
        self.rpc_timeout = timeout
        return self

    def set_network_timeout(self, timeout):
        self.network_timeout = timeout
        return self

