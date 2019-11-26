from rookcore.common import *
from rookcore.record import *
from rookcore.reactive import reactive

class ValCell:
    @classmethod
    def parse(cls, book, text):
        name, code = text.split('=', 1)
        name = name.strip()
        code = code.strip()
        return cls(book, name, code)

    cell_type = 'val'

    def __init__(self, book, name, code):
        self.book = book
        self.name = name
        self.result = reactive(lambda: eval(code, {'__builtins__': __builtins__}, self.book.ns))

    def get_values(self):
        return {
            self.name: self.result
        }

cell_types = frozendict({
    'val': ValCell
})
