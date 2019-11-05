from rookcore import record, reactive
from rookwidget.core import h, widget, Widget, mount_widget
import js

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

    js.window.setInterval(cont, 2000) # leak
