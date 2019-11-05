from typing import *

class Lazy:
    def __init__(self, f):
        self._f = f

    def get(self):
        if hasattr(self, '_value'):
            return self._value # type: ignore
        else:
            self._value = self._f()
            del self._f
            return self._value

    @staticmethod
    def maybe_unwrap(l):
        if isinstance(l, Lazy):
            return l.get()
        else:
            return l

    def __repr__(self):
        if hasattr(self, '_value'):
            return '<Lazy %r>' % self._value
        else:
            return '<Lazy>'

def lazy(f: Callable):
    return Lazy(f=f)

def dict_multi(pairs):
    result: Dict = {}
    for k, v in pairs:
        if k not in result:
            result[k] = []
        result[k].append(v)

    return result

def _frozen_exc():
    raise Exception('attempting to modify frozen structure')

class frozenlist(list):
    def __setitem__(self, i, val):
        _frozen_exc()

    def __delitem__(self, i):
        _frozen_exc()

    def reverse(self):
        _frozen_exc()

    def insert(self, i, x):
        _frozen_exc()

    def append(self, x):
        _frozen_exc()

    def sort(self, *args, **kwargs):
        _frozen_exc()

    def pop(self, i=None):
        _frozen_exc()

    def remove(self, x):
        _frozen_exc()

    def extend(self, l):
        _frozen_exc()

    def __iadd__(self, l): # type: ignore
        _frozen_exc()

    def __hash__(self):
        return hash(tuple(self))

class frozendict(dict):
    def __setitem__(self, i, val):
        _frozen_exc()

    def __delitem__(self, i):
        _frozen_exc()

    def update(self, i):
        _frozen_exc()

    def __hash__(self):
        return hash(tuple(self.items()))

    # TODO: other APIs
