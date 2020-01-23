from rookcore.reactive import *
from rookcore.common import *
from rookcore.record import *
from rookcore import rpc, serialize
from typing import *
import os, json, string

allowed_file_name_letters = string.ascii_lowercase + string.ascii_uppercase + string.digits + '_.'

class Storage:
    root_dir: str

    def get_file_path(self, name):
        if not all( ch in allowed_file_name_letters for ch in name ):
            raise ValueError('invalid file name %r' % name)

        return os.path.join(self.root_dir, name)

class BookScope:
    def __init__(self, storage, cell_types, cell_sources: Ref[Dict[str, str]]):
        self.storage = storage
        self.cell_sources = cell_sources
        self._cell_sources = reactive_dict_map(f=lambda r: r, ref=cell_sources)
        self.cells = reactive_dict_map(f=self._eval_cell, ref=const_ref(self._cell_sources))
        self.values = reactive_dict_map(f=lambda v: v.value, ref=reactive(self._get_values))
        self.ns = _Namespace(self)
        self.cell_types = cell_types

    def _get_values(self):
        cells = self.cells
        result: Dict[str, Ref] = {}
        for cell_id in cells:
            cell = cells[cell_id]
            for k, v in cell.value.get_values().items():
                if k in result:
                    # todo: error if k already in r
                    print('duplicate variable', k)

                result[k] = v

        return frozendict(result)

    @reactive_property
    def require_all_values(self):
        for k in self.values.keys():
            self.values[k]._record_read()

        return self.values.keys()

    def _eval_cell(self, source: Ref[str]):
        source = source.value.strip()
        if not source.startswith('%'): raise Exception('source should start with "%"')

        mod_name, rest = source[1:].split(None, 1)
        return self.cell_types[mod_name].parse(self, rest)

builtins_dict = __builtins__

class _Namespace:
    def __init__(self, book):
        self.__book = book

    def __setitem__(self, name, value):
        self.__book.values[name].value = value

    def __getitem__(self, name):
        if name == '__builtins__':
            return builtins_dict

        if name in builtins_dict:
            raise KeyError()

        return self.__book.values[name].value

OnDiskCellInfo = make_record('OnDiskCellInfo', [
    field('uuid', id=1, type=str),
    field('code', id=2, type=str),
])

WidgetValueType = make_record('WidgetValueType', [
    field('kind', id=1, type=str),
    field('payload', id=2, type=serialize.AnyPayload, default=serialize.TypedPayload(value=None, type_=type(None))),
])

WidgetValue = make_record('WidgetValue', [
    field('type', id=1, type=WidgetValueType),
    field('value', id=2, type=serialize.AnyPayload),
])

RemoteCellInfo = make_record('RemoteCellInfo', [
    field('uuid', id=1, type=str),
    field('code', id=2, type=Ref[str]),
    field('widget_value', id=3, type=WidgetValue),
])

class SheetData:
    def __init__(self, cells: List[OnDiskCellInfo]):
        self.cells = VarRef({
            c.uuid: VarRef(c.code) for c in cells
        })
        self.visible_cells = VarRef([ cell.uuid for cell in cells ])

    @classmethod
    def load_from_file(self, path):
        with open(path, 'r') as f: data = json.load(f)
        return SheetData([
            OnDiskCellInfo(uuid=l['uuid'], code=l['code'])
            for l in data
        ])

class SheetIface(metaclass=rpc.RpcMeta):
    @rpc.rpcmethod(id=1)
    def get_cells(self) -> Ref[List[RemoteCellInfo]]:
        raise

class Sheet(SheetIface):
    def __init__(self, scope, sheet_data):
        self.sheet_data = sheet_data
        self.scope = scope

    async def get_cells(self):
        return reactive(lambda: [
            self._make_remote_cell_info(uuid) for uuid in self.sheet_data.visible_cells.value
        ])

    def _make_remote_cell_info(self, uuid):
        cell_source = self.sheet_data.cells.value[uuid]

        if uuid in self.scope.cells:
            cell = self.scope.cells[uuid].value
            widget_value = cell.get_widget_value()
        else:
            widget_value = WidgetValue(
                value=TypedPayload(value=None, type_=type(None)),
                type=WidgetValueType(kind='none'))

        return RemoteCellInfo(
            uuid=uuid,
            code=cell_source,
            widget_value=widget_value,
        )

class Book:
    def __init__(self, cell_types, root_dir):
        self.storage = Storage()
        self.storage.root_dir = root_dir

        self._sheet_data = VarRef({})
        self.scope = BookScope(self.storage, cell_types, self._cell_sources)
        self.sheets = reactive_dict_map(
            ref=self._sheet_data,
            f=lambda sheet_data: Sheet(sheet_data=sheet_data, scope=self.scope))
        self._load_sheets()

    @reactive_property
    def _cell_sources(self):
        result = {}
        for sheet_data in self._sheet_data.value.values():
            result.update({ k: v.value for k, v in sheet_data.cells.value.items() })
        return result

    def _load_sheets(self):
        sheets = {}
        for fn in os.listdir(self.storage.root_dir):
            if fn.endswith('.sheet'):
                name = fn.rsplit('.', 1)[0]
                fn = self.storage.root_dir + '/' + fn
                sheets[name] = SheetData.load_from_file(fn)

        self._sheet_data.value = sheets
