import unittest
from typing import *
from .common import *
from .record import *
from . import serialize

StringList = make_record('StringList', [
    field('head', str, id=1),
    field('tail', lazy(lambda: StringList), id=2, default=None)]) # type: ignore

StringOrInt = make_union({
    1: int,
    2: str
})

class SerializeTest(unittest.TestCase):
    def test_roundtrips(self):
        self.roundtrip('fooą')
        self.roundtrip(b'foo')
        self.roundtrip(StringList(head="foo", tail=None))

        curr = None
        for i in range(10):
            curr = StringList(head='%d' % i, tail=curr)
            self.roundtrip(curr)

        self.roundtrip('foo', StringOrInt)
        self.roundtrip(5, StringOrInt)
        assert isinstance(5, StringOrInt)

    def roundtrip(self, x, t=None):
        t = type(x) if t is None else t
        data = serialize.Serializer().serialize_to_memoryview(t, x)
        r = serialize.Serializer().unserialize(t, data)
        self.assertEqual(x, r)

if __name__ == '__main__':
    unittest.main()
