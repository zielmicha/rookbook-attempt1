from rookcore import rpc
from rookcore.reactive import Ref

import rookcore.reactive_rpc

class ServerIface(metaclass=rpc.RpcMeta):
    @rpc.rpcmethod(id=1)
    def welcome(self, who: str) -> str: pass

    @rpc.rpcmethod(id=2)
    def welcome_reactive(self, who: Ref[str]) -> Ref[str]: pass
