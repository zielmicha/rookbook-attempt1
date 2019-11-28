import unittest, sqlite3
from typing import *
from .common import *
from .record import *
from . import serialize, sqlite_table

FooRow = make_record('FooRow', [
    field('id', int, id=1),
    field('val1', int, id=3),
    field('val2', str, id=2)])

class SqliteTableTest(unittest.TestCase):
    def test_roundtrips(self):
        conn = sqlite3.connect(':memory:')

        tbl = sqlite_table.SqliteTable(conn, 'tbl', FooRow)
        tbl._insert(FooRow(id=1, val1=5, val2='xoo'))
        self.assertEqual(tbl.filter_noreactive(), [FooRow(id=1, val1=5, val2='xoo')])

        tbl = sqlite_table.SqliteTable(conn, 'tbl', FooRow)
        self.assertEqual(tbl.filter_noreactive(), [FooRow(id=1, val1=5, val2='xoo')])

class ReactiveTableTest(unittest.TestCase):
    def test_roundtrips(self):
        conn = sqlite3.connect(':memory:')

        tbl = sqlite_table.SqliteTable(conn, 'tbl', FooRow)
        tbl._insert(FooRow(id=1, val1=5, val2='xoo'))
        self.assertEqual(tbl.filter_noreactive(), [FooRow(id=1, val1=5, val2='xoo')])

        tbl = sqlite_table.SqliteTable(conn, 'tbl', FooRow)
        self.assertEqual(tbl.filter_noreactive(), [FooRow(id=1, val1=5, val2='xoo')])

if __name__ == '__main__':
    unittest.main()
