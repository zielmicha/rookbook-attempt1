from abc import ABCMeta, abstractmethod
from .reactive import reactive, VarRef
from .common import *
import weakref, collections, functools

class Table(metaclass=ABCMeta):
    def __init__(self, row_type):
        self.row_type = row_type

        self.__reactive_refs: collections.defaultdict = collections.defaultdict(weakref.WeakValueDictionary)

    @abstractmethod
    def filter_noreactive(self, **filters): pass

    def _mask_row(self, row, mask):
        pass

    def _get_filter_mask(self, filters):
        pass

    def _fire_callbacks(self, row):
        for mask, refs_by_value in self.__reactive_refs.items():
            masked_row = self._mask_row(row, mask)
            refs = refs_by_value.get(masked_row, None)
            if refs:
                for ref in refs:
                    ref._refresh()

    def filter_reactive(self, **filters):
        filters = frozendict(filters)
        filter_mask, filter_value = self._get_filter_mask(filters)
        refs_by_value = self.__reactive_refs.get(filter_mask, None)
        result = refs_by_value.get(filter_value, None)

        if result is None:
            # TODO: reactive_manual
            result = reactive(functools.partial(self.filter_noreactive, **filters))

            refs_by_value[filter_value] = result

        return result

    def filter(self, **filters):
        return self.filter_reactive(**filters).value

class SqliteTable(Table):
    pass
