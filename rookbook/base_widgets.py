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
        return h('div', self.value.value)

class ErrorWidget(Widget):
    def init(self, type_args, value):
        self.msg = value.unserialize(Ref[str])

    def render(self):
        return h('div', {'style': 'color: red'}, self.msg.value)

cell_widget_types = frozendict({
    'string': StringWidget,
    'error': ErrorWidget,
    'unknown': UnknownWidget
})
