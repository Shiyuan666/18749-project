import argparse
import asyncio
import signal
import enum
import socket
import threading
from asyncio import StreamReader, StreamWriter
from datetime import datetime
from util import log


description = "A fault-tolerant reliable distributed system server."
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = "18749"
DEFAULT_S2_PORT = "18748"
DEFAULT_S3_PORT = "18747"
DEFAULT_TAG = "S1"
barrier = threading.Barrier(2) 
lock = threading.Lock()


class Status(enum.Enum):
    INIT = "initial status"
    RECV = "Received Message"
    BEFORE_PROC = "Before Process"
    PROC = "In Process"
    AFTER_PROC = "After Process"
    SEND = "Send Message"
    WAIT = "Wait for Message"
    ERR = "Error"



class DSServer:
    """ Distributed System Server """

    def __init__(self, tag):
        self.tag = tag
        self.port = None
        self.tcpserver = None
        self.status = Status.INIT
        self.currentRequest = None
        self.state = 0
        self.count = 0

    async def listen(self, port):
        """ bind server to port """
        print("Listening:", port)
        # If we are changing port, close old listen socket
        if self.tcpserver:
            self.tcpserver.close()
            await self.tcpserver.wait_closed()
        self.port = port
        # Start server listening on port with callback
        self.tcpserver = await asyncio.start_server(self.handle_conn, port=port)

    async def handle_conn(self, reader, writer):
        """ callback function of asyncio tcp server """
        try:
            while not reader.at_eof():
                msg = (await reader.readline()).decode()
                service = msg.strip("\r\n")
                if service == "request":
                    payload = await self.serve_request(reader, writer)
                elif service == "heartbeat":
                    await self.heartbeat(reader, writer)
                elif service == "checkpoint":
                    await self.checkpointfunc(reader, writer)
                elif msg.endswith("\n"):
                    log("Service", service)
                    # writer.write(f"Service Requested".encode())
            # EOF
            log("connection", "Connection dropped")
        except asyncio.CancelledError:
            writer.write_eof()

    def connFunc(self, ip, port):
        while True:
            try:
                sock = socket.create_connection((ip, port))
                return sock
            except:
                pass

    def increasecount(self, num):
        lock.acquire()
        if num > self.count:
            self.count = num
        lock.release()
            

    async def connect_s1_s2(self):
        #reader, writer = await asyncio.open_connection(server["host"], server["port"])    
        # if self.tag == "S1":
        sock = self.connFunc("127.0.0.1", DEFAULT_S2_PORT)
        sock_stream = sock.makefile(mode='rw')
        log("connection", "S1 is connected to S2")
        # sock1 = self.connFunc("127.0.0.1", DEFAULT_S3_PORT)
        # sock_stream1 = sock1.makefile(mode='rw')
        # log("connection", "S1 is connected to S3")
        # sock_stream.write("S1 is connected to S2\r\n")
        # sock_stream.flush()
        while True:
            try:
                c = self.count
                log("info", "checkpoint sent S2: state: " + str(self.state) + " count: " + str(c))
                info = "checkpoint\r\n" + str(self.state) + "\n" + str(c) + "\r\n"
                sock_stream.write(info)
                sock_stream.flush()

                self.increasecount(c + 1)
                # log("info", "checkpoint sent S3: state: " + str(self.state) + "count: " + str(self.count))
                # sock_stream1.write(info.encode())
                # sock_stream1.flush()
                # count += 1
                # res = sock_stream.readline()
                await asyncio.sleep(10)
            except (KeyboardInterrupt):
                return

    async def connect_s1_s3(self): 
        # if self.tag == "S1":
        sock = self.connFunc("127.0.0.1", DEFAULT_S3_PORT)
        sock_stream = sock.makefile(mode='rw')
        # # log("connection", "S1 is connected to S3")
        log("connection", "S1 is connected to S3")
        # print("S1 is connected to S3")
        while True:
            try:
                c = self.count
                log("info", "checkpoint sent S3: state: " + str(self.state) + " count: " + str(c))
                info = "checkpoint\r\n" + str(self.state) + "\n" + str(c) + "\r\n"
                sock_stream.write(info)
                sock_stream.flush()
                self.increasecount(c + 1)
                # res = sock_stream.readline()
                await asyncio.sleep(10)
            except (KeyboardInterrupt):
                return

    async def checkpointfunc(self, reader, writer):
        try:
            data = await reader.readuntil(b"\r\n")
            state, count = data.decode().strip("\r\n").split("\n")
            log("checkpoint", f"Update state: {state} count: {count}")
            self.state = int(state)
            self.count = int(count)
        except Exception as e:
            print("Invalid client request:", e)
            return

    async def serve_request(self, reader, writer):
        """ Read and response to client request """
        try:
            data = await reader.readuntil(b"\r\n")
            cli_tag, req_num, payload = data.decode().strip("\r\n").split("\n")

            req_desc = f"<{cli_tag}, {self.tag}, {req_num}, request>"
            log("request", f"Received {req_desc}: {payload}")
            # Service
            log("state",
                f"my_state_{self.tag} = {self.state} before processing {req_desc}")
            self.state += int(payload)
            log("state",
                f"my_state_{self.tag} = {self.state} after processing {req_desc}")
            res_line = f"reply\n{self.tag}\nreq_num\n{self.state}\r\n"
            res_desc = f"<{cli_tag}, {self.tag}, {req_num}, reply>"
            writer.write(res_line.encode())
            log("reply", f"Sending {res_desc}")
        except Exception as e:
            print("Invalid client request:", e)
            return

    async def heartbeat(self, reader, writer):
        """ handle heartbeating events """
        writer.write(f"heartbeat {self.tag}\r\n".encode())
        log("heartbeat", "Sent heartbeat")

    async def close(self):
        """ Shut down server """
        self.tcpserver.close()
        await self.tcpserver.wait_closed()

    def recv_request(self, client_name, request_num):
        self.status = Status.RECV
        self.currentRequest = "<" + client_name + ", " + \
            self.tag + ", " + request_num + ",  request>"
        print("Received " + self.currentRequest)

    def send_request(self):
        self.status = Status.SEND
        print("Sending " + self.currentRequest)
        self.status = Status.WAIT

    def process(self):
        self.status = Status.BEFORE_PROC
        print("my_state_" + self.tag + "=" + self.status +
              "before process " + self.currentRequest)
        self.status = Status.PROC
        # add process in future
        self.status = Status.AFTER_PROC
        print("my_state_" + self.tag + "=" + self.status +
              "after process " + self.currentRequest)


def timestamp():
    return datetime.now().isoformat(timespec='milliseconds')


def run_server(port, server_tag,server):
    # Register server listening socket to open in event loop
    loop = asyncio.get_event_loop()
    loop.create_task(server.listen(port))
    try:
        # Run event loop indefinitely
        loop.run_forever()
    except KeyboardInterrupt:
        # Shutdown gracefully
        loop.run_until_complete(server.close())
        loop.close()
        print("Stopping.")
    #  asyncio.run(server.run())

def connect_s1_s2(server):
    server1 = {
        "host": "127.0.0.1",
        "port": "18748",
        "tag": "S2",
    }
    try:
        asyncio.run(server.connect_s1_s2())
        # print("S1 is connected to S2")
    except BaseException as e:
        # log("error", "S2 Connection Lost")
        print("Error", e)

def connect_s1_s3(server):
    server2 = {
        "host": "127.0.0.1",
        "port": "18747",
        "tag": "S3",
    }
    try:
        asyncio.run(server.connect_s1_s3())
        # print("S1 is connected to S3")
    except BaseException as e:
        log("error", "S3 Connection Lost")
        # print("Error", e)


def main():
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-p', '--port', default=DEFAULT_PORT)
    parser.add_argument('-q', '--port2', default=DEFAULT_S2_PORT)
    parser.add_argument('-r', '--port3', default=DEFAULT_S3_PORT)
    parser.add_argument('-t', '--tag', default=DEFAULT_TAG)

    args = parser.parse_args()
    server = DSServer(args.tag)
    if args.tag == "S1":
        connect_1 = threading.Thread(target=connect_s1_s2,args=(server,))
        connect_1.start()
        connect_2 = threading.Thread(target=connect_s1_s3,args=(server,))
        connect_2.start()
        run_server(args.port, args.tag,server)
        connect_1.join()
        connect_2.join()
    else:
        run_server(args.port, args.tag,server)

if __name__ == "__main__":
    main()
