from typing import *
from .common import *
import operator
import collections

__all__ = ['make_record', 'field', 'make_union']

class _Field(NamedTuple):
    name: str
    type: Any
    id: int
    default: Any

MISSING = object()

class BaseRecord:
    @classmethod
    def _from_message(cls, msg, serializer):
        assert type(msg) == list
        msg_dict = dict_multi(msg)
        result: Dict = {}

        for field in cls._fields: # type: ignore
            values = msg_dict.get(field.id, [])

            type_ = Lazy.maybe_unwrap(field.type)
            origin_type = getattr(type_, '__origin__', None)
            if origin_type == List:
                subtype, = type_.__args__
                result[field.name] = [ serializer.unserialize(v, subtype) for v in values ]
            else:
                if len(values) == 0:
                    if field.default == MISSING:
                        raise Exception('missing value for field %r' % field)
                    else:
                        result[field.name] = field.default
                else:
                    result[field.name] = serializer.unserialize(type_=type_, value=values[0])

        return cls(**result) # type: ignore

    def _to_message(self, serializer):
        msg = []
        for field in self._fields: # type: ignore
            value = getattr(self, field.name)
            type_ = Lazy.maybe_unwrap(field.type)
            origin_type = getattr(type_, '__origin__', None)

            if origin_type == List:
                subtype, = type_.__args__
                assert isinstance(value, (list, tuple))
                for item in value:
                    msg.append((field.id, serializer.serialize(subtype, item)))
            else:
                if value is None and field.default is None:
                    pass
                else:
                    msg.append((field.id, serializer.serialize(type_, value)))

        return msg

    def _to_dict(self):
        return { field.name:getattr(self, field.name) for field in self._fields } # type: ignore

def make_record(name, fields):
    fields = tuple(sorted(fields, key=lambda f: f.id))

    dict: Dict[str, Any] = {}
    dict['__slots__'] = tuple( '_F' + field.name for field in fields )
    for field in fields:
        dict[field.name] = property(operator.attrgetter('_F' + field.name))

    dict['_fields'] = fields

    for field in fields:
        if isinstance(field.type, Lazy):
            dict[f'_T{field.name}'] = staticmethod(field.type.get)
        else:
            dict[f'_T{field.name}'] = (lambda t: staticmethod(lambda: t))(field.type)

    exec('def __init__(self, *, %s):\n  %s' % (
        ', '.join( field.name for field in fields),
        '\n  '.join( f'if {field.name} is not None and not isinstance({field.name}, self._T{field.name}()): raise TypeError("field {field.name} should have type {field.type}, not %s" % type({field.name}))\n  self._F{field.name} = {field.name}' for field in fields)), dict)

    exec('def __hash__(self):\n  return hash((%s, ))' % (
        ', '.join( field.name for field in fields)), dict)

    exec('def __eq__(self, other):\n  return self is other or (type(self) == type(other) and %s)' % (
        ' and '.join( f'self.{field.name} == other.{field.name}' for field in fields )), dict)

    exec('def __repr__(self):\n  return "%s(%s)" %% (%s)' % (
        name,
        ', '.join( '%s=%%r' % (field.name) for field in fields ),
        ', '.join( 'self.%s' % (field.name) for field in fields ),
    ), dict)

    exec('def __str__(self): return repr(self)', dict)

    return type(name, (BaseRecord,), dict)

def field(name: str, type: Any, id: int, default=MISSING):
    return _Field(name=name, type=type, id=id, default=default)

class _Union(type):
    by_id: Dict[int, Any]
    by_type: Dict[Any, int]

    def __subclasshook__(self, t):
        return t in self.by_type

    def __instancecheck__(self, t):
        return type(t) in self.by_type

    def _to_message(self, value, serializer):
        type_ = type(value)
        id = self.by_type[type_]
        return [(id, serializer.serialize(type_, value))]

    def _from_message(self, msg, serialize):
        for id, value in msg:
            if id in self.by_id:
                return serialize.unserialize(self.by_id[id], value)

        raise Exception('unknown Union member')

def make_union(types):
    by_id: Dict[int, Any] = {}
    by_type: Dict[Any, int] = {}

    for id, type_ in types.items():
        assert type(id) == int
        if id in by_id:
            raise Exception('duplicate id %d' % id)
        by_id[id] = type_

        if type_ in by_type:
            raise Exception('duplicate type %s' % type_)
        by_type[type_] = id

    return _Union('Union', (), dict(by_id=by_id, by_type=by_type))
