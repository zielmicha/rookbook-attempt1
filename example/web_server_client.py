from rookcore import record, rpc, rpc_session, js_asyncio, js_rpc, async_tools
from rookcore.reactive import reactive, VarRef, stabilise
from rookwidget.core import h, widget, Widget, mount_root_widget, WidgetArgs
from . import web_server_common
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
    def init(self, who, text_var, m_ref):
        self.who = who
        self.text_var = text_var
        self.m_ref = m_ref

    def render(self):
        return h('h1', {'style': 'color: red'}, 'Hello world: ', str(self.who),
                 h('br', {'data-foo': str(self.who)}),
                 widget(TextBox, placeholder='hello', text_var=self.text_var),
                 widget(TextBox, placeholder='hello', text_var=self.text_var, key='w2'),
                 h('br'),
                 self.m_ref.value,
                 h('div', self.text_var.value.upper())
        )

def client_run():
    who = VarRef(0)
    text_var = VarRef('xoxo')

    def cont():
        who.value += 1
        stabilise()

    async def loop():
        while True:
            cont()
            await asyncio.sleep(2.0)

    async def rpc_main():
        session = await js_rpc.start_websocket_rpc_session('/websocket', root_object=None)
        iface = session.remote_root_object.as_proxy(web_server_common.ServerIface)

        m = await iface.welcome(who='michal')
        print(m)

        m_ref = await iface.welcome_reactive(who=text_var)
        print(m)

        w = MyWidget(reactive(lambda: WidgetArgs(args=(who.value, text_var, m_ref), kwargs={})))
        mount_root_widget(w)
        stabilise()

        async_tools.run_in_background(loop())

    async_tools.run_in_background(rpc_main())
