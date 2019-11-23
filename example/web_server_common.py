from rookcore import rpc

class ServerIface(metaclass=rpc.RpcMeta):
    @rpc.rpcmethod(id=1)
    def welcome(self, who: str) -> str: pass
