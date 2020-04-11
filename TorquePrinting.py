from sys import stdout

from TorqueFile import TorqueFile
from TorqueFunctionCall import TorqueFunctionCall
from TorqueFunctionDeclaration import TorqueFunctionDeclaration
from TorqueObject import TorqueObject
from TorqueReturn import TorqueReturn
from TorqueVariable import TorqueVariable

class TorquePrinting:
    def __init__(self, tree, sink=stdout):
        self.tree = tree
        self.sink = sink
        self.indent = 0

    def formatArgv(self, argv):
        baseStr = argv[0]
        for i in range(1, len(argv)):
            baseStr += ", " + argv[i]

        return baseStr

    def printIndented(self, arg):
        print("\t" * self.indent + arg, end="", file=self.sink)

    def printFile(self, node):
        self.printIndented("// Decompiled file: " + node.name + "\n\n")

        for child in node.children:
            self.printNode(child)

    def printCall(self, node):
        self.printCallByType[node.callType](self, node)

    def printFunctionCall(self, node):
        if node.namespace == "":
            self.printIndented(node.name + "(" + self.formatArgv(node.argv) + ");\n")
        else:
            self.printIndented(node.namespace + "::" + node.name + "(" + self.formatArgv(node.argv) + ");\n")

    def printMethodCall(self, node):
        if node.namespace == "":
            baseStr = ""
        else:
            baseStr = node.namespace + "::"

        if " " in node.argv[0]:
            # If built dynamically:
            baseStr += "(" + node.argv[0] + ")"
        else:
            baseStr += node.argv[0]

        self.printIndented(baseStr + "." + node.name + "(" + self.formatArgv(node.argv) + ");\n")

    # TODO:
    def printParentCall(self, node):
        raise NotImplementedError

    printCallByType = {
        0:  printFunctionCall,
        1:  printMethodCall,
        2:  printParentCall
    }

    def printFunctionDeclaration(self, node):
        if node.namespace == "":
            baseStr = "function " + node.name + "("
        else:
            baseStr = "function " + node.namespace + "::" + node.name + "("

        if node.argc > 0:
            baseStr += self.formatArgv(node.argv)

        baseStr += ")\n"

        self.printIndented(baseStr)
        self.printIndented("{\n")

        self.indent += 1

        for child in node.children:
            self.printNode(child)

        self.indent -= 1

        self.printIndented("}\n\n")

    def printObject(self, node):
        self.printIndented("%{} = new {}(Name : ".format(node.id, node.argv[0]) + self.formatArgv(node.argv[1:]) + ")\n")
        self.printIndented("{\n")

        # TODO: I think something should be printed here

        self.indent += 1

        for child in node.children:
            self.printNode(child)

        self.indent -= 1

        self.printIndented("}\n\n")

    def printReturn(self, node):
        self.printIndented("return {};\n".format(node.value))

    def printVariable(self, node):
        self.printIndented("{} = {};\n\n".format(node.name, node.value))

    callPrintRoutine = {
        "TorqueFile":                   printFile,
        "TorqueFunctionCall":           printCall,
        "TorqueFunctionDeclaration":    printFunctionDeclaration,
        "TorqueObject":                 printObject,
        "TorqueReturn":                 printReturn,
        "TorqueVariable":               printVariable
    }

    def printNode(self, node):
        self.callPrintRoutine[node.__class__.__name__](self, node)

    def print(self):
        self.printNode(self.tree)