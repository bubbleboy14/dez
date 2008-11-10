from xml.dom.minidom import parseString

LT_ESCAPE = "__LT_ESCAPE__"
GT_ESCAPE = "__GT_ESCAPE__"

class XMLNode(object):
    def __init__(self, name):
        self.name = name
        self.attributes = {}
        self.children = []

    def __repr__(self):
        return "<XMLNode %s>"%self.name

    def __str__(self):
        if self.children:
            return "<%s>%s</%s>"%(self._full_name(), ''.join([str(c) for c in self.children]), self.name)
        return "<%s/>"%(self._full_name())

    def __len__(self):
        return len(self.__str__())

    def _full_name(self):
        if self.attributes:
            return self.name + ' ' + ' '.join(["%s='%s'"%(key, val) for key, val in self.attributes.items()])
        return self.name

    def has_children(self):
        return bool(self.children)

    def has_attribute(self, attr):
        return attr in self.attributes

    def attr(self, attr):
        return self.attributes.get(attr, None)

    def add_child(self, child):
        self.children.append(child)

    def add_attribute(self, key, val):
        self.attributes[key] = val

def new_node(dnode, unescape=False):
    if dnode.nodeType == dnode.TEXT_NODE:
        if not unescape:
            return dnode.data.replace(LT_ESCAPE,"&lt;").replace(GT_ESCAPE,"&gt;")
        return dnode.data
    node = XMLNode(dnode.nodeName)
    for key, val in dnode.attributes.items():
        node.add_attribute(key, val)
    for child in dnode.childNodes:
        node.add_child(new_node(child))
    return node

def extract_xml(string, unescape=False):
    try:
        if not unescape:
            string = string.replace("&lt;",LT_ESCAPE).replace("&gt;",GT_ESCAPE)
        return new_node(parseString(string).firstChild, unescape)
    except:
        return None