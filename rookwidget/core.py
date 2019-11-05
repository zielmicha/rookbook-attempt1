from rookcore.common import *
from rookcore.reactive import *
from rookwidget import dom
from typing import *
from abc import abstractmethod, ABCMeta
import itertools

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
        self._current_vdom = None
        self._current_dom = None
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
                widget_obj = self._children[key]
            else:
                print('creating widget!', widget)
                widget_obj = widget.type_(*widget.args, **widget.kwargs)

            new_children[key] = widget_obj
            widget_obj._params.value = _Args(widget.args, widget.kwargs)
            return widget_obj._dom_render.value

        result = _apply_dom_patch(src_vdom=self._current_vdom, src_dom=self._current_dom,
                                  dst_vdom=element,
                                  get_child_widget=get_child_widget)
        self._current_dom = result
        self._current_vdom = element
        self._children = frozendict(new_children)
        return result

def _apply_dom_patch(src_vdom, src_dom, dst_vdom, get_child_widget):
    if isinstance(dst_vdom, _Element):
        if not isinstance(src_vdom, _Element) or src_vdom.name != dst_vdom.name:
            src_vdom = None

        if src_vdom is None:
            src_vdom = _Element(dst_vdom.name, {}, [])
            result = dom.createElement(dst_vdom.name)
        else:
            result = src_dom

        for k, v in dst_vdom.attrs.items():
            if src_vdom.attrs.get(k) != v:
                # TODO: event handlers now leak memory
                dom.setAttribute(result, k, v)

        for k, v in src_vdom.attrs.items():
            if k not in src_vdom.attrs:
                result.removeAttribute(k)

        # import random
        # dom.setAttribute(e, "data-uniq-id", str(random.randrange(1000000)))

        removed_count = 0

        for i, (src_child, dst_child) in enumerate(itertools.zip_longest(src_vdom.children, dst_vdom.children)):
            if dst_child is None:
                result.removeChild(result.childNodes[i - removed_count])
                removed_count += 1
            else:
                child_dom = result.childNodes[i] if src_child is not None else None
                child_result = _apply_dom_patch(src_child, child_dom, dst_child, get_child_widget)
                if child_result != child_dom:
                    if child_dom is None:
                        result.appendChild(child_result, child_dom)
                    else:
                        result.replaceChild(child_result, child_dom)

        return result
    elif isinstance(dst_vdom, _Widget):
        return get_child_widget(dst_vdom)
    elif isinstance(dst_vdom, str):
        if src_vdom == dst_vdom:
            return src_dom
        else:
            return dom.createTextNode(dst_vdom)
    else:
        raise TypeError(type(dst_vdom))

def mount_widget(widget, parent):
    container = dom.createElement('div')
    parent.appendChild(container)

    def set_child(child):
        #parent.removeChild(parent.childNodes[0])
        #parent.appendChild(child)
        parent.replaceChild(child, parent.childNodes[0])

    set_child(widget._dom_render.value)
    observer = Observer(widget._dom_render, lambda: set_child(widget._dom_render.value))
    container.dataset.rookwidget_observer = observer
