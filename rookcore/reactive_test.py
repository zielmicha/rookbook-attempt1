import unittest
from .reactive import *
from .common import *

class ReactiveTest(unittest.TestCase):
    def test_exc(self):
        z = reactive(lambda: 1/0)

        try:
            z.value
        except ZeroDivisionError: pass
        else: assert False

        should_raise = VarRef(False)
        z = reactive(lambda: 1/0 if should_raise.value else 1)
        o = Observer(z)
        z.value
        stabilise()

        should_raise.value = True
        stabilise()

        try:
            z.value
        except ZeroDivisionError: pass
        else: assert False

        z1 = reactive(lambda: z.value + 1)
        o1 = Observer(z1)
        try:
            z1.value
        except ZeroDivisionError: pass
        else: assert False

        should_raise.value = False
        stabilise()
        self.assertEqual(z1.value, 2)

    def test_dict_map(self):
        d = VarRef(frozendict())
        dinc = reactive_dict_map(ref=d, f=lambda x: x+1)

        x = dinc['x']
        o = Observer(x)
        stabilise()

        d.value = frozendict(x=5)
        stabilise()
        self.assertEqual(x.value, 6)

    def test_suprising_enable(self):
        src = VarRef(5)
        src_dup = reactive(lambda: str(src.value))
        fin = reactive(lambda: src_dup.value if src.value != 5 else None)

        o = Observer(fin)
        stabilise()
        self.assertEqual(src_dup.value, "5")
        self.assertEqual(fin.value, None)
        src.value = 6
        stabilise()
        self.assertEqual(src_dup.value, "6")
        self.assertEqual(fin.value, "6")

if __name__ == '__main__':
    unittest.main()
