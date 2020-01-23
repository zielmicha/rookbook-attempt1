from .reactive import CustomRef
from .serialize import *
from .common import *
import os, weakref

def _make_default(type_):
    return type_() # TODO

def _load_value(type_, path):
    if not os.path.exists(path):
        return _make_default(type_)
    else:
        with open(path, 'rb') as f: data = f.read()

        return Serializer().unserialize_from_bytes(value=data, type_=type_)

def _write_value(type_, value, path):
    data = Serializer().serialize_to_memoryview(value=value, type_=type_)
    replace_file(path, data)

_file_based_ref_cache: weakref.WeakValueDictionary = weakref.WeakValueDictionary()

def make_file_based_ref(type_, path):
    initial_value = _load_value(type_, path)

    def write_callback(value):
        _write_value(type_, value, path)

    ref = _file_based_ref_cache.get(path) # not ideal?
    if ref is None:
        ref = CustomRef(initial_value=initial_value,
                        write_callback=write_callback,
                        _allow_in_immutable_ctx=True)
        _file_based_ref_cache[path] = ref
    return ref
