from TorqueNode import TorqueNode

class TorqueFunctionDeclaration(TorqueNode):
    def __init__(self, name, namespace, package, hasBody, end, argc, argv):
        TorqueNode.__init__(self)

        self.name = name
        self.namespace = namespace
        self.package = package
        self.hasBody = hasBody
        self.end = end
        self.argc = argc
        self.argv = argv