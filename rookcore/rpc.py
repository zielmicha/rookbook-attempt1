from typing import *
from .record import *
from . import serialize
import inspect, abc

__all__ = ['RpcIface', 'RpcMeta', 'rpcmethod']

class RpcIface:
    pass

class _RpcObj(RpcIface):
    async def rpc_call(self, method_id, params: serialize.AnyPayload):
        method = self._rpc_method_by_id[method_id] # type: ignore
        params_obj = params.unserialize(method.param_type)
        return_obj = await getattr(self, method.name)(**params_obj._to_dict())

        return serialize.TypedPayload(value=return_obj, type_=method.return_type)

class RpcMeta(type): # inherit from type to make Mypy happy
    def __new__(self, name, bases, namespace):
        abc_namespace: dict = {}

        by_id: dict = {}

        for name, v in namespace.items():
            if name.startswith('__'): continue

            assert isinstance(v, _TmpRpcMethod), "%s is not annotated with @rpcmethod" % name
            abc_namespace[name] = abc.abstractmethod(v.method)

            if v.id in by_id:
                raise ValueError('method id collision (%s vs %s)' % (by_id[v.id], v))

            by_id[v.id] = _RpcMethod(name=name, param_type=v.param_type, return_type=v.return_type)

        abc_namespace['_rpc_method_by_id'] = by_id

        return abc.ABCMeta(name, bases + (_RpcObj,), abc_namespace)

class _RpcMethod(NamedTuple):
    name: str
    param_type: Any
    return_type: Any

class _TmpRpcMethod(NamedTuple):
    id: int
    param_type: Any
    return_type: Any
    method: Any

def rpcmethod(id: int):
    def wrapper(method):
        sig = inspect.signature(method)

        assert sig.return_annotation != inspect.Parameter.empty # type: ignore

        param_fields = []

        for i, (name, param) in enumerate(sig.parameters.items()):
            if i == 0:
                assert name == "self", "parameter 0 should be called self"
                continue
            assert param.annotation != inspect.Parameter.empty, ("parameter %s has no annotation" % name) # type: ignore

            param_fields.append(field(
                name,
                id=i,
                type=param.annotation,
                **({} if param.default == inspect.Parameter.empty else {'default': param.default})
            ))

        param_type = make_record('_Params', param_fields)

        return _TmpRpcMethod(id=id, param_type=param_type, return_type=sig.return_annotation, method=method)

    return wrapper
