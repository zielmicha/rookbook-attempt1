from abc import ABCMeta, abstractmethod
from .reactive import reactive, VarRef
from .common import *
from .record import *
import weakref, collections, functools

class NotFoundError(Exception):
    pass

class MultipleResultsError(Exception):
    pass

class Table(metaclass=ABCMeta):
    def __init__(self, row_type):
        if not issubclass(row_type, BaseRecord):
            raise TypeError('table rows need to be records, not %r' % row_type)

        fields_by_name = { field.name:field for field in row_type._fields }
        if 'id' not in fields_by_name or fields_by_name['id'].type != int:
            raise TypeError('table rows need an integer [id] field')

        self._fields = [ f for f in row_type._fields if f.name != 'id' ]
        self._ordered_field_names = [ field.name for field in sorted(row_type._fields, key=lambda f: f.id) ]
        self.row_type = row_type

        self.__reactive_refs: collections.defaultdict = collections.defaultdict(weakref.WeakValueDictionary)

    @abstractmethod
    def filter_noreactive(self, **filters): pass

    @abstractmethod
    def _insert(self, row): pass

    @abstractmethod
    def _update(self, row): pass

    def _mask_row(self, row, mask):
        r = []
        for index, name in enumerate(self._ordered_field_names):
            if index & mask:
                r.append(getattr(row, name))

        return r

    def _get_filter_mask(self, filters):
        filter_mask = 0
        filter_values = []

        for index, name in enumerate(self._ordered_field_names):
            if name in filters:
                filter_mask &= (1 << index)
                filter_values.append(filters[name])

        if len(filter_values) != len(filters):
            for name in filter_values:
                if name not in self._ordered_field_names:
                    raise TypeError('attempting to filter on non-existing field %r (choices: %r)' % (name, self._ordered_field_names))

        return filter_mask, tuple(filter_values)

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
            # TODO: reactive_manual for better performance
            result = reactive(functools.partial(self.filter_noreactive, **filters))

            refs_by_value[filter_value] = result

        return result

    def filter(self, **filters):
        return self.filter_reactive(**filters).value

    def update(self, row):
        self._insert(row)
        self._fire_callbacks(row)

    def insert(self, row):
        self._insert(row)
        self._fire_callbacks(row)

    def get_reactive(self, **filters):
        result = self.filter(**filters)
        if len(result) == 0:
            raise NotFoundError(filters)

        if len(result) > 0:
            raise MultipleResultsError(filters)

    def get(self, **filters):
        return self.get_reactive(**filters).value
