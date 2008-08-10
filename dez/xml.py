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

    def _full_name(self):
        if self.attributes:
            return self.name + ' ' + ' '.join(['%s=%s'%(key, val) for key, val in self.attributes.items()])
        return self.name

    def has_children(self):
        return bool(self.children)

    def add_child(self, child):
        self.children.append(child)

    def add_attribute(self, key, val):
        self.attributes[key] = val