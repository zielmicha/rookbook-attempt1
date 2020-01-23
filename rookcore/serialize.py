import functools, typing
from . import serialize_io, record

SERIALIZERS = {}
UNSERIALIZERS = {}

GENERIC_SERIALIZERS = {}
GENERIC_UNSERIALIZERS = {}

def register_serializer(t):
    def f(v): SERIALIZERS[t] = v
    return f

def register_unserializer(t):
    def f(v): UNSERIALIZERS[t] = v
    return f

def expect_varint(value):
    assert isinstance(value, int), "found packed value where varint expected"

def expect_packed(value):
    assert isinstance(value, memoryview), "found varint value where packed expected"

@register_serializer(int)
def serialize_int(value, serializer):
    return serialize_io.int_to_uint(value)

@register_unserializer(int)
def unserialize_int(value, unserializer):
    expect_varint(value)
    return serialize_io.uint_to_int(value)

@register_serializer(bool)
def serialize_bool(value, serializer):
    return 1 if value else 0

@register_unserializer(bool)
def unserialize_bool(value, unserializer):
    expect_varint(value)
    return value != 0

@register_serializer(bytes)
def serialize_bytes(value, serializer):
    return value

@register_unserializer(bytes)
def unserialize_bytes(value, serializer):
    expect_packed(value)
    return bytes(value)

@register_serializer(str)
def serialize_str(value, serializer):
    return value.encode('utf8')

@register_unserializer(str)
def unserialize_str(value, serializer):
    expect_packed(value)
    return bytes(value).decode('utf8')

@register_serializer(type(None))
def serialize_none(value, serializer):
    return 0

@register_unserializer(type(None))
def unserialize_none(value, serializer):
    return None

def assert_is_serializable_type(t):
    return isinstance(t, type)

class AnyPayload:
    def unserialize(self, type_): assert False

class _BinaryPayload(AnyPayload):
    def __init__(self, serializer, data):
        self.serializer = serializer
        self.data = data

    def unserialize(self, type_):
        return self.serializer.unserialize(type_, self.data)

    def __repr__(self):
        return '_BinaryPayload(%r, %r)' % (self.serializer, bytes(self.data))

class TypedPayload(AnyPayload):
    def __init__(self, type_, value):
        assert_is_serializable_type(type_)
        assert record.isinstance_plus(value, type_), (type_, value)
        self.type_ = type_
        self.value = value

    def unserialize(self, type_):
        if type_ != self.type_:
            raise TypeError('cannot unserialize %s as %s' % (self.type_, type_))

        return self.value

    def __repr__(self):
        return 'TypedPayload(%r, %r)' % (self.type_, self.value)

@register_serializer(AnyPayload)
def serialize_any_payload(value, serializer):
    if isinstance(value, _BinaryPayload):
        return value.data
    elif isinstance(value, TypedPayload):
        return serializer.serialize(value.type_, value.value)
    else:
        raise TypeError(type(value))

@register_unserializer(AnyPayload)
def unserialize_any_payload(value, serializer):
    return _BinaryPayload(serializer=serializer, data=value)

def serialize_generic_list(args, value, serializer):
    subtype, = args
    return serialize_io.write_message([ (0, serializer.serialize(type_=subtype, value=v)) for v in value ])

def unserialize_generic_list(args, value, serializer):
    subtype, = args
    msg = serialize_io.read_message(value)
    return [ serializer.unserialize(type_=subtype, value=v) for i, v in msg if i == 0 ]

GENERIC_SERIALIZERS[typing.List] = serialize_generic_list
GENERIC_UNSERIALIZERS[typing.List] = unserialize_generic_list
GENERIC_SERIALIZERS[list] = serialize_generic_list
GENERIC_UNSERIALIZERS[list] = unserialize_generic_list

class Serializer:
    def serialize(self, type_, value):
        if type_ in SERIALIZERS:
            return SERIALIZERS[type_](value, self)

        if hasattr(type_, "_to_message"):
            message = type_._to_message(value, self) # type: ignore
            return serialize_io.write_message(message)

        if getattr(type_, '__origin__', None) in GENERIC_SERIALIZERS:
            return GENERIC_SERIALIZERS[getattr(type_, '__origin__')](type_.__args__, value, self)

        raise Exception('cannot serialize type=%s value=%s' % (type_, type(value)))

    def serialize_to_memoryview(self, type_, value):
        x = self.serialize(type_, value)
        if isinstance(x, bytes):
            return memoryview(x)
        elif isinstance(x, int):
            return memoryview(serialize_io.write_uint(x))
        else:
            return memoryview(x.getvalue())

    def unserialize(self, type_, value):
        assert isinstance(value, (memoryview, int)), value

        if type_ in UNSERIALIZERS:
            return UNSERIALIZERS[type_](value, self)

        if hasattr(type_, "_from_message"):
            msg = serialize_io.read_message(value)
            return type_._from_message(msg, self)

        if getattr(type_, '__origin__', None) in GENERIC_UNSERIALIZERS:
            return GENERIC_UNSERIALIZERS[getattr(type_, '__origin__')](type_.__args__, value, self)

        raise Exception('cannot unserialize %s (origin: %s)' % (type_, getattr(type_, '__origin__', None)))

    def unserialize_from_bytes(self, type_, value):
        if isinstance(value, bytes):
            value = memoryview(value)

        if isinstance(value, memoryview) and isinstance(type_, (int, bool)):
            length, value_n = serialize_io.read_uint(value)
            if length != len(value): raise Exception('invalid value (too long)')
            value = value_n

        return self.unserialize(type_=type_, value=value)
