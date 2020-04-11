class TorqueNode:
    def __init__(self):
        self.parent = None
        self.children = []

    def append(self, child):
        self.children.append(child)
        self.children[-1].parent = self