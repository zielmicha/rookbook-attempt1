from typing import *

class Node:
    def __init__(self, name, *args):
        self.name = name
        self.attrs: Dict[str, Any] = {}
        self.children: List[Any] = []
        for arg in args:
            if isinstance(arg, dict):
                self.attrs.update(arg)
            else:
                self.children.append(arg)

        # self.attrs = freeze(self.attrs)
        # self.children = freeze(self.children)

    def __eq__(self, other):
        return type(other) == Node and other.name == self.name and other.attrs == self.attrs and other.children == self.children

def make_dom(vdom):
    pass
