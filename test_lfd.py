import asyncio
import argparse
import reliableRPC
import reliableRPC
from reliableRPC import service, Node, task
from test_server import DSServer
import json

SEC_PER_MIN = 60
DEFAULT_HB_INT = 5


class LFD(reliableRPC.Server, reliableRPC.Client):

    def init(self):
        self.hb_interval = DEFAULT_HB_INT

    #  @tasks run automatically after Node.run()
    @task
    async def LFD_loop(self):
        self.server_online = False
        while True:
            heartbeat = False
            try:
                await self.server_node.heartbeat()
                heartbeat = True
            except reliableRPC.RPCError as e:
                #  Error hearbeating server
                heartbeat = False
            if heartbeat and not self.server_online:
                try:
                    await self.gfd.server_online(self, self.server_node)
                    self.server_online = True
                except reliableRPC.RPCError as e:
                    print("Failed to connect to GFD.")
            elif not heartbeat and self.server_online:
                print(f"Heartbeat Failue!")
                try:
                    await self.gfd.server_offline(self)
                    self.server_online = False
                except reliableRPC.RPCError as e:
                    print("Failed to connect to GFD.")
            await asyncio.sleep(self.hb_interval)

    @service
    def heartbeat(self):
        pass

    def set_hb_interval(self, hb_interval):
        self.hb_interval = hb_interval


if __name__ == "__main__":
    #  Set groups
    from test_gfd import GFD
    LFD.server = DSServer()
    LFD.gfd = GFD()

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config')
    parser.add_argument('-i', '--interval', type=float,
                        help="heartbeat interval", default=3)
    parser.add_argument('-f', '--freq', type=int,
                        help="Heartbeats per minute, overwrites interval")

    args = parser.parse_args()
    if args.freq:
        args.interval = SEC_PER_MIN / args.freq

    with open(args.config) as f:
        config = json.load(f)
    with open("gfd.json") as f:
        gfd_config = json.load(f)

    server_config = config["server"]
    lfd = LFD(config=config["lfd"]).listen()
    #  Set server node by adding to group
    lfd.server_node = lfd.server.add_node(Node(config=config["server"]))
    #  Set gfd node by adding to group
    lfd.gfd.add_node(Node(config=gfd_config["gfd"]))
    #  Set heartbeat frequency
    lfd.set_hb_interval(args.interval)
    #  Set rpc timeout
    lfd.set_rpc_timeout(1)
    lfd.set_network_timeout(1)
    #  Run LFD
    lfd.run()
