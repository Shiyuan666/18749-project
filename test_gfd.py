import asyncio
import reliableRPC
import json
import argparse
from reliableRPC import task, service, log, sync
from test_client import DSClient
from test_lfd import LFD
from test_server import DSServer


DEFAULT_INT = 5

class GFD(reliableRPC.Client, reliableRPC.Server):

    #  init() runs before tasks when run() is called
    def init(self):
        self.membership = {}
        self.active_nodes = set()
        self.backup_nodes = set()
        self.passive = False
        self.primary_server = None
        self.hb_interval = DEFAULT_INT

    def set_passive(self, passive):
        self.passive = passive

    def set_hb_interval(self, interval):
        self.hb_interval = interval

    #  @tasks are run automatically when run()
    @task
    async def GFD_loop(self):
        while True:
            try:
                await self.lfd.heartbeat()
            except reliableRPC.RPCError as e:
                if e.node:
                    lfd_node = e.node
                    log("LFD", f"Heartbeat Fail: {e}")
                    log("membership", f"Losing machine of {lfd_node.tag}")
                    await self.server_offline(lfd_node)
                    self.lfd.remove_node(lfd_node)
                else:
                    print("Network Failure")
            await asyncio.sleep(4)

    def print_membership(self):
        log("membership", "{}: {} member: {}".format(self.tag, len(self.membership), " ".join([node.tag for _, node in self.membership.items()])))

    @service
    def subscribe(self, node):
        client_node = self.client.add_node(node)
        for node in self.active_nodes:
            #  Add existing servers to clients at subscribe
            self.create_task(client_node.add_server(node))

    @service
    def unsubscribe(self, node):
        self.client.remove_node(node)

    #  server_online and server_offline called by LFDs
    @service
    def server_online(self, lfd_node, server_node):
        if lfd_node.tag in self.membership:
            return
        else:
            self.membership[lfd_node.tag] = server_node
            self.print_membership()
            self.lfd.add_node(lfd_node)
            server_node = self.server.add_node(server_node)
            if self.passive:
                if self.primary_server is None:
                    self.primary_server = server_node
                    self.active_nodes.add(server_node)
                    self.create_task(server_node.set_primary(True))
                    self.create_task(self.client.add_server(server_node))
                else:
                    self.backup_nodes.add(server_node)
                    self.create_task(self.primary_server.add_backup(server_node))
            else:
                self.active_nodes.add(server_node)
                self.create_task(self.client.add_server(server_node))

    @service
    def server_offline(self, lfd_node):
        if lfd_node.tag in self.membership:
            server_node = self.membership.pop(lfd_node.tag)
            self.server.remove_node(server_node)
            self.print_membership()
            if self.passive:
                if server_node == self.primary_server:
                    self.active_nodes.remove(server_node)
                    self.create_task(self.client.remove_server(server_node))
                    #  TODO: change primary
                else:
                    self.backup_nodes.remove(server_node)
                    self.create_task(self.primary_server.remove_backup(server_node))
            else:
                self.active_nodes.remove(server_node)
                self.create_task(self.client.remove_server(server_node))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-P', '--passive', action='store_true')
    parser.add_argument('-i', '--interval')
    args = parser.parse_args()

    GFD.client = DSClient()
    GFD.lfd = LFD()
    GFD.server = DSServer()

    with open("gfd.json") as f:
        config = json.load(f)

    #  gfd = GFD(tag="gfd", port="30001", listen=True)
    gfd = GFD(config=config["gfd"]).listen()
    gfd.set_passive(args.passive)
    gfd.set_hb_interval(args.interval or DEFAULT_INT)
    gfd.set_rpc_timeout(2)
    gfd.set_network_timeout(1)
    gfd.run()


if __name__ == "__main__":
    main()
