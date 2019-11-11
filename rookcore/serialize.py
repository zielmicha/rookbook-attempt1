import functools
from . import serialize_io

SERIALIZERS = {}
UNSERIALIZERS = {}

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

class AnyPayload:
    def unserialize(self, type_): assert False

class _BinaryPayload(AnyPayload):
    def __init__(self, serializer, data):
        self.serializer = serializer
        self.data = data

    def unserialize(self, type_):
        return self.serializer.unserialize(type_, self.data)

class TypedPayload(AnyPayload):
    def __init__(self, type_, value):
        self.type_ = type_
        self.value = value

    def unserialize(self, type_):
        if type_ != self.type_:
            raise TypeError('cannot unserialize %s as %s' % (self.type_, type_))

        return self.value

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

class Serializer:
    def serialize(self, type_, value):
        if type_ in SERIALIZERS:
            return SERIALIZERS[type_](value, self)

        if hasattr(type_, "_to_message"):
            message = type_._to_message(value, self) # type: ignore
            return serialize_io.write_message(message)

        raise Exception('cannot serialize %s' % type(value))

    def serialize_to_memoryview(self, type_, value):
        x = self.serialize(type_, value)
        if isinstance(x, bytes):
            return memoryview(x)
        else:
            return memoryview(x.getvalue())

    def unserialize(self, type_, value):
        assert isinstance(value, (memoryview, int)), value

        if type_ in UNSERIALIZERS:
            return UNSERIALIZERS[type_](value, self)

        if hasattr(type_, "_from_message"):
            msg = serialize_io.read_message(value)
            return type_._from_message(msg, self)

        raise Exception('cannot serialize %s' % type_)
