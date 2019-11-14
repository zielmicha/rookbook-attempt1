import unittest
from .reactive import *

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

if __name__ == '__main__':
    unittest.main()
