from rookcore import record, rpc, rpc_session, js_asyncio
from rookcore.reactive import reactive, VarRef, stabilise
from rookwidget.core import h, widget, Widget, mount_root_widget, WidgetArgs
import asyncio, traceback
import js # type: ignore

class TextBox(Widget):
    def init(self, placeholder, text_var):
        self.placeholder = placeholder
        self.text_var = text_var

    def render(self):
        cb_js = 'rookwidget_callback(%d, "_on_change", this.value)' % self.id
        return h('input', {'type': 'text', 'placeholder': self.placeholder,
                           'value': self.text_var.value,
                           'oninput': cb_js,
                           'onchange': cb_js})

    def _on_change(self, v):
        self.text_var.value = v
        stabilise()

class MyWidget(Widget):
    def init(self, who, text_var):
        self.who = who
        self.text_var = text_var

    def render(self):
        return h('h1', {'style': 'color: red'}, 'Hello world: ', str(self.who),
                 h('br', {'data-foo': str(self.who)}),
                 widget(TextBox, placeholder='hello', text_var=self.text_var),
                 widget(TextBox, placeholder='hello', text_var=self.text_var, key='w2'),
                 h('br'),
                 h('div', self.text_var.value.upper())
        )

def client_run():
    who = VarRef(0)
    text_var = VarRef('xoxo')
    w = MyWidget(reactive(lambda: WidgetArgs(args=(who.value, text_var), kwargs={})))
    mount_root_widget(w)
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
