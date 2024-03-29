# Support for sending and observing reactive Refs over the RPC
from .record import *
from .serialize import *
from .common import *
from . import rpc, reactive, serialize, async_tools, rpc_session
import functools, asyncio, weakref

RefValue = make_record('RefValue', [
    field(id=1, name="current_value", type=AnyPayload),
    field(id=2, name="observable", type=lazy(lambda: ObservableIface)),
    field(id=3, name="is_writable", type=bool),
])

stabilise_requested = False

def stabilise_later():
    global stabilise_requested

    def do():
        global stabilise_requested
        stabilise_requested = False
        reactive.stabilise()

    if not stabilise_requested:
        stabilise_requested = True
        asyncio.get_event_loop().call_soon_threadsafe(do)

class ObserverIface(metaclass=rpc.RpcMeta):
    @rpc.rpcmethod(id=1)
    def value_changed(self, value: AnyPayload) -> None:
        pass

class ObservableIface(metaclass=rpc.RpcMeta):
    @rpc.rpcmethod(id=1)
    def observe(self, observer: ObserverIface) -> None:
        raise

    @rpc.rpcmethod(id=2)
    def stop_observing(self) -> None:
        pass

    @rpc.rpcmethod(id=3)
    def write(self, value: AnyPayload) -> None:
        pass

class ObservableImpl(ObservableIface):
    def __init__(self, value_type, current_value, ref):
        self.value_type = value_type
        self.ref = ref
        self.observer = None
        self.last_call_in_progress = None
        self.run_only_one = async_tools.RunOnlyOne()

    async def observe(self, observer):
        # we could avoid sending update now if another side already knows the state, but it seems a bit tricky
        self._changed(observer)

        self.observer = reactive.Observer(self.ref, functools.partial(self._changed, observer))

    async def stop_observing(self):
        if self.observer:
            self.observer.close()
        self.observer = None

    async def write(self, value: AnyPayload):
        v = value.unserialize(self.value_type)
        self.ref.value = v
        stabilise_later()

    def __del__(self):
        if getattr(self, 'observer', None):
            self.observer.close() # type: ignore

    def _changed(self, remote_observer):
        def f():
            return remote_observer.value_changed(value=TypedPayload(type_=self.value_type, value=self.ref.value))

        self.run_only_one.run(f)

_observable_cache_per_session: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()

def serialize_ref(args, value, serializer):
    ref = value
    value_type, = args
    current_value = ref.value

    assert isinstance(serializer, rpc_session._RpcSerializer)
    session = serializer.session
    observable_cache = _observable_cache_per_session.setdefault(session, weakref.WeakKeyDictionary())

    observable = observable_cache.get(ref)
    if observable is None:
        observable = ObservableImpl(value_type, current_value, ref)
        observable_cache[ref] = observable

    return serializer.serialize(
        type_=RefValue,
        value=RefValue(current_value=TypedPayload(type_=value_type, value=current_value),
                       is_writable=ref.is_writable,
                       observable=observable))

class ObserverImpl(ObserverIface):
    def __init__(self, value_type, custom_ref):
        self.value_type = value_type
        self.custom_ref = custom_ref

    async def value_changed(self, value):
        self.custom_ref.change_value(value.unserialize(self.value_type))
        stabilise_later()

_ref_cache: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()

def unserialize_ref(args, value, serializer):
    value_type, = args

    ref_value = serializer.unserialize(type_=RefValue, value=value)

    cache_key = ref_value.observable._rpc_remote_object
    cached_return = _ref_cache.get(cache_key)
    if cached_return is not None:
        return cached_return

    current_value = ref_value.current_value.unserialize(value_type)
    remote_observable = ref_value.observable

    # avoid unbounded memory use when RPC pipe is too slow
    write_runner = async_tools.RunOnlyOne()
    enabledisable_runner = async_tools.RunOnlyOne()

    def write_callback(value):
        write_runner.run(lambda: remote_observable.write(value=TypedPayload(value=value, type_=value_type)))

    def enable_callback():
        enabledisable_runner.run(lambda: remote_observable.observe(observer=ObserverImpl(value_type, custom_ref)))

    def disable_callback():
        enabledisable_runner.run(lambda: remote_observable.stop_observing())

    custom_ref = reactive.CustomRef(
        initial_value=current_value,
        write_callback=write_callback if ref_value.is_writable else None,
        enable_callback=enable_callback,
        disable_callback=disable_callback,
        # This is safe - morally, the references are created when the RPC system receives the
        # call, we just do it lazily.
        _allow_in_immutable_ctx=True
    )
    _ref_cache[cache_key] = custom_ref
    return custom_ref

serialize.GENERIC_SERIALIZERS[reactive.Ref] = serialize_ref
serialize.GENERIC_UNSERIALIZERS[reactive.Ref] = unserialize_ref
