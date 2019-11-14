from rookcore.reactive import reactive, reactive_dict_map, const_ref, reactive_property, Ref
from typing import *

class Book:
    def __init__(self, cell_types, cell_sources):
        self.cell_sources = cell_sources
        self._cell_sources = reactive_dict_map(f=lambda r: r, ref=cell_sources)
        self._cells = reactive_dict_map(f=self.eval_cell, ref=const_ref(self._cell_sources))
        self.values = reactive_dict_map(f=lambda v: v, ref=reactive(self._get_values))
        self.ns = _Namespace(self)
        self.cell_types = cell_types

    def _get_values(self):
        cells = self._cells
        result: Dict[str, Ref] = {}
        for cell_id in cells:
            print(cells.dict_ref.value.dict_ref.value)
            cell = cells[cell_id]
            for k, v in cell.value.get_values().items():
                if k in result:
                    # todo: error if k already in r
                    print('duplicate variable', k)

                result[k] = v

        return result

    @reactive_property
    def require_all_values(self):
        for k in self.values.keys():
            self.values[k].value

    def eval_cell(self, source: Ref[str]):
        source = source.value.strip()
        if not source.startswith('%'): raise Exception('source should start with "%"')

        mod_name, rest = source[1:].split(None, 1)
        return self.cell_types[mod_name].parse(self, rest)

    def reload(self):
        pass

class _Namespace:
    def __init__(self, book):
        self.__book = book

    def __setitem__(self, name, value):
        self.__book.values[name].value = value

    def __getitem__(self, name):
        if name == '__builtins__':
            return __builtins__.__dict__

        return self.__book.values[name].value
