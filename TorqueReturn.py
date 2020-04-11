from TorqueNode import TorqueNode

class TorqueReturn(TorqueNode):
    def __init__(self, value):
        TorqueNode.__init__(self)

        self.value = value