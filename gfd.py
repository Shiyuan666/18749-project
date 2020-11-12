import argparse
import time
import socket
import asyncio
import signal
from util import log
from asyncio import StreamReader, StreamWriter
import threading

DEFAULT_PORT = "18746"
connList = []
# lock = threading.Lock()

async def server_loop(port: str):
	# loop = asyncio.get_running_loop()
	loop = asyncio.get_event_loop()
	# loop.add_signal_handler(signal.SIGINT, int_handler)

	await asyncio.start_server(handle_conn, port=port)

	while True:
		await asyncio.sleep(5)

async def handle_conn(reader: StreamReader, writer: StreamWriter):
	# print("get connList")
	# print("GFD: " + str(len(connList)) + " members: " + str(connList))
	while True:
		try:
			while not reader.at_eof():
				data = await reader.readuntil(b"\r\n")
				# print(data.decode())
				# print(data.decode())
				name, status = data.decode().strip("\r\n").split("\n")
				print(name + " " + status)
				# for i in connList:
				# 	members += i + ", "
				# print("GFD: " + str(len(connList)) + " members: " + str(connList))
				# lock.acquire()
				# print("before: ")
				# print(connList)
				if int(status) == 0:
					if name in connList:
						connList.remove(name)
						# print("GFD: " + str(len(connList)) + " members: " + str(connList))
				else:
					if name not in connList:
						connList.append(name)
						# print("GFD: " + str(len(connList)) + " members: " + str(connList))
				# print(connList)
				print("GFD: " + str(len(connList)) + " members: " + str(connList))
				# lock.release()
		except (KeyboardInterrupt):
			return
		except:
			# print("get except")
			pass

# def int_handler():
# 	print("Stopping.")
# 	# exit(0)
# 	raise SystemExit(0)

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('-p', '--port', default=DEFAULT_PORT)
	args = parser.parse_args()
	print("GFD: " + str(len(connList)) + " members: " + str(connList))
	asyncio.run(server_loop(args.port))

	# loop = asyncio.get_event_loop()
	# sock = socket.create_connection(("127.0.0.1", args.port))
	# sock_stream = sock.makefile(mode='rw')

	



if __name__ == "__main__":
	main()