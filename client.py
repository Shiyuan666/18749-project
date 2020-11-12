import argparse
import asyncio
import socket
import threading

from datetime import datetime
from util import log

description = "A fault-tolerant reliable distributed system client."
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = "18749"
DEFAULT_PORT2 = "18748"
DEFAULT_PORT3 = "18747"
DEFAULT_TAG = "C1"
DEFALUT_INTERVAL = 5

REQUEST_LIST = []
lock = threading.Lock()
LARGESTREQ = -1;

class DSClient:
    """ Distributed System Client """

    def __init__(self, tag):
        self.tag = tag
        self.waitingRequest = set()
        self.req_num = 101
        # self.lastreq = -1

    async def connect(self, server: dict):
        self.server = server
        """ open connection with server and write requests """
        reader, writer = await asyncio.open_connection(server["host"], server["port"])
        await self.send_requests(reader, writer, server["interval"])

    async def send_requests(self, reader, writer, interval):
        async for req_num, payload in self.requests(interval):
            #  if random.randint(0, 100) % 2:
            #      req = "Check Status"
            if writer.is_closing():
                break
            req_line = f"request\n{self.tag}\n{req_num}\n{payload}\r\n"
            req_desc = f"<{self.tag}, {self.server['tag']}, {req_num}, request>"
            lock.acquire()
            global LARGESTREQ
            if (req_num > LARGESTREQ) and (req_num not in REQUEST_LIST):
                REQUEST_LIST.append(req_num)
                LARGESTREQ = req_num
            lock.release()
            writer.write(req_line.encode())
            log("request", f"Sent {req_desc}: {payload}")

            # Handle response
            data = await reader.readuntil(b'\r\n')
            service, _, _, payload = data.decode().strip("\r\n").split("\n")
            res_desc = f"<{self.tag}, {self.server['tag']}, {req_num}, reply>"
            if service != "reply":
                print(
                    f"Invalid response received from server {server['tag']}: {data.decode()}")
                continue
            lock.acquire()
            if req_num in REQUEST_LIST:
                REQUEST_LIST.remove(req_num)
                log("reply", f"Received {res_desc}: Server state {payload}")
            else:
                log("discard", f"Discarded {res_desc}")
            # print(req_num)
            # print(REQUEST_LIST)
            lock.release()
            # log("reply", f"Received {res_desc}: Server state {payload}")
            #  if 'Server' in data.decode():
            #      print(f"{'[Reply]': <15} {timestamp()} {data.decode()}")
            #  elif 'ERROR' in data.decode():
            #      print('Server received message, but ' + data.decode())
            #  await asyncio.sleep(3)
        print("Stopping.")

    async def requests(self, interval):
        """ pseudo request generator using random numbers """
        import random
        for _ in range(10000):
            req_str = random.randint(0, self.req_num)
            # await asyncio.sleep(2 + random.random() * 4)
            await asyncio.sleep(interval)
            yield self.req_num, req_str
            self.req_num += 1

    def recv(self, server, requestNum):
        print("Received <" + self.tag + ", " +
              server + ", " + requestNum + ", reply>")
        if request not in self.waitingRequest:
            print("request number " + requestNum +
                  ": Discarded duplicate reply from " + server)
        else:
            self.waitingRequest.remove(requestNum)


def launch_client(args):
    client = DSClient(args.tag)
    server = {
        "host": args.host,
        "port": args.port,
        "tag": "S1",
        "interval": int(args.interval)
    }
    try:
        asyncio.run(client.connect(server))
    except BaseException as e:
        print("Stopping.", e)

def launch_client2(args):
    client = DSClient(args.tag)
    server = {
        "host": args.host,
        "port": args.port2,
        "tag": "S2",
        "interval": int(args.interval)
    }
    try:
        asyncio.run(client.connect(server))
    except BaseException as e:
        print("Stopping.", e)

def launch_client3(args):
    client = DSClient(args.tag)
    server = {
        "host": args.host,
        "port": args.port3,
        "tag": "S3",
        "interval": int(args.interval)
    }
    try:
        asyncio.run(client.connect(server))
    except BaseException as e:
        print("Stopping.", e)

def main():
    parser = argparse.ArgumentParser(description=description, add_help=False)
    parser.add_argument('-p', '--port', default=DEFAULT_PORT)
    parser.add_argument('-q', '--port2', default=DEFAULT_PORT2)
    parser.add_argument('-r', '--port3', default=DEFAULT_PORT3)
    parser.add_argument('-h', '--host', default=DEFAULT_HOST)
    parser.add_argument('-t', '--tag', default=DEFAULT_TAG)
    parser.add_argument('-i', '--interval', default=DEFALUT_INTERVAL)

    args = parser.parse_args()
    # print(args)
    launch_client(args)
    # worker1 = threading.Thread(target=launch_client, args=(args,))
    # worker1.start()
    # worker2 = threading.Thread(target=launch_client2, args=(args,))
    # worker2.start()
    # worker3 = threading.Thread(target=launch_client3, args=(args,))
    # worker3.start()
    # worker1.join()
    # worker2.join()
    # worker3.join()
    #  asyncio.run(connect(args.host, args.port))


if __name__ == "__main__":
    main()
