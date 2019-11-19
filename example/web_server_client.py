from rookcore import record, rpc, rpc_session, js_asyncio
from rookcore.reactive import reactive, VarRef, stabilise
from rookwidget.core import h, widget, Widget, mount_widget, WidgetArgs
import asyncio, traceback
import js # type: ignore

class TextBox(Widget):
    def init(self, placeholder):
        self.placeholder = placeholder

    def render(self):
        return h('input', {'type': 'text', 'placeholder': self.placeholder})

class MyWidget(Widget):
    def init(self, who):
        self.who = who

    def render(self):
        return h('h1', {'style': 'color: red'}, 'Hello world: ', str(self.who), h('br', {'data-foo': str(self.who)}), widget(TextBox, placeholder='hello'))

def client_run():
    js.document.body.innerHTML = ''
    who = VarRef(0)
    w = MyWidget(reactive(lambda: WidgetArgs(args=(who.value,), kwargs={})))
    mount_widget(w, js.document.body)
    stabilise()

    def cont():
        who.value += 1
        stabilise()

    async def loop():
        try:
            while True:
                cont()
                await asyncio.sleep(2.0)
        except Exception:
            traceback.print_exc()

    asyncio.ensure_future(loop())

def pyreload():
    import sys

    for name, mod in list(sys.modules.items()):
        f = getattr(mod, '__file__', None)
        if f and f.startswith('/user-code'):
            print('unload', name)
            del sys.modules[name]

    print('load new code')
    js.window.startClientCode()

js.window.pyreload = pyreload
