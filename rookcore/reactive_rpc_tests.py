import unittest, asyncio, tempfile, functools
from typing import *
from .common import *
from .record import *
from .reactive import *
from . import serialize, rpc_session, rpc, reactive_rpc

class HelloIface(metaclass=rpc.RpcMeta):
    @rpc.rpcmethod(id=1)
    def welcome(self) -> Ref[int]: raise

class HelloImpl(HelloIface):
    def __init__(self, ref1):
        self.ref1 = ref1

    async def welcome(self):
        return self.ref1

class RpcTest(unittest.TestCase):
    def test_proxy(self):
        session2: rpc_session.RpcSession
        root1 = None
        ref1 = VarRef(5)
        root2 = HelloImpl(ref1)
        session1 = rpc_session.RpcSession(root_object=root1,
                                          on_message=lambda data: session2.message_received(data))
        session2 = rpc_session.RpcSession(root_object=root2,
                                          on_message=lambda data: session1.message_received(data))

        iface = session1.remote_root_object.as_proxy(HelloIface)

        async def run():
            ref1p = await iface.welcome()
            assert ref1p.value == 5

            ref_is_set: asyncio.Future[None] = asyncio.Future()

            o = Observer(ref1p, lambda: ref_is_set.set_result(None))
            ref1.value = 6
            stabilise()

            await ref_is_set
            o.close()
            assert ref1p.value == 6
            assert ref1.value == 6

            ref_is_set1: asyncio.Future[None] = asyncio.Future()
            o1 = Observer(ref1, lambda: ref_is_set1.set_result(None))

            ref1p.value = 4
            stabilise()
            await ref_is_set1

            assert ref1.value == 4
            assert ref1p.value == 4

        asyncio.get_event_loop().run_until_complete(asyncio.wait_for(run(), 5))

if __name__ == '__main__':
    unittest.main()
