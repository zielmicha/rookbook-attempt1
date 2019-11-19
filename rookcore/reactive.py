'''
>>> x = VarRef(1)
>>> y = VarRef(2)
>>> z = reactive(lambda: x.value + y.value + x.value)
>>> z.value
4
>>> len(z._depends)
2
>>> assert not x._enabled
>>> z_observer = Observer(z)
>>> x.value = 0
>>> stabilise()
>>> z.value
2

>>> use_x = VarRef(False)
>>> x_0 = VarRef(1)
>>> x = reactive(lambda: x_0.value)
>>> z = reactive(lambda: x.value if use_x.value else 5)
>>> z_observer = Observer(z)
>>> z._height
1
>>> use_x.value = True
>>> stabilise()
>>> x._height
1
>>> z._height
2
'''

from typing import *
import threading, weakref, functools, collections, heapq
from abc import ABCMeta, abstractproperty
try:
    import cython
except ImportError:
    from . import fake_cython as cython

T = TypeVar('T')

_thread_local = threading.local()

class _thread_state:
    pass

def _get_thread_local():
    if cython.compiled:
        assert _thread_local_c != cython.NULL # type: ignore
        return cython.cast(_thread_state, _thread_local_c) # type: ignore
    else:
        return _thread_local # type: ignore

_set_vars = {}

def init_thread_local():
    if cython.compiled:
        global _thread_local_c
        _thread_local.state = _thread_state()
        _thread_local_c = cython.cast(cython.p_void, _thread_local.state) # type: ignore
    _get_thread_local().ref_enabled = None
    _get_thread_local().immutable_ctx = False
    _get_thread_local().record_lookups = None

init_thread_local()

class Ref(Generic[T]):
    @property
    def value(self):
        raise Exception('not supported')

class _BaseRef:
    def __init__(self):
        self._rdepends = set()
        self._depends = set()
        self._height = 0
        self._enabled = False

    @cython.locals(d='_BaseRef')
    def _enable_internal(self):
        self._enabled = True
        for d in self._depends:
            # We start depending on `d`. This might enable `d` and change its height.
            d.__add_rdepend(self)
            self._height = max(self._height, d._height + 1)

    def _enable(self):
        assert not self._enabled
        ref_enabled = _get_thread_local().ref_enabled
        if ref_enabled is not None: ref_enabled.append(self)

        self._enable_internal()

    @cython.locals(d='_BaseRef')
    def _disable(self):
        self._enabled = False
        for d in self._depends:
            d.__remove_rdepend(self)

    def __add_rdepend(self, val):
        # `val` starts depending on us
        enabling = len(self._rdepends) == 0
        self._rdepends.add(val)
        if enabling:
            self._enable()

    def __remove_rdepend(self, val):
        self._rdepends.remove(val)
        if len(self._rdepends) == 0:
            self._disable()

    def _set_depends(self, new_depends):
        if self._depends != new_depends:
            enabled = self._enabled
            if enabled: self._disable()
            self._depends = new_depends
            if enabled: self._enable_internal()

    def _record_read(self):
        record_lookups = _get_thread_local().record_lookups
        if record_lookups is not None:
            record_lookups.add(self)

    def _refresh(self):
        pass

class _QueueItem:
    priority: int
    value: object

    def __lt__(self, other: '_QueueItem'):
        return self.priority < other.priority

class _OnceQueue:
    '''
    >>> x = _OnceQueue()
    >>> x.add(2, "foo", False)
    >>> x.add(2, "foo", False)
    >>> x.add(1, "bar", False)
    >>> assert x
    >>> x.pop()
    'bar'
    >>> x.pop()
    'foo'
    >>> assert not x
    '''

    def __init__(self):
        self.queue: list = []
        self.added = set()

    def add(self, priority, value, force):
        if force or value not in self.added:
            item = _QueueItem()
            item.value = value
            item.priority = priority
            heapq.heappush(self.queue, item)
            self.added.add(value)

    def pop(self):
        item: _QueueItem = heapq.heappop(self.queue)
        return item.value

    def __bool__(self):
        return bool(self.queue)

@cython.locals(x=_BaseRef, item=_BaseRef)
def stabilise():
    # zielmicha:
    # This is extremly tricky. At some point I should write a formal proof of its behaviour.
    # (good randomized test would be even better)
    enabled_ref: list = []
    _get_thread_local().ref_enabled = enabled_ref

    queue = _OnceQueue()
    for x in _set_vars: queue.add(x._height, x, force=False)

    while queue:
        item = queue.pop()
        old_value = item._value
        item._refresh()

        if enabled_ref:
            for x in enabled_ref:
                queue.add(x._height, x, force=False)
            enabled_ref[:] = []
            queue.add(item._height, item, force=True)

        if old_value != item._value:
            for x in item._rdepends:
                queue.add(x._height, x, force=False)

    _get_thread_local().ref_enabled = None
    _set_vars.clear()

class VarRef(_BaseRef):
    def __init__(self, value):
        super().__init__()
        # it's too easy to cause infinite loops in `stabilise` by making new VarRefs in reactive contexts
        assert not _get_thread_local().immutable_ctx
        self._value = value

    @property
    def value(self):
        self._record_read()
        return self._value

    @value.setter
    def value(self, x):
        assert self._enabled
        assert not _get_thread_local().immutable_ctx
        _set_vars[self] = x

    def _refresh(self):
        if self in _set_vars:
            self._value = _set_vars[self]

    def __repr__(self):
        return 'VarRef(%s)' % (self._value)

class ReactiveRef(_BaseRef):
    def __init__(self, refresh_f):
        super().__init__()
        self._exception = None
        self._refresh_f = refresh_f
        self._refresh()

    def _refresh(self):
        self._exception, self._value, new_depends = self._refresh_f()
        if self._exception is not None:
            self._value = object() # unique value every time

        self._set_depends(new_depends)

    @property
    def value(self):
        self._record_read()
        if self._exception is not None:
            raise self._exception
        else:
            return self._value

    def __repr__(self):
        if self._exception:
            v = '<Error: %r>' % self._exception
        else:
            v = repr(self._value)

        return 'ReactiveRef(%x %s)' % (id(self), v)

class Observer(_BaseRef):
    def __init__(self, ref, callback=lambda: None):
        super().__init__()
        self._callback = callback
        self._depends = {ref}
        self._ref = ref
        self._enable()
        self._value = None

    def __enter__(self):
        pass

    def __exit__(self):
        self.close()

    def close(self):
        self._disable()

    def _refresh(self):
        self._callback()

    def __repr__(self):
        return '<Observer of %r>' % self._ref

def const_ref(value):
    # TODO: block setter
    return VarRef(value)

def reactive_property(f):
    def wrapper(self):
        name = '_reactive__' + f.__name__
        r = getattr(self, name, None)
        if not r:
            r = reactive(functools.partial(f, self))
            setattr(self, name, r)
        return r

    return property(wrapper)

class ReactiveDictMap:
    # If items would not depend on self.dict_ref we could avoid loops in many cases.
    # Then only KeyError needs to be handled specially.
    def __init__(self, dict_ref, f):
        self.dict_ref = dict_ref
        self.f = f
        # zielmicha: Is WeakValueDictionary actually safe here?
        self._refs: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
        #self._refs = {}

    def __getitem__(self, key):
        r = self._refs.get(key)
        if not r:
            def get():
                res = self.dict_ref.value[key]
                return self.f(res)

            r = reactive(get)
            self._refs[key] = r

        return r

    def keys(self):
        return self.dict_ref.value.keys()

    def __iter__(self):
        return iter(self.keys())

def reactive_dict_map(f: Callable, ref: _BaseRef):
    return ReactiveDictMap(ref, f)

def _record_lookups(f):
    record_lookups_prev = _get_thread_local().record_lookups
    immutable_ctx_prev = _get_thread_local().immutable_ctx
    record_lookups: Set[Any] = set()
    _get_thread_local().record_lookups = record_lookups
    _get_thread_local().immutable_ctx = True
    exception = None
    result = None
    try:
        result = f()
    except Exception as exc:
        exception = exc
    finally:
        _get_thread_local().record_lookups = record_lookups_prev
        _get_thread_local().immutable_ctx = immutable_ctx_prev

    return exception, result, record_lookups

def reactive(f):
    r = ReactiveRef(functools.partial(_record_lookups, f))
    return r
