from .reactive import reactive, VarRef
from .common import *
from .record import *
from .table import Table
from . import serialize
import sqlite3, string

allowed_table_name_letters = string.ascii_lowercase + string.ascii_uppercase + string.digits + '_'

class SqliteTable(Table):
    def __init__(self, conn, table_name, row_type):
        super().__init__(row_type)
        self.conn = conn
        if not all( ch in allowed_table_name_letters for ch in table_name ):
            raise ValueError('invalid table name %r' % table_name)
        self.table_name = table_name
        self.__fields_by_name = { field.name:field for field in self._fields }
        self._init_sql()

    def _init_sql(self):
        r = list(self.conn.execute('select sql from sqlite_master where name = ?', (self.table_name, )))
        current_field_ids = [ field.id for field in self._fields ]

        if r:
            # e.g. "CREATE TABLE xx (id int primary key, f1 blob, f2 blob)"
            sql, = r[0]
            assert sql.startswith('CREATE TABLE ')

            fields = sql.split('(')[1].strip(')').split(', ')
            used_field_ids = [ int(f.split()[0][1:]) for f in fields if f.startswith('f') ]

            missing_ids = set(current_field_ids) - set(used_field_ids)

            # TODO: handle defaults!
            for id in missing_ids:
                self.conn.execute('ALTER TABLE %s ADD COLUMN f%d BLOB;' % (self.table_name, id))
        else:
            fields = ['id INTEGER PRIMARY KEY'] + [ ('f%d BLOB' % i) for i in current_field_ids ]
            self.conn.execute('CREATE TABLE %s (%s);' % (self.table_name, ', '.join(fields)))

    def __getattr_serialized(self, row, field):
        serializer = serialize.Serializer()
        return serializer.serialize(value=getattr(row, field.name), type_=field.type)

    def __unserialize_row(self, row):
        serializer = serialize.Serializer()

        return self.row_type(id=row[0], **{
            field.name:serializer.unserialize_from_bytes(type_=field.type, value=value)
            for value, field in zip(row[1:], self._fields) })

    def _update(self, row):
        self.conn.execute('UPDATE %s SET %s WHERE id = ?' %
                          (self.table_name, ', '.join([ f'f{f.id} = ?' for f in self._fields ])),
                          (row.id,) + tuple( self.__getattr_serialized(row, f) for f in self._fields ))

    def _insert(self, row):
        self.conn.execute('INSERT INTO %s (%s) VALUES (%s)' %
                          (self.table_name,
                           ', '.join([ f'f{f.id}' for f in self._fields ]),
                           ', '.join(['?'] * (len(self._fields)))),
                          tuple( self.__getattr_serialized(row, f) for f in self._fields ))

    def filter_noreactive(self, **filters):
        serializer = serialize.Serializer()
        filters_id = [ (self.__fields_by_name[name].id, serializer.serialize(value=value, type_=self.__fields_by_name[name].type)) for name, value in filters.items() ]
        c = self.conn.execute('SELECT id, %s FROM %s WHERE %s' %
                              (', '.join( f'f{f.id}' for f in self._fields),
                               self.table_name,
                               ' AND '.join( f'f{id} = ?' for id in filters_id ) or '1=1'),
                              tuple( value for _, value in filters_id ))
        return [ self.__unserialize_row(row) for row in c ]
