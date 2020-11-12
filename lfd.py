import argparse
import time
import threading
import socket
import signal
import sys
import asyncio

DEFAULT_PORT = "18749"
DEFAULT_GFD_PORT = "18746"
DEFAULT_INTL = 5
SEC_PER_MIN = 60

DEFAULT_TAG = "1"
# NAME = "0"
# SERVER_STATUS = 0

# async def connect(host: str, port: str):
#     reader, writer = await asyncio.open_connection(host, port)
#     print(port)
#     while True:
#         togfdstr = f"S{NAME}\n{str(SERVER_STATUS)}\r\n"
#         # writer.write(b"Msg from the client\n")
#         print(togfdstr)
#         writer.write(togfdstr.encode())
#         await asyncio.sleep(5)

# def gfd_func(portNum):
#     asyncio.run(connect("127.0.0.1", portNum))
#     print("thread gets")

# def int_handler():
#     print("Stopping.")
#     exit(0)
class LFD:
    def __init__(self, args):
        self.SERVER_STATUS = 0
        self.tag = args.tag
        # self.talk2server(args)

    async def connect(self, host: str, port: str):
        reader, writer = await asyncio.open_connection(host, port)
        print(port)
        while True:
            # print("line 45")
            togfdstr = f"S{self.tag}\n{str(self.SERVER_STATUS)}\r\n"
            # print("LFD" + self.tag + ": send to GFD status: " + str(self.SERVER_STATUS))
            # writer.write(b"Msg from the client\n")
            # print(togfdstr)
            writer.write(togfdstr.encode())
            await asyncio.sleep(5)

    def gfd_func(self, portNum):
        asyncio.run(self.connect("127.0.0.1", portNum))
        # print("thread gets")

    def connFunc(self, ip, port):
        while True:
            try:
                sock = socket.create_connection((ip, port))
                return sock
            except:
                pass

    def talk2server(self, args):
        sock = self.connFunc("127.0.0.1", args.port)
        sock_stream = sock.makefile(mode='rw')

        while True:
            """ Poll server heartbeat constantly """
            try:
                sock_stream.write("heartbeat\r\n")
                sock_stream.flush()
                res = sock_stream.readline()
                # print("line 54 " + res)
                if res == "":
                    self.SERVER_STATUS = 0
                    print("Hearbeat Failure! Server stopped.")
                    print("LFD" + self.tag + ": delete replica S" + self.tag)
                    # fflush()
                    sock = self.connFunc("127.0.0.1", args.port)
                    sock_stream = sock.makefile(mode='rw')
                    # break
                else:
                    if self.SERVER_STATUS == 0:
                        # print("line 61: " + res)
                        print("LFD" + self.tag + ": add replica S" + self.tag) # need to print "LFD1: add replica S1" with self name and server name
                    self.SERVER_STATUS = 1
                    print(res.strip("\r\n"))
                    time.sleep(args.interval)
            except (BrokenPipeError, ConnectionResetError):
                self.SERVER_STATUS = 0
                print("Hearbeat Failure! Server stopped.")
                print("LFD" + self.tag + ": delete replica S" + self.tag)
                # fflush()
                sock = self.connFunc("127.0.0.1", args.port)
                sock_stream = sock.makefile(mode='rw')
                break
            except (KeyboardInterrupt):
                return
            except:
                self.SERVER_STATUS = 0
                print("Hearbeat Failure! Server stopped.")
                # print("Stopping.")
                print("LFD" + self.tag + ": delete replica S" + self.tag)
                # fflush()
                sock = self.connFunc("127.0.0.1", args.port)
                sock_stream = sock.makefile(mode='rw')
                break


def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    raise SystemExit(0)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', default=DEFAULT_PORT)
    parser.add_argument('-i', '--interval', type=float, default=DEFAULT_INTL)
    parser.add_argument('-f', '--freq', type=int,
                        help="Heartbeats per minute, overwrites interval")
    parser.add_argument('-t', '--tag', default=DEFAULT_TAG)
    parser.add_argument('-g', '--gfd', default=DEFAULT_GFD_PORT)
    args = parser.parse_args()
    NAME = args.tag
    if args.freq:
        args.interval = SEC_PER_MIN / args.freq

    # import socket
    # sock = socket.create_connection(("127.0.0.1", args.port))

    lfd = LFD(args)

    gfd_thread = threading.Thread(target=lfd.gfd_func, args=(args.gfd,))
    gfd_thread.start()

    server_thread = threading.Thread(target=lfd.talk2server, args=(args,))
    server_thread.start()
    # signal.signal(signal.SIGINT, signal_handler)
    # sock = connFunc("127.0.0.1", args.port)
    # sock_stream = sock.makefile(mode='rw')

    # while True:
    #     """ Poll server heartbeat constantly """
    #     try:
    #         sock_stream.write("heartbeat\r\n")
    #         sock_stream.flush()
    #         res = sock_stream.readline()
    #         if res == "":
    #             SERVER_STATUS = 0
    #             # print("Hearbeat Failure! Server stopped.")
    #             # break
    #         else:
    #             if SERVER_STATUS == 0:
    #                 print(res)
    #                 print("LFD" + NAME + ": add replica S" + NAME) # need to print "LFD1: add replica S1" with self name and server name
    #             SERVER_STATUS = 1
    #             print(res.strip("\r\n"))
    #             time.sleep(args.interval)
    #     except (BrokenPipeError, ConnectionResetError):
    #         SERVER_STATUS = 0
    #         # print("Hearbeat Failure! Server stopped.")
    #         # break
    #     except:
    #         SERVER_STATUS = 0
    #         # print("Stopping.")
    #         # break

    server_thread.join()
    gfd_thread.join()

if __name__ == "__main__":
    main()
