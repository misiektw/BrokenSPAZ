from TorqueNode import TorqueNode

class TorqueVariable(TorqueNode):
    def __init__(self, name, value):
        TorqueNode.__init__(self)

        self.name = name
        self.value = value