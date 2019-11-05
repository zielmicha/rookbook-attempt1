from rookcore.common import *
from rookcore.reactive import *
from rookwidget import dom
from typing import *
from abc import abstractmethod, ABCMeta

class _Element(NamedTuple):
    name: str
    attrs: Dict
    children: List

def h(name, *args):
    attrs = {}
    children = []

    for arg in args:
        if isinstance(arg, dict):
            attrs.update(arg)
        elif isinstance(arg, (_Widget, _Element, str)):
            children.append(arg)
        else:
            raise TypeError('unknown element: %r' % arg)

    return _Element(name, attrs, children)

class _Widget(NamedTuple):
    type_: Any
    key: Any
    args: List
    kwargs: Dict

class _Args(NamedTuple):
    args: Tuple
    kwargs: Dict

def widget(type_, *args, key=None, **kwargs):
    assert issubclass(type_, Widget)
    return _Widget(type_, key, frozenlist(args), frozendict(kwargs))

class Widget(metaclass=ABCMeta):
    def __init__(self, *args, **kwargs):
        self._params = VarRef(_Args(args, kwargs))
        self._children = {}
        self._dom_render = reactive(self._dom_render_internal)

    def init(self):
        pass

    @abstractmethod
    def render(self):
        pass

    def _dom_render_internal(self):
        params = self._params.value
        self.init(*params.args, **params.kwargs) # type: ignore

        element = self.render()
        new_children: Dict[Any, Widget] = {}

        def get_child_widget(widget):
            key = widget.key or widget.type_
            if key in new_children:
                raise Exception('duplicate widget key %r' % key)

            if key in self._children:
                widget = self._children[key]
            else:
                widget = widget.type_(*widget.args, **widget.kwargs)

            new_children[key] = widget
            widget._params.value = _Args(widget.args, widget.kwargs)
            return widget._dom_render.value

        self._children = new_children

        return _to_dom(element, get_child_widget)

def _to_dom(element, handle_widget):
    if isinstance(element, _Element):
        e = dom.createElement(element.name)

        for k, v in element.attrs.items():
            # TODO: event handlers now leak memory
            dom.setAttribute(e, k, v)

        for child in element.children:
            e.appendChild(_to_dom(child, handle_widget))

        return e
    elif isinstance(element, _Widget):
        return handle_widget(element)
    elif isinstance(element, str):
        return dom.createTextNode(element)
    else:
        raise TypeError(type(element))

def mount_widget(widget, parent):
    container = dom.createElement('div')
    parent.appendChild(container)

    def set_child(child):
        parent.removeChild(parent.childNodes[0])
        parent.appendChild(child)

    set_child(widget._dom_render.value)
    observer = Observer(widget._dom_render, lambda: set_child(widget._dom_render.value))
    container.dataset.rookwidget_observer = observer
