from typing import *
from .record import *
from .common import Bijection
from . import serialize, rpc
import weakref, dataclasses

CallRequest = make_record('CallRequest', [
    field('id', int, id=1),
    field('obj_id', int, id=2),
    field('method_id', int, id=3),
    field('params', serialize.AnyPayload, id=4),
])

CallResponse = make_record('CallResponse', {
    field('id', int, id=1),
    field('value', serialize.AnyPayload, id=2),
})

FinalizeResponse = make_record('FinalizeResponse', {
    field('id', int, id=1),
})

AdjustRefCount = make_record('AdjustRefCount', {
    field('obj_id', int, id=1),
    field('delta', int, id=2),
})

RpcMessage = make_union({
    1: CallRequest,
    2: CallResponse,
    3: FinalizeResponse,
    4: AdjustRefCount,
})

SerializedObject = make_record('SerializedObject', {
    field('own_id', int, id=1, default=None),
    field('remote_id', int, id=1, default=None),
})

class RpcSession:
    def __init__(self, on_message):
        self._on_message = on_message
        self._own_objects_by_obj = {}
        self._own_objects_by_id = {}
        self._next_own_object_id = 1
        self._remote_proxies: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        self._next_call_id = 1
        self._call_states = {}

    def message_received(self, data):
        msg = _RpcSerializer(self).unserialize(RpcMessage, data)
        if isinstance(msg, CallRequest):
            pass
        elif isinstance(msg, CallResponse):
            pass
        elif isinstance(msg, FinalizeResponse):
            pass
        elif isinstance(msg, AdjustRefCount):
            pass

    def call_with_cb(self, obj_id: int, method_id: int, params: serialize.AnyPayload, callback):
        call_id = self._next_call_id
        self._next_call_id += 1

        req = CallRequest(id=call_id, obj_id=obj_id, method_id=method_id, params=params)

        serializer = _RpcSerializer(self)
        serialized = serializer.serialize(RpcMessage, req)
        self._call_states[call_id] = _CallState(callback=callback, ref_count_incremented=serializer.ref_count_incremented)
        self._on_message(serialized)

@dataclasses.dataclass
class _CallState:
    ref_count_incremented: List[_OwnObject]
    callback: Callable

@dataclasses.dataclass
class _OwnObject:
    ref_count: int
    obj: Any

class _RemoteObjectProxy(rpc.RpcIface):
    def __init__(self, session, obj_id):
        self._session = session
        self._obj_id = obj_id

    def rpc_call(self, method_id, params):
        self._session.call(self._obj_id, method_id, params)

class _RpcSerializer(serialize.Serializer):
    def __init__(self, session):
        self.session = session
        self.ref_count_incremented = []

    def serialize(self, type_, value):
        if issubclass(type_, rpc.RpcIface):
            serialized_obj = self.session.serialize_obj(value)
            return super().serialize(SerializedObject, serialized_obj)
        else:
            return super().serialize(type_, value)

    def _serialize_obj(self, obj):
        if isinstance(obj, _RemoteObjectProxy):
            if obj._session != self.session:
                # we trivially could, by proxying the requests
                raise Exception('cannot serilize third party remote objects')

            return SerializedObject(remote_id=obj._obj_id)

        if obj in self.session._own_objects_by_obj:
            own_object = self.session._own_objects_by_obj[obj]
            own_object.ref_count += 1
            self.ref_count_incremented.append(own_object)
            return SerializedObject(own_id=id)

        id = self.session._next_own_object_id
        self.session._next_own_object_id += 1
        own_object = _OwnObject(obj=obj, ref_count=1)
        self.ref_count_incremented.append(own_object)
        self.session._own_objects_by_obj[obj] = own_object
        self.session._own_objects_by_id[id] = own_object

        return SerializedObject(own_id=id)

    def unserialize(self, type_, value):
        return super().serialize(type_, value)
