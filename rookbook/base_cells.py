from rookcore.common import *
from rookcore.record import *
from rookcore.reactive import *
from rookcore import serialize, persistent_ref
from rookbook.core import WidgetValueType, WidgetValue

class ValCell:
    @classmethod
    def parse(cls, book, text):
        name, code = text.split('=', 1)
        name = name.strip()
        code = code.strip()
        return cls(book, name, code)

    def __init__(self, book, name, code):
        self.book = book
        self.name = name
        self.result = reactive(lambda: eval(code, {'__builtins__': __builtins__}, self.book.ns))

    def get_values(self):
        return {
            self.name: self.result
        }

    def get_widget_value(self):
        return get_widget_value(self.result)

class VarCell:
    @classmethod
    def parse(cls, book, text):
        name, type_code = text.split(':', 1)
        name = name.strip()
        type_code = type_code.strip()
        return cls(book, name, type_code)

    def __init__(self, book, name, type_code):
        self.book = book
        self.name = name
        self.type_ = eval(type_code, {'__builtins__': __builtins__})
        self.value = persistent_ref.make_file_based_ref(self.type_, book.storage.get_file_path('%s.var' % self.name))

    def get_values(self):
        return {
            self.name: self.value
        }

    def get_widget_value(self):
        return get_widget_value(self.value)

def get_widget_value(ref):
    try:
        t = type(ref.value)
    except Exception as err:
        return WidgetValue(
            type=WidgetValueType(kind='error'),
            value=serialize.TypedPayload(type_=Ref[str], value=const_ref(str(err))))

    if t == str:
        return WidgetValue(
            type=WidgetValueType(kind='string'),
            value=serialize.TypedPayload(type_=Ref[str], value=ref))
    else:
        def f():
            try:
                return repr(ref.value)
            except Exception as err:
                return '[repr failed with %s]' % err
        
        return WidgetValue(
            type=WidgetValueType(kind='unknown'),
            value=serialize.TypedPayload(type_=Ref[str], value=reactive(f)))

cell_types = frozendict({
    'val': ValCell,
    'var': VarCell,
})
