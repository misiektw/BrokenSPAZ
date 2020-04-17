from sys import stdout

class Operation:
    def __init__(self, operands):
        self.operands = operands

    def __eq__(self, obj):
        return str(self) == str(obj)


class Add(Operation):
    def __str__(self):
        return " + ".join(str(op) for op in self.operands)


class Sub(Operation):
    def __str__(self):
        return " - ".join(str(op) for op in self.operands)


class Mul(Operation):
    def __str__(self):
        return " * ".join(str(op) for op in self.operands)


class Div(Operation):
    def __str__(self):
        return " / ".join(str(op) for op in self.operands)


class Mod(Operation):
    def __str__(self):
        return " % ".join(str(op) for op in self.operands)


class Neg(Operation):
    def __str__(self):
        if isinstance(self.operands[0], float):
            return "-" + str(self.operands[0])
        else:
            return "-1.0 * " + str(self.operands[0])


class Not(Operation):
    def __str__(self):
        # If negates an equal operation:
        if isinstance(self.operands[0], StringEqual):
            # Get operands of equal operation:
            equalOperands = self.operands[0].operands
            # Get not equal operation with the same operands:
            notEqualOperation = StringNotEqual(equalOperands)
            # Call not equal operation instead:
            return str(notEqualOperation)
        # TODO: Cover more cases
        else:
            return "!(" + str(self.operands[0]) + ")"


class Equal(Operation):
    def __str__(self):
        return " == ".join(str(op) for op in self.operands)


class NotEqual(Operation):
    def __str__(self):
        return " != ".join(str(op) for op in self.operands)


class Less(Operation):
    def __str__(self):
        return " < ".join(str(op) for op in self.operands)


class LessOrEqual(Operation):
    def __str__(self):
        return " <= ".join(str(op) for op in self.operands)


class Greater(Operation):
    def __str__(self):
        return " > ".join(str(op) for op in self.operands)


class GreaterOrEqual(Operation):
    def __str__(self):
        return " >= ".join(str(op) for op in self.operands)


class And(Operation):
    def __str__(self):
        return " && ".join(str(op) for op in self.operands)


class Or(Operation):
    def __str__(self):
        return " || ".join(str(op) for op in self.operands)


class Complement(Operation):
    def __str__(self):
        return " ~ ".join(str(op) for op in self.operands)


class BitAnd(Operation):
    def __str__(self):
        return " & ".join(str(op) for op in self.operands)


class BitOr(Operation):
    def __str__(self):
        return " | ".join(str(op) for op in self.operands)


class Xor(Operation):
    def __str__(self):
        return " ^ ".join(str(op) for op in self.operands)


class ShiftLeft(Operation):
    def __str__(self):
        return " << ".join(str(op) for op in self.operands)


class ShiftRight(Operation):
    def __str__(self):
        return " >> ".join(str(op) for op in self.operands)


class StringEqual(Operation):
    def __str__(self):
        return " $= ".join(str(op) for op in self.operands)


class StringNotEqual(Operation):
    def __str__(self):
        return " !$= ".join(str(op) for op in self.operands)


class Concat(Operation):
    def __str__(self):
        return " @ ".join(str(op) for op in self.operands)


class ConcatNl(Operation):
    def __str__(self):
        return " NL ".join(str(op) for op in self.operands)


class ConcatTab(Operation):
    def __str__(self):
        return " TAB ".join(str(op) for op in self.operands)


class ConcatSpc(Operation):
    def __str__(self):
        return " SPC ".join(str(op) for op in self.operands)


class ConcatComma(Operation):
    def __str__(self):
        return ", ".join(str(op) for op in self.operands)

def isConcatOp(op):
    return isinstance(op, Concat) or isinstance(op, ConcatNl) or isinstance(op, ConcatSpc) or isinstance(op, ConcatTab) or isinstance(op, ConcatComma)

class ArrayAccess(Operation):
    def __str__(self):
        return str(self.operands[0]) + "[" + str(self.operands[1]) + "]"


class Node:
    def __init__(self):
        self.parent = None
        self.children = []
        self.carryIndent = 0

    def append(self, child):
        child.parent = self
        self.children.append(child)


class Assignment(Node):
    def __init__(self, left, right):
        super().__init__()

        self.left = left
        self.right = right

        if isinstance(self.right, ObjDecl):
            self.children = self.right.children
            self.carryIndent = self.right.carryIndent
        else:
            self.carryIndent = 0

    def __str__(self):
        return str(self.left) + " = " + str(self.right)


class Else(Node):
    def __init__(self):
        super().__init__()

        self.carryIndent = 1

    def __str__(self):
        return "else"


class File(Node):
    def __init__(self, name):
        super().__init__()

        self.name = name
        self.carryIndent = 0

    def __str__(self):
        return "// Decompiled file: " + self.name


class FuncCall(Node):
    callTypes = {
        0:  "Function",
        1:  "Method",
        2:  "Parent"
    }

    def __init__(self, name, namespace, callType, argv):
        super().__init__()

        self.name = name
        self.namespace = namespace
        self.callType = callType

        if self.callTypes[self.callType] == "Method":
            self.objClass = argv[0]
            self.argv = argv[1:]
        else:
            self.argv = argv

        self.carryIndent = 0

    def __str__(self):
        if self.namespace == "":
            if self.callTypes[self.callType] == "Parent":
                baseStr = "base::"
            else:
                baseStr = ""
        else:
            baseStr = self.namespace + "::"

        if self.callTypes[self.callType] == "Method":
            # TODO: What if built dynamically?
            baseStr += str(self.objClass) + "."

        return baseStr + self.name + "(" + str(ConcatComma(self.argv)) + ")"


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
        self.carryIndent = 1

    def __str__(self):
        if self.namespace == "":
            return "function " + self.name + "(" + str(ConcatComma(self.argv)) + ")"
        else:
            return "function " + self.namespace + "::" + self.name + "(" + str(ConcatComma(self.argv)) + ")"


class If(Node):
    def __init__(self, condition):
        super().__init__()

        self.condition = condition

        self.elseHandle = None
        self.carryIndent = 1

    def __str__(self):
        return "if (" + str(self.condition) + ")"
    

class ObjDecl(Node):
    def __init__(self, parentName, isDataBlock, argv):
        super().__init__()

        self.parentName = parentName
        self.isDataBlock = isDataBlock

        self.objType = argv[0]
        self.argv = argv[1:]

        if self.argv:
            self.argv[0] = "Name : " + str(self.argv[0])

        self.carryIndent = 1

    def __str__(self):
        return "new " + self.objType + "(" + str(ConcatComma(self.argv)) + ")"


class Return(Node):
    def __init__(self, value):
        super().__init__()

        self.value = value
        self.carryIndent = 0

    def __str__(self):
        if self.value == None:
            return "return"
        else:
            return "return " + str(self.value)


class While(Node):
    def __init__(self, condition):
        super().__init__()

        self.condition = condition

        self.carryIndent = 1

    def __str__(self):
        return "while (" + str(self.condition) + ")"


class Tree:
    def __init__(self, root):
        self.root = root
        self.curNode = root
        self.indent = ""

    def append(self, node):
        self.curNode.append(node)

    def replace(self, new):
        old = self.curNode

        parent = old.parent
        children = old.children

        if parent is not None:
            parent.children[parent.children.index(old)] = new

        for child in children:
            child.parent = new

        new.parent = parent
        new.children = children

        self.curNode = new

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

        # Print indented line of code:
        print(self.indent + str(thisNode), end="", file=sink)

        # If opens a block:
        if thisNode.carryIndent > 0:
            # Print newline:
            print("", file=sink)
            # Open brackets:
            print(self.indent + "{", file=sink)
            # Indent:
            self.indent += "\t" * thisNode.carryIndent
        else:
            print(";", file=sink)

        # Call recursively for all children:
        for child in thisNode.children:
            self.curNode = child
            self.dump(sink=sink)

        # If opens a block:
        if thisNode.carryIndent > 0:
            # Unindent:
            self.indent = self.indent[:-thisNode.carryIndent]
            # Close brackets:
            print(self.indent + "}", file=sink)

        # Restore current node:
        self.curNode = thisNode
