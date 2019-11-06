from typing import *
from .record import *
from . import serialize
import weakref, dataclasses

CallRequest = make_record('CallRequest', [
    field('id', int, id=1),
    field('obj_id', int, id=2),
    field('method_id', int, id=3),
    field('args', serialize.AnyPayload, id=4),
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

class RpcSession:
    def __init__(self, on_message):
        self._on_message = on_message
        self._own_objects = {}
        self._remote_proxies: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        self._next_call_id = 1

    def _send(self, msg):
        self._on_message(_RpcSerializer(self).serialize(RpcMessage, msg))

    def message_received(self, data):
        pass

    def call(self, obj_id: int, method_id: int, args: serialize.AnyPayload):
        call_id = self._next_call_id
        self._next_call_id += 1

        req = CallRequest(id=call_id, obj_id=obj_id, method_id=method_id, args=args)
        self._send(req)

@dataclasses.dataclass
class _OwnObject:
    ref_count: int
    obj: Any

class _RemoteObjectProxy:
    def __init__(self, session, obj_id):
        self._session = session
        self._obj_id = obj_id

class _RpcSerializer(serialize.Serializer):
    def __init__(self, session):
        self.session = session

    def serialize(self, type_, value):
        pass

    def unserialize(self, type_, value):
        pass
