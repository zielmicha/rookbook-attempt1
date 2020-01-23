from rookwidget.core import Widget, widget, h
from rookcore import serialize, rpc
from rookcore.record import *
from rookcore.reactive import *
from rookcore.common import *
from . import base_cells

class UnknownWidget(Widget):
    def init(self, type_args, value):
        self.repr = value.unserialize(Ref[str])

    def render(self):
        return h('div', self.repr.value)

class StringWidget(Widget):
    def init(self, type_args, value):
        self.value = value.unserialize(Ref[str])

    def render(self):
        if self.value.is_writable:
            return h('input', {'value': self.value.value,
                               'onedit': self.event_handler('_edit'),
                               'onkeyup': self.event_handler('_edit')})
        else:
            return h('div', self.value.value, repr(self.value))

    def _edit(self, event):
        self.value.value = event.target.value
        stabilise()

class ErrorWidget(Widget):
    def init(self, type_args, value):
        self.msg = value.unserialize(Ref[str])

    def render(self):
        return h('div', {'style': 'color: red'}, 'Error: %s' % self.msg.value)

class TableWidget(Widget):
    pass

cell_widget_types = frozendict({
    'string': StringWidget,
    'error': ErrorWidget,
    'unknown': UnknownWidget,
    'table': TableWidget,
})
