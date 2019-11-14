import unittest, asyncio, tempfile, functools
from typing import *
from .common import *
from .record import *
from . import serialize, rpc_session, rpc

class HelloIface(metaclass=rpc.RpcMeta):
    @rpc.rpcmethod(id=66)
    def welcome(self, who: str) -> str: raise

class HelloImpl(HelloIface):
    async def welcome(self, who):
        if who == "": raise ValueError("missing name")
        return 'Hello ' + who

class ComplexIface(metaclass=rpc.RpcMeta):
    @rpc.rpcmethod(id=1)
    def get_greeter(self) -> HelloIface: pass

class ComplexImpl(ComplexIface):
    async def get_greeter(self):
        return HelloImpl()

class RpcTest(unittest.TestCase):
    def test_simple(self):
        session2: rpc_session.RpcSession
        root1 = None
        root2 = HelloImpl()
        session1 = rpc_session.RpcSession(root_object=root1,
                                          on_message=lambda data: session2.message_received(data))
        session2 = rpc_session.RpcSession(root_object=root2,
                                          on_message=lambda data: session1.message_received(data))

        finished: asyncio.Future = asyncio.Future()

        def cb(is_err, resp):
            assert not is_err, resp.unserialize(str)
            assert resp.unserialize(str) == 'Hello zielmicha', resp.unserialize(str)
            finished.set_result(None)

        param_type = HelloIface._rpc_method_by_id[66].param_type # type: ignore
        session1.call_with_cb(1, 66, serialize.TypedPayload(type_=param_type, value=param_type(who="zielmicha")), cb)

        asyncio.get_event_loop().run_until_complete(asyncio.wait_for(finished, 5))

    def test_proxy(self):
        session2: rpc_session.RpcSession
        root1 = None
        root2 = HelloImpl()
        session1 = rpc_session.RpcSession(root_object=root1,
                                          on_message=lambda data: session2.message_received(data))
        session2 = rpc_session.RpcSession(root_object=root2,
                                          on_message=lambda data: session1.message_received(data))
        session2._print_error = lambda result: None # type: ignore

        iface = session1.remote_root_object.as_proxy(HelloIface)

        async def run():
            res = await iface.welcome(who="zielmicha")
            assert res == "Hello zielmicha"

            try:
                await iface.welcome(who="")
            except rpc.RemoteError as err:
                assert str(err) == "ValueError: missing name", err
            else:
                assert False

        asyncio.get_event_loop().run_until_complete(asyncio.wait_for(run(), 5))

    def test_complex(self):
        session2: rpc_session.RpcSession
        root1 = None
        root2 = ComplexImpl()
        session1 = rpc_session.RpcSession(root_object=root1,
                                          on_message=lambda data: session2.message_received(data))
        session2 = rpc_session.RpcSession(root_object=root2,
                                          on_message=lambda data: session1.message_received(data))

        iface = session1.remote_root_object.as_proxy(ComplexIface)

        async def run():
            greeter = await iface.get_greeter()
            res = await greeter.welcome(who="zielmicha")
            assert res == "Hello zielmicha"

        asyncio.get_event_loop().run_until_complete(asyncio.wait_for(run(), 5))

    def test_unix_server(self):
        root2 = HelloImpl()

        async def run(path):
            await asyncio.start_unix_server(
                path=path,
                client_connected_cb=functools.partial(rpc_session.RpcSession.start_on_stream, root2))

            client_reader, client_writer = await asyncio.open_unix_connection(path=path)
            sess = rpc_session.RpcSession.start_on_stream(None, client_reader, client_writer)
            iface = sess.remote_root_object.as_proxy(HelloIface)

            for i in range(10):
                res = await iface.welcome(who="zielmicha%d" % i)
                assert res == "Hello zielmicha%d" % i

        with tempfile.TemporaryDirectory() as dir:
            path = dir + '/socket'
            asyncio.get_event_loop().run_until_complete(asyncio.wait_for(run(path), 5))

if __name__ == '__main__':
    unittest.main()
