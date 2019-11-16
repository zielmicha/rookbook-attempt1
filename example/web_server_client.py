from rookcore import record, reactive, rpc, rpc_session, js_asyncio
from rookwidget.core import h, widget, Widget, mount_widget
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
        return h('h1', {'style': 'color: red'}, 'Hello world: ', str(self.who.value), h('br', {'data-foo': str(self.who.value)}), widget(TextBox, placeholder='hello'))

def client_run():
    js.document.body.innerHTML = ''
    who = reactive.VarRef(0)
    w = MyWidget(who)
    mount_widget(w, js.document.body)
    reactive.stabilise()

    def cont():
        who.value += 1
        reactive.stabilise()

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
        if f and f.startswith('/user-code.zip/'):
            print('unload', name)
            del sys.modules[name]

    print('load new code')
    js.window.startClientCode()

js.window.pyreload = pyreload
