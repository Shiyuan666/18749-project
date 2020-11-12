#  18749 ReliableDS

### Running the demo

Node configs were defined in gfd.json, clients.json, machine1.json, machine2.json, machine3.json

```
python3 gfd.py [-P]
python3 lfd.py -c machine1.json
python3 server.py -c machine1.json
python3 client.py -t 1/2/3
```

## GFD

add -P or --passive to run in passive replicated mode

Run gfd:

```sh
python3 gfd.py [-P]
```

### Server groups

```
GFD.client = DSClient()
GFD.lfd = LFD()
GFD.server = DSServer()
```

### Services

#### subscribe(client_node)

Called by clients to subscribe to server list. GFD Notifies subscribed clients of new server, or died server.

e.g.

```
Client.config_server = GFD()
client = Client()
client.config_server.subscribe(client)
```

#### unsubscribe(node)

Same

#### server_online(lfd, server)

#### server_offline(lfd)

Called by LFD to add newly online server, or remove dead server

## LFD

```
python3 lfd.py -c machine1.json
python3 lfd.py -c machine2.json
python3 lfd.py -c machine3.json
```

#### Server groups

```
LFD.server = DSServer()
LFD.gfd = GFD()
```

## DSServer

```
python3 server.py -c machine1.json
```

### Server groups

None

### Services (tentative)

#### add(num)

add num to state

#### minus(num)

minus num from state

## DSClient

```
python3 client.py -t 1
python3 client.py -t 2
python3 client.py -t 3
```

Subscribe to GFD

in console:

` sub 0.0.0.0 30000`

### Server groups

```
DSClient.config_server = GFD()
DSClient.server = DSServer()
```

### Services

#### add_server(node)

#### remove_server(node)

Called by GFD or RM to add or remove a server node

#  ReliableRPC Framework

>   Service Classes API

## reliableRPC.Node

in `reliableRPC/node.py`

>    Node(tag, host, port, config)

Represents a service node with a `tag`, `host` and `port`.

Base class for reliableRPC.

if `config ` is given, the `Node` is loaded from a dictionary

#### init()

This method runs after initialization and before anything else. Override to do initialization work.

#### run()

Runs the service eventloop and begin schedule any `@task` to run.

#### create_task(coroutine)

Schedules a coroutine to run as a task in the eventloop.

#### clean_up()

Called when run() is stopped. Override to do any clean up job.

#### to_Node()

Returns a `Node` object for any `Node` and its subclass object.

#### Node.from_dict(dict)

Classmethod that returns a new `Node` loaded from a dictionary

## reliableRPC.Server(Node)

in `reliableRPC/server.py`

A service providing Node, with functions related to exposing and handling a `@service`.

Not replicated. Any remote service call made on a group waits for reponses from all nodes.

#### listen()

Make the Server accepts incoming requests. Make its services available.

#### on_service_called(request)

Called before serving a request. Override to intercept request object.

#### on_service_return(response)

Called before service returns. Override to intercept service response.

### As remote Server group

#### add_node(node, verify=False)

Adds a node to the server group. If verify is True, verifies the node identity and sets its tag.

Returns the added Server node.

#### get_node(tag)

Returns the node with the tag, raises KeyError when tag doesn't exist.

#### remove_node(node)

Removes a node from the server group, essentially identified by its tag.

#### Internal services

#### @service heartbeat()

A default heartbeat service

## reliableRPC.ReliableServer(Server)

in `reliableRPC/server.py`

A `Server` that is by default replicated. When used as a remote server group, any node added is considered a replica. Calling remote services on the group only waits for the first response.

#### set_checkpoint_interval(interval)

Sets checkpointing interval. Only matters when passively replicated and has backups.

#### get_checkpoint()

Should return current state for checkpoint. Override to provide checkpointing state.

#### put_checkpoint(state)

Should accept state update from primary's checkpoint. Override to update internal state to checkpoint.

#### Internal services

#### @service set_primary(will_be_primary)

Sets a node to be primary or not.

Should NOT be CALLED on a GROUP!

#### @service add_backup(node)

Adds a backup node to a primary node (or service group)

#### @service remove_backup(node)

Removes a node from the backup nodes of a primary node (or service group)

#### @service checkpoint(state, checkpoint_number):

Sends a checkpoint. Updates the state of a backup node.

## reliableRPC.Client(Node)

in `reliableRPC/client.py`

A client Node capable of making reliableRPC remote calls.

The host and port is not used for a Client, only tag matters. (Should probably not be a subclass of Node)

Also provides a console for command line input.

#### console()

Starts a console when run.

#### main(args)

Invoked by console inputs. Not implemented by default. Override to handle console commands.

#### on_rpc_call(request)

Called before making remote call requests. Override to intercept requests.

#### on_rpc_returned(response)

Called when remote call returns. Override to intercept responses.

#### set_rpc_timeout(self, timeout)

Sets the timeout for remote calls of the client. If not called a default timeout is used.

#### set_network_timeout(timeout)

Sets the network timeout of client requests. If not called a default value is used.

## RPC protocol

reliableRPC uses Python pickles for remote calls. A Request and a Response class were defined for making remote calls.

During a remote call, a Client sends a `reliableRPC.Request` to a server node and the server node responses with a `reliableRPC.Response` object.

Defined in `reliableRPC/common.py`

*class **Request***

service: service name

client: calling node

server: serving node

req_num: request number

args: argument list

kwargs: keyword argument dict

*class **Response***

service: service name

client: calling node

server: serving node

req_num: request number

result: service return value

exception: Exception caught in service handling, `None` if none.

## Exceptions in RPC

Exceptions caught during RPC call will be returned in `response.exception`

Exceptions related to RPC call:

defined in `reliableRPC/exceptions.py`

When a remote call times out after `rpc_timeout`, a `reliableRPC.RPCTimeoutError` is raised.

If a node can't be reached, a `relialeRPC.RPCConnectionError` is raised.

If a node doesn't reply after `network_timeout`, a `reliableRPC.RPCConnectionTimeoutError` is raised.

The above exceptions are all subclasses of `reliableRPC.RPCError`

## Usages

### Defining a Node

Define a Server node If a node exposes services. Inherits `ReliableServer` if it is replicated otherwise `Server`.

If a node needs to call services from other nodes, also inherit `Client`

For a client doesn't provide any service, inheirit `Client`

### Providing a Service

Add `@service` decorator to a `Server` object method, the method will be exposed as a service when listen() and run() are called on the server.

### To run a Task

Add `@task` decorator to a `Node` object method, the method will be scheduled to run in the eventloop when run() is called.

### Defining a Server group

Calling a remote service on a server group will send requests to all nodes in the group.

To define a server group, assign an instance of the server group type to a member of your class. For example:

```python
class MyServer(reliableRPC.ReliableServer):
    pass

class MyClient(reliableRPC.Client):
	server = MyServer()
# OR
MyClient.server = MyServer()

my_client = MyClient(tag="C")
```

### Adding a node to a Server group

A node can be added to a server group by calling `add_node(node)` on the server group.

```python
new_node = Node()
my_client.server.add_node(new_node)
```

### Calling a service on a Server group

>    `@service` service calls are all by default asynchronous, that is to say,  `await` is needed for remote service calls.

Making a remote call to a server group will send request to all nodes in the group.

Calls made to a `ReliableServer` group only wait for and return the first response.

To make a group RPC, call the method of the server group.

```python
await my_client.server.heartbeat()
```

### Calling a service on a Server node

Adding a node to a group returns the added node that can be used for making service calls.

```python
new_node = Node()
new_node = my_client.server.add_node(new_node)
await new_node.heartbeat()
```

A node of a group can be retrieved by calling `get_node()` on the group with a tag.

```python
server_node = my_client.server.get_node("S1")
await server_node.heartbeat()
```

### Calling a service asynchronously in the background

```python
my_client.create_task(my_client.server.heartbeat())
```



