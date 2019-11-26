from rookwidget.core import Widget, widget, h
from rookcore import serialize, rpc
from rookcore.record import *
from rookcore.common import *
from . import base_cells

ValCellValue = make_record('ValCellValue', [
    field('name', id=1, type=str),
    field('value_repr', id=2, type=str),
])

class ValCellWidget(Widget):
    def init(self, value: serialize.AnyPayload):
        self.value = value.unserialize(ValCellValue)

    def render(self):
        return h('div', '%s = %s' % (self.value.name, self.value.value_repr))

def val_cell_widget_server(cell: base_cells.ValCell):
    try:
        value_repr = repr(cell.result.value)
    except Exception as exc:
        value_repr = 'error: ' + str(exc)

    return serialize.TypedPayload(type_=ValCellValue,
                                  value=ValCellValue(name=cell.name, value_repr=value_repr))

class LoadingWidget(Widget):
    def init(self, value): pass

    def render(self):
        return h('div', 'loading...')

cell_widget_types = frozendict({
    'val': (val_cell_widget_server, ValCellWidget),
    'loading': (None, LoadingWidget)
})
