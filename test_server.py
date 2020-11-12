import argparse
import asyncio
import json

from reliableRPC import service, log
import reliableRPC


class DSServer(reliableRPC.ReliableServer, reliableRPC.Client):

    #  init is called before tasks are run
    def init(self):
        self.state = 0

    def get_checkpoint(self):
        return self.state

    def put_checkpoint(self, state):
        self.state = state

    @service
    def add(self, num):
        self.state += num
        return self.state

    @service
    def minus(self, num):
        self.state -= num
        return self.state

    #  Override
    #  Add Logging of state change
    def on_service_called(self, request):
        super().on_service_called(request)
        if request.service in ["add", "minus"]:
            req_desc = f"<{request.client.tag}, {self.tag}, {request.req_num}, {request.service}>"
            log("state",
                f"my_state_{self.tag} = {self.state} before {req_desc}: " + "< {} {} >".format(request.service, ' '.join([str(a) for a in request.args])))

    def on_service_return(self, response):
        if response.service in ["add", "minus"]:
            res_desc = f"<{response.client.tag}, {self.tag}, {response.req_num}, {response.service}>"
            log("state",
                f"my_state_{self.tag} = {self.state} after {res_desc}")
        super().on_service_return(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config')
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)
    #  server = DSServer(tag=args.tag, port=args.port)
    server = DSServer(config=config["server"])
    server.listen()
    server.run()


if __name__ == "__main__":
    main()
