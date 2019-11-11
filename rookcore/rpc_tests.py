import unittest, asyncio
from typing import *
from .common import *
from .record import *
from . import serialize, rpc_session, rpc

class HelloIface(metaclass=rpc.RpcMeta):
    @rpc.rpcmethod(id=66)
    def welcome(self, who: str) -> str: raise

class HelloImpl(HelloIface):
    async def welcome(self, who):
        return 'Hello ' + who

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

        asyncio.get_event_loop().run_until_complete(finished)

if __name__ == '__main__':
    unittest.main()
