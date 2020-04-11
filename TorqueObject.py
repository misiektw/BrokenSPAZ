from TorqueNode import TorqueNode

class TorqueObject(TorqueNode):
    def __init__(self, parentName, isDataBlock, isInternal, isMessage, failJump, argv):
        TorqueNode.__init__(self)

        self.parentName = parentName
        self.isDataBlock = isDataBlock
        self.isInternal = isInternal
        self.isMessage = isMessage
        self.failJump = failJump
        self.argv = argv

        self.id = None