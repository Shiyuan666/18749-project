class NodeException(Exception):

    def __reduce__(self):
        return type(self), ()


class NodeStopException(NodeException):
    pass


class RPCError(Exception):
    def __init__(self, *args, node=None, **kwargs):
        self.node = node
        super().__init__(*args, **kwargs)

    def __reduce__(self):
        return type(self), ()


class RPCTimeoutError(RPCError):
    pass

class RPCConnectionError(RPCError):
    pass


class RPCConnectionTimeoutError(RPCConnectionError):
    pass
