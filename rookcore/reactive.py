'''
>>> x = VarRef(1)
>>> y = VarRef(2)
>>> z = reactive(lambda: x.value + y.value + x.value)
>>> z.value
4
>>> len(z._depends)
2
>>> x.value = 0
>>> assert not x._enabled
>>> z_observer = Observer(z)
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

_thread_local = threading.local()
_set_vars = {}

class _BaseRef:
    def __init__(self):
        self._rdepends = set()
        self._depends = set()
        self._height = 0
        self._enabled = False

    def _enable(self):
        self._enabled = True
        for d in self._depends:
            # We start depending on `d`. This might enable `d` and change its height.
            d.__add_rdepend(self)
            self._height = max(self._height, d._height + 1)

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
            if enabled: self._enable()

    def _record_read(self):
        record_lookups = getattr(_thread_local, 'record_lookups', None)
        if record_lookups is not None:
            record_lookups.add(self)

class _OnceQueue:
    '''
    >>> x = _OnceQueue()
    >>> x.add(2, "foo")
    >>> x.add(2, "foo")
    >>> x.add(1, "bar")
    >>> assert x
    >>> x.pop()
    'bar'
    >>> x.pop()
    'foo'
    >>> assert not x
    '''

    def __init__(self):
        self.queue: List[Any] = []
        self.added = set()

    def add(self, priority, item):
        if item not in self.added:
            heapq.heappush(self.queue, (priority, item))
            self.added.add(item)

    def pop(self):
        _, x = heapq.heappop(self.queue)
        return x

    def __bool__(self):
        return bool(self.queue)

def stabilise():
    queue = _OnceQueue()
    for x in _set_vars: queue.add(x._height, x)

    while queue:
        item = queue.pop()
        old_value = item._value
        item._refresh()
        if old_value != item._value:
            for x in item._rdepends:
                queue.add(x._height, x)

    _set_vars.clear()

class VarRef(_BaseRef):
    def __init__(self, value):
        super().__init__()
        self._value = value

    @property
    def value(self):
        self._record_read()
        return self._value

    @value.setter
    def value(self, x):
        assert not getattr(_thread_local, '_immutable_ctx', False)
        _set_vars[self] = x

    def _refresh(self):
        self._value = _set_vars[self]

class ReactiveRef(_BaseRef):
    def __init__(self, refresh_f):
        super().__init__()
        self._refresh_f = refresh_f
        self._refresh()

    def _refresh(self):
        self._value, new_depends = self._refresh_f()
        self._set_depends(new_depends)

    @property
    def value(self):
        self._record_read()
        return self._value

class Observer(_BaseRef):
    def __init__(self, ref, callback=lambda: None):
        super().__init__()
        self._callback = callback
        self._depends = {ref}
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

def _record_lookups(f):
    record_lookups_prev = getattr(_thread_local, 'record_lookups', None)
    immutable_ctx_prev = getattr(_thread_local, 'immutable_ctx', False)
    record_lookups: Set[Any] = set()
    _thread_local.record_lookups = record_lookups
    _thread_local.immutable_ctx = True
    try:
        result = f()
    finally:
        _thread_local.record_lookups = record_lookups_prev
        _thread_local.immutable_ctx = immutable_ctx_prev

    return result, record_lookups

def reactive(f):
    r = ReactiveRef(functools.partial(_record_lookups, f))
    return r
