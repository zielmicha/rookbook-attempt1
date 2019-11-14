import unittest, uuid
from . import core, base_cells
from rookcore.common import *
from rookcore.reactive import reactive, stabilise, VarRef, Observer

class BookTest(unittest.TestCase):
    def test_simple(self):
        cells = VarRef(frozendict({}))
        book = core.Book(cell_types=base_cells.cell_types, cell_sources=cells)

        o = Observer(book.require_all_values)

        cells.value = frozendict(cells.value, **{
            '02a4729c-66cd-4966-83d2-abcf813fc6c7': '%val x = 5',
            '46e3ec0c-2488-4f16-ab35-68b6fd4f12cb': '%val z = x + 1'
        })
        stabilise()

        self.assertEquals(book.ns['x'], 5)
        self.assertEquals(book.ns['z'], 6)
        cells.value = frozendict(cells.value,
                                 **{'46e3ec0c-2488-4f16-ab35-68b6fd4f12cb': '%val x = 6'})
        stabilise()

        self.assertEquals(book.ns['x'], 6)
        self.assertEquals(book.ns['z'], 7)

if __name__ == '__main__':
    unittest.main()
