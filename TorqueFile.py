from TorqueNode import TorqueNode

class TorqueFile(TorqueNode):
    def __init__(self, name):
        TorqueNode.__init__(self)

        self.name = name