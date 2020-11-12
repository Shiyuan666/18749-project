import asyncio
import reliableRPC
import argparse

from reliableRPC import service, Node, log
import reliableRPC


class DSClient(reliableRPC.Client, reliableRPC.Server):

    #  main() responses to console
    async def main(self, args):
        service = args[0]
        ret = None
        try:
            if service in ["add", "a"]:
                ret = await self.server.add(int(args[1]))
            elif service in ["minus", "m"]:
                ret = await self.server.minus(int(args[1]))
            elif service in ["subscribe", "sub"]:
                #  e.g. sub 127.0.0.1 30000
                gfd_node = Node(host=args[1], port=args[2])
                if self.config_server.add_node(gfd_node, verify=True):
                    #  RPC call the subscribe service of config server
                    await self.config_server.subscribe(self)
                    return f"Successfully subscribed to config server {gfd_node}."
                else:
                    return f"Failed subscribing to server {gfd_node}."
        except reliableRPC.RPCError as e:
            return f"RPCError: {e}"
        return ret

    #  clean_up() will be called upon closing
    async def clean_up(self):
        await self.config_server.unsubscribe(self)

    #  Config server is responsible of adding new server
    @service
    def add_server(self, node):
        self.server.add_node(node)

    @service
    def remove_server(self, node):
        self.server.remove_node(node)

    #  Override
    def on_rpc_returned(self, response):
        #  super().on_rpc_returned(response)
        res_desc = f"<{self.tag}, {response.server.tag}, {response.req_num}, {response.status}>"
        result = response.result or ""
        log(response.status, f"Received {res_desc} {result}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--tag')
    args = parser.parse_args()

    from test_gfd import GFD
    from test_server import DSServer
    import json
    #  Set GFD as our config server prototype
    DSClient.config_server = GFD()
    #  Set DSServer as our server prototype
    DSClient.server = DSServer()

    with open("clients.json") as f:
        config = json.load(f)

    client = DSClient(config=config[f"client{args.tag}"]).listen()
    client.console()
    client.run()
