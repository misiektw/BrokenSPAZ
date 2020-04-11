from TorqueNode import TorqueNode

class TorqueFunctionCall(TorqueNode):
    def __init__(self, name, namespace, callType, argv):
        TorqueNode.__init__(self)

        self.name = name
        self.namespace = namespace
        self.callType = callType
        self.argv = argv