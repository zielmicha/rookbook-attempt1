from . import web_widget
from .record import *
from .reactive import *
from .vdom import *

class TodoListServer(web_widget.WidgetServer):
    def init(self, title, items):
        self.title = title
        self.children.items = {
            k : TodoItemServer(v)
            for k, v in items
        }

    def client_state(self):
        return (Client, {'title': self.title})

class TodoList(web_widget.Widget):
    def init(self, state):
        self.title = state['title']
        # self.children.title_widget = InputWidget()

    def render(self):
        pass

class TodoItemServer(web_widget.WidgetServer):
    def init(self, value):
        pass

    def client_state(self):
        pass

class TodoItem(web_widget.Widget):
    def init(self, state):
        pass

    def client_state(self):
        pass

if __name__ == '__main__':
    state = RootState(counter=0, secret_value="secret!")
    root_widget = RootWidget.create(log=sys.stdout)
