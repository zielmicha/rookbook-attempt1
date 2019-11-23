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
    def __new__(self, class_name, bases, namespace):
        abc_namespace: dict = {}

        by_id: dict = {}

        for name, v in namespace.items():
            if name.startswith('__'): continue

            assert isinstance(v, _TmpRpcMethod), "%s is not annotated with @rpcmethod" % name
            abc_namespace[name] = abc.abstractmethod(v.method)

            if v.id in by_id:
                raise ValueError('method id collision (%s vs %s)' % (by_id[v.id], v))

            param_type = make_record(f'{class_name}.{name}_Params', v.param_fields)

            by_id[v.id] = _RpcMethod(name=name, param_type=param_type,
                                     return_type=v.return_type if v.return_type is not None else type(None))

        abc_namespace['_rpc_method_by_id'] = by_id
        abc_namespace['__module__'] = namespace['__module__']

        iface_type = abc.ABCMeta(class_name, bases + (_RpcObj,), abc_namespace)

        remote_proxy_namespace: dict = {}

        for id, method in  by_id.items():
            d = {}
            d[f'_{method.name}_return_type'] = method.return_type
            d[f'_{method.name}_param_type'] = method.param_type
            d['TypedPayload'] = serialize.TypedPayload
            exec(f'''def {method.name}(self, **kwargs):
                       return self.rpc_call({id}, TypedPayload(_{method.name}_param_type, _{method.name}_param_type(**kwargs)), _{method.name}_return_type)''', d)
            remote_proxy_namespace[method.name] = d[method.name]

        iface_type.RemoteProxy = type(class_name + '.RemoteProxy', (iface_type, ), remote_proxy_namespace) # type: ignore

        return iface_type

class RemoteError(Exception): pass

class _RpcMethod(NamedTuple):
    name: str
    param_type: Any
    return_type: Any

class _TmpRpcMethod(NamedTuple):
    id: int
    param_fields: Any
    return_type: Any
    method: Any

def rpcmethod(id: int):
    def wrapper(method):
        sig = inspect.signature(method)

        assert sig.return_annotation != inspect.Parameter.empty, "missing return type annotation" # type: ignore

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

        return _TmpRpcMethod(id=id, param_fields=param_fields, return_type=sig.return_annotation, method=method)

    return wrapper
