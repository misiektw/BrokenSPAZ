from sys import stdout

def formatArgv(prefix, argv):
    if len(argv) > 0:
        form = argv[0]
        for i in range(1, len(argv)):
            form += ", " + argv[i]

        return prefix + "(" + form + ")"
    else:
        return prefix + "()"

class Node:
    def __init__(self):
        self.parent = None
        self.children = []
        self.indentChildren = False

    def append(self, child):
        child.parent = self
        self.children.append(child)


class File(Node):
    def __init__(self, name):
        super().__init__()

        self.name = name
        self.indentChildren = False

    def dump(self, indent, sink=stdout):
        print(indent + "// Decompiled file: " + self.name, file=sink)


class FuncCall(Node):
    def __init__(self, name, namespace, callType, argv):
        super().__init__()

        dumpByType = {
            0:  self.dumpFunc,
            1:  self.dumpMethod,
            2:  self.dumpParent
        }

        self.name = name
        self.namespace = namespace
        self.callType = callType
        self.dump = dumpByType[callType]
        self.argv = argv
        self.indentChildren = False

    def dumpFunc(self, indent, sink=stdout):
        if self.namespace == "":
            print(indent + formatArgv(self.name, self.argv) + ";", file=sink)
        else:
            print(indent + formatArgv(self.namespace + "::" + self.name, self.argv) + ";", file=sink)

    def dumpMethod(self, indent, sink=stdout):
        if self.namespace == "":
            baseStr = ""
        else:
            baseStr = self.namespace + "::"

        if " " in self.argv[0]:
            # If built dynamically:
            baseStr += "(" + self.argv[0] + ")"
        else:
            baseStr += self.argv[0]

        print(indent + formatArgv(baseStr + "." + self.name, self.argv[1:]) + ";", file=sink)

    # TODO:
    def dumpParent(self, indent, sink=stdout):
        raise NotImplementedError


class FuncDecl(Node):
    def __init__(self, name, namespace, package, hasBody, end, argc, argv):
        super().__init__()

        self.name = name
        self.namespace = namespace
        self.package = package
        self.hasBody = hasBody
        self.end = end
        self.argc = argc
        self.argv = argv
        self.indentChildren = True

    def dump(self, indent, sink=stdout):
        if self.namespace == "":
            print(indent + "function " + formatArgv(self.name, self.argv), file=sink)
        else:
            print(indent + "function " + formatArgv(self.namespace + "::" + self.name, self.argv), file=sink)


class ObjDecl(Node):
    def __init__(self, parentName, isDataBlock, isInternal, isMessage, failJump, argv):
        super().__init__()

        self.parentName = parentName
        self.isDataBlock = isDataBlock
        self.isInternal = isInternal
        self.isMessage = isMessage
        self.failJump = failJump
        self.argv = argv
        self.id = None
        self.indentChildren = True

    def dump(self, indent, sink=stdout):
        if len(self.argv) >= 2:
            self.argv[1] = "Name : " + self.argv[1]

        print(indent + "%{} = new ".format(self.id) + formatArgv(self.argv[0], self.argv[1:]), file=sink)


class Return(Node):
    def __init__(self, value):
        super().__init__()

        self.value = value
        self.indentChildren = False

    def dump(self, indent, sink=stdout):
        print(indent + "return {};".format(self.value), file=sink)


class Variable(Node):
    def __init__(self, name, value):
        super().__init__()

        self.name = name
        self.value = value
        self.indentChildren = False

    def dump(self, indent, sink=stdout):
        print(indent + "{} = {};".format(self.name, self.value), file=sink)


class Tree:
    def __init__(self, root):
        self.root = root
        self.curNode = root
        self.indent = ""

    def append(self, node):
        self.curNode.append(node)

    def rewind(self):
        self.curNode = self.root

    def focusChild(self, idx=-1):
        self.curNode = self.curNode.children[idx]

    def focusParent(self):
        self.curNode = self.curNode.parent

    def getFocused(self):
        return self.curNode

    def dump(self, sink=stdout):
        # Get current node:
        thisNode = self.curNode

        thisNode.dump(self.indent, sink=sink)

        if thisNode.indentChildren:
            print(self.indent + "{", file=sink)
            self.indent += "\t"

        # Call recursively for all children:
        for child in thisNode.children:
            self.curNode = child
            self.dump(sink=sink)

        if thisNode.indentChildren:
            self.indent = self.indent[:-1]
            print(self.indent + "}", file=sink)

        # Restore current node:
        self.curNode = thisNode
