from typing import *
from .record import *
from .common import Bijection
from . import serialize, rpc
import weakref, dataclasses, functools, asyncio, traceback, sys

CallRequest = make_record('CallRequest', [
    field('id', int, id=1),
    field('obj_id', int, id=2),
    field('method_id', int, id=3),
    field('params', serialize.AnyPayload, id=4),
])

CallResponse = make_record('CallResponse', {
    field('id', int, id=1),
    field('is_error', bool, default=False, id=2),
    field('value', serialize.AnyPayload, id=3),
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
    def __init__(self, root_object, on_message):
        self._on_message = on_message
        self._own_objects_by_obj: dict = {}
        self._own_objects_by_id: dict = {}
        self._next_own_object_id = 2
        self._remote_proxies: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        self._next_call_id = 1
        self._call_states = {}
        self._response_states = {}

        o = _OwnObject(id=1, ref_count=1, obj=root_object)
        self._own_objects_by_obj[root_object] = o
        self._own_objects_by_id[1] = o

    def message_received(self, data):
        msg = _RpcSerializer(self).unserialize(RpcMessage, data)
        if isinstance(msg, CallRequest):
            obj = self._own_objects_by_id[msg.obj_id]

            self._run_call(obj, msg.method_id, msg.params, functools.partial(self._send_call_response, msg.id))
        elif isinstance(msg, CallResponse):
            call_state = self._call_states[msg.id]

            for own_object in call_state.ref_count_incremented: self._decref(own_object)
            call_state.callback(msg.is_error, msg.value)

            finalize_msg = FinalizeResponse(id=msg.id)
            self._on_message(serialize.Serializer().serialize_to_memoryview(RpcMessage, finalize_msg))
        elif isinstance(msg, FinalizeResponse):
            for own_object in self._response_states[msg.id]:
                self._decref(own_object)
        elif isinstance(msg, AdjustRefCount):
            own_object = self._own_objects_by_id[msg.id]

            if msg.delta == 1:
                own_object.ref_count += 1
            elif msg.delta == -1:
                self._decref(own_object)
            else:
                raise Exception('invalid delta')

    def _run_call(self, obj, method_id, params, callback):
        asyncio.ensure_future(obj.obj.rpc_call(method_id, params)).add_done_callback(_print_errors(callback))
        #r = obj.obj.rpc_call(method_id, params)
        #callback('foo')

    def _send_call_response(self, call_id, result):
        exc = result.exception()
        if exc is None:
            assert isinstance(result.result(), serialize.AnyPayload)
            response = CallResponse(id=call_id, value=result.result())
        else:
            sys.stderr.write('Error in RPC call:\n')
            result.print_stack()
            response = CallResponse(id=call_id, is_error=True,
                                    value=serialize.TypedPayload(type_=str, value='%s: %s' % (type(exc).__name__, exc)))

        serializer = _RpcSerializer(self)
        serialized = serializer.serialize_to_memoryview(RpcMessage, response)
        self._response_states[call_id] = serializer.ref_count_incremented
        self._on_message(serialized)

    def _decref(self, own_object):
        own_object.ref_count -= 1
        if own_object.ref_count == 0:
            del self._own_objects_by_id[own_object.id]
            del self._own_objects_by_obj[own_object.obj]

    def call_with_cb(self, obj_id: int, method_id: int, params: serialize.AnyPayload, callback):
        call_id = self._next_call_id
        self._next_call_id += 1

        req = CallRequest(id=call_id, obj_id=obj_id, method_id=method_id, params=params)

        serializer = _RpcSerializer(self)
        serialized = serializer.serialize_to_memoryview(RpcMessage, req)
        self._call_states[call_id] = _CallState(callback=callback, ref_count_incremented=serializer.ref_count_incremented)
        self._on_message(serialized)

@dataclasses.dataclass
class _OwnObject:
    id: int
    ref_count: int
    obj: Any

@dataclasses.dataclass
class _CallState:
    ref_count_incremented: List[_OwnObject]
    callback: Callable

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
        own_object = _OwnObject(obj=obj, ref_count=1, id=id)
        self.ref_count_incremented.append(own_object)
        self.session._own_objects_by_obj[obj] = own_object
        self.session._own_objects_by_id[id] = own_object

        return SerializedObject(own_id=id)

    def unserialize(self, type_, value):
        return super().unserialize(type_=type_, value=value)

def _print_errors(f):
    def wrapper(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except Exception:
            traceback.print_exc()
            raise

    return wrapper
