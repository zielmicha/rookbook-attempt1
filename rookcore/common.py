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
