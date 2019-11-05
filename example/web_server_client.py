from rookcore import record, reactive
from rookwidget.core import h, widget, Widget, mount_widget
import js

class MyWidget(Widget):
    def init(self, who):
        self.who = who

    def render(self):
        return h('h1', 'Hello world: ', str(self.who.value), h('br'), h('input', {'type': 'text'}))

def client_run():
    js.document.body.innerHTML = ''
    who = reactive.VarRef(0)
    w = MyWidget(who)
    mount_widget(w, js.document.body)
    reactive.stabilise()

    def cont():
        who.value += 1
        reactive.stabilise()

    js.window.setInterval(cont, 500) # leak
