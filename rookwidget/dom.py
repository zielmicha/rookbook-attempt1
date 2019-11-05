try:
    import js
except ImportError:
    def createElement(name):
        return Element(name)

    class Element:
        def __init__(self, name):
            self.name = name
            self._children = []
            self._attrs = {}

        def appendChild(self, elem):
            self._children.append(elem)

    def setAttribute(e, k, v):
        e._attrs[k] = v

    def createTextNode(s):
        return s
else:
    def createElement(name):
        return js.document.createElement(name)

    def createTextNode(s):
        return js.document.createTextNode(s)

    def setAttribute(e, k, v):
        setattr(e, k, v)
