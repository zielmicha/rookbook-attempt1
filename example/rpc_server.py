from typing import *
from rookcore.rpc import *

class FooIface(metaclass=RpcMeta):
    @rpcmethod(id=1)
    def foo1(self, x: int) -> int: raise
