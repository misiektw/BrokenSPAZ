from sys import stdout

'''
Template for TorqueScript operation
'''
class Operation:
    # By default, not included in any category:
    isArithmetic = False
    isBoolean = False
    isBitwise = False
    isString = False
    isAccess = False

    '''
    Constructs an Operation object
    @param  operands    List of operands
    '''
    def __init__(self, operands):
        self.operands = operands
        
        try:
            if isinstance(operands[0], StringEqual):
                self.isString = operands[0].isString
        except:
            pass
    '''
    Equal operator override
    @params obj     Object to compare this instance with
    '''
    def __eq__(self, obj):
        # Two statements are equal if their string representations are equal:
        return str(self) == str(obj)


'''
TorqueScript Add operation
'''
class Add(Operation):
    isArithmetic = True

    '''
    String representation override
    '''
    def __str__(self):
        return " + ".join(str(op) for op in self.operands)

class AddPP(Operation):
    isArithmetic = True

    '''
    String representation override
    '''
    def __str__(self):
        return str(self.operands[0]) + "++"


'''
TorqueScript Subtraction operation
'''
class Sub(Operation):
    isArithmetic = True


    def __str__(self):
        return " - ".join(str(op) for op in self.operands)

class SubPP(Operation):
    isArithmetic = True

    '''
    String representation override
    '''
    def __str__(self):
        return str(self.operands[0]) + "--"

'''
TorqueScript Multiply operation
'''
class Mul(Operation):
    isArithmetic = True


    def __str__(self):
        br = []
        for op in self.operands:
            if isinstance(op, Add) or isinstance(op, Sub):
                br.append('('+ str(op) +')')
            else:
                br.append(str(op))
        return " * ".join(br)


'''
TorqueScript Division operation
'''
class Div(Operation):
    isArithmetic = True


    def __str__(self):
        br = []
        for op in self.operands:
            if isinstance(op, Add) or isinstance(op, Sub):
                br.append('('+ str(op) +')')
            else:
                br.append(str(op))
        return " / ".join(br)


'''
TorqueScript Modulo operation
'''
class Mod(Operation):
    isArithmetic = True


    def __str__(self):
        return " % ".join(str(op) for op in self.operands)


'''
TorqueScript Modulo operation
'''
class Neg(Operation):
    isArithmetic = True


    def __str__(self):
        #if isinstance(self.operands[0], float):
        ##    return "-" + str(self.operands[0])
        #elif
        #else:
        try:
            number = eval("-1.0 * " + str(self.operands[0]))
            return str(number)
        except:
            if True in [ self.operands[0][0] == v for v in ['$','%','('] ]:
                return "-" + str(self.operands[0])
            else:
                return "-1.0 * " + str(self.operands[0])


'''
TorqueScript Negation operation
'''
class Not(Operation):
    isBoolean = True


    def __str__(self):
        # If negates a boolean equal operation:
        if isinstance(self.operands[0], StringEqual):
            operands = self.operands[0].operands
            if self.isString:
                operation = StringNotEqual(operands)
            else:
                operation = NotEqual(operands)
            return str(operation)
        # If negates a boolean not equal operation:
        elif isinstance(self.operands[0], StringNotEqual):
            operands = self.operands[0].operands
            operation = Equal(operands)
            return str(operation)
        # If negates a less than operation:
        elif isinstance(self.operands[0], Less):
            operands = self.operands[0].operands
            operation = GreaterOrEqual(operands)
            return str(operation)
        # If negates a less than or equal to operation:
        elif isinstance(self.operands[0], LessOrEqual):
            operands = self.operands[0].operands
            operation = Greater(operands)
            return str(operation)
        # If negates a greater than operation:
        elif isinstance(self.operands[0], Greater):
            operands = self.operands[0].operands
            operation = LessOrEqual(operands)
            return str(operation)
        # If negates a greater than or equal to operation:
        elif isinstance(self.operands[0], GreaterOrEqual):
            operands = self.operands[0].operands
            operation = Less(operands)
            return str(operation)
        # If negates a string equal operation:
        elif isinstance(self.operands[0], StringEqual):
            operands = self.operands[0].operands
            operation = StringNotEqual(operands)
            return str(operation)
        # If negates a string not equal operation:
        elif isinstance(self.operands[0], StringNotEqual):
            operands = self.operands[0].operands
            operation = StringEqual(operands)
            return str(operation)
        else:
            return "!(" + str(self.operands[0]) + ")"


'''
TorqueScript Equal operation
'''
class Equal(Operation):
    isBoolean = True


    def __str__(self):
        return " == ".join(str(op) for op in self.operands)


'''
TorqueScript Not Equal operation
'''
class NotEqual(Operation):
    isBoolean = True
    

    def __str__(self):
        return " != ".join(str(op) for op in self.operands)


'''
TorqueScript Less Than operation
'''
class Less(Operation):
    isBoolean = True


    def __str__(self):
        return " < ".join(str(op) for op in self.operands)


'''
TorqueScript Less Than Or Equal To operation
'''
class LessOrEqual(Operation):
    isBoolean = True


    def __str__(self):
        return " <= ".join(str(op) for op in self.operands)


'''
TorqueScript Greater Than operation
'''
class Greater(Operation):
    isBoolean = True


    def __str__(self):
        return " > ".join(str(op) for op in self.operands)


'''
TorqueScript Greater Than Or Equal To operation
'''
class GreaterOrEqual(Operation):
    isBoolean = True


    def __str__(self):
        return " >= ".join(str(op) for op in self.operands)


'''
TorqueScript And operation
'''
class And(Operation):
    isBoolean = True


    def __str__(self):
        return " && ".join(str(op) for op in self.operands)


'''
TorqueScript Or operation
'''
class Or(Operation):
    isBoolean = True


    def __str__(self):
        return " || ".join(str(op) for op in self.operands)


'''
TorqueScript One's Complement operation
'''
class Complement(Operation):
    isBoolean = True


    def __str__(self):
        return " ~ ".join(str(op) for op in self.operands)


'''
TorqueScript Bitwise And operation
'''
class BitAnd(Operation):
    isBitwise = True


    def __str__(self):
        return " & ".join(str(op) for op in self.operands)


'''
TorqueScript Bitwise Or operation
'''
class BitOr(Operation):
    isBitwise = True


    def __str__(self):
        return " | ".join(str(op) for op in self.operands)


'''
TorqueScript Bitwise Xor operation
'''
class Xor(Operation):
    isBitwise = True


    def __str__(self):
        return " ^ ".join(str(op) for op in self.operands)


'''
TorqueScript Shift Left operation
'''
class ShiftLeft(Operation):
    isBitwise = True


    def __str__(self):
        return " << ".join(str(op) for op in self.operands)


'''
TorqueScript Shift Right operation
'''
class ShiftRight(Operation):
    isBitwise = True


    def __str__(self):
        return " >> ".join(str(op) for op in self.operands)


'''
TorqueScript String Equal operation
'''
class StringEqual(Operation):
    isString = True


    def __str__(self):
        return " $= ".join(str(op) for op in self.operands)


'''
TorqueScript String Not Equal operation
'''
class StringNotEqual(Operation):
    isString = True


    def __str__(self):
        return " !$= ".join(str(op) for op in self.operands)


'''
TorqueScript String Concatenation operation
'''
class Concat(Operation):
    isString = True


    def __str__(self):
        return " @ ".join(str(op) for op in self.operands)


'''
TorqueScript String Newline Concatenation operation
'''
class ConcatNl(Operation):
    isString = True


    def __str__(self):
        return " NL ".join(str(op) for op in self.operands)


'''
TorqueScript String Tab Concatenation operation
'''
class ConcatTab(Operation):
    isString = True


    def __str__(self):
        return " TAB ".join(str(op) for op in self.operands)


'''
TorqueScript String Space Concatenation operation
'''
class ConcatSpc(Operation):
    isString = True


    def __str__(self):
        return " SPC ".join(str(op) for op in self.operands)


'''
TorqueScript String Comma Concatenation operation (for array access)
'''
class ConcatComma(Operation):
    isString = True


    def __str__(self):
        return ", ".join(str(op) for op in self.operands)


'''
TorqueScript Array Access operation
'''
class ArrayAccess(Operation):
    isAccess = True


    def __str__(self):
        try:
            return str(self.operands[0]) + "[" + str(int(eval(self.operands[1]))) + "]"
        except:
            return str(self.operands[0]) + "[" + str(self.operands[1]) + "]"

'''
TorqueScript Field Access operation
'''
class FieldAccess(Operation):
    isAccess = True


    def __str__(self):
        return ".".join(str(op) for op in self.operands)


'''
Template class for a node of the tree
'''
class Node:
    '''
    Constructs a Node object
    '''
    def __init__(self):
        self.parent = None
        self.children = []
        self.block = False
        self.is_object = False

    '''
    Equal operator override
    @params obj     Object to compare this instance with
    '''
    def __eq__(self, obj):
        # Two statements are equal if their string representations are equal:
        return str(self) == str(obj)

    '''
    Appends the given node to the children list
    @params child   Node to be appended as child
    '''
    def append(self, child):
        child.parent = self
        self.children.append(child)


'''
TorqueScript assignment
'''
class Assignment(Node):
    '''
    Constructs an Assignment object
    @param  left    Left operand of assignment
    @param  right   Right operand of assignment
    '''
    def __init__(self, left, right):
        # Inherit characteristics from Node:
        super().__init__()

        self.left = left
        self.right = right

        if isinstance(self.right, ObjCreation):
            # Move children of object to assignment
            self.children = self.right.children
            # Indicate if there is a block of code (children):
            self.block = self.right.block
            self.is_object = self.right.is_object
        else:
            # No block otherwise:
            self.block = False


    def __str__(self):
        if isinstance(self.right, AddPP) or isinstance(self.right, SubPP):
            if self.left == self.right.operands[0]:
                return str(self.right).replace('\n', '\\n') # put only var++/var-- not var=var++
        else:
            return str(self.left) + " = " + str(self.right).replace('\n', '\\n')


'''
TorqueScript break from loop statement
'''
class Break(Node):
    '''
    Constructs an Assignment object
    '''
    def __init__(self):
        # Inherit characteristics from Node:
        super().__init__()

        # No block declaration:
        self.block = False


    def __str__(self):
        return "break"


'''
TorqueScript else statement
'''
class Else(Node):
    '''
    Constructs an Assignment object
    '''
    def __init__(self):
        # Inherit characteristics from Node:
        super().__init__()

        # Block declaration:
        self.block = True


    def __str__(self):
        return "else"


'''
File information header comment (also root of tree)
'''
class File(Node):
    '''
    Constructs a File object
    @param  name    Name of the file being decompiled
    '''
    def __init__(self, name):
        # Inherit characteristics from Node:
        super().__init__()

        self.name = name

    def __str__(self):
        return "// Decompiled file: " + self.name


'''
TorqueScript function call
'''
class FuncCall(Node):
    callTypes = {
        0:  "Function",
        1:  "Method",
        2:  "Parent"
    }

    '''
    Constructs a FuncCall object
    @param  name        Name of the function being called
    @param  namespace   Namespace of function being called
    @param  callType    Type of call (function, method or parent)
    @param  argv        List of arguments passed to function
    '''
    def __init__(self, name, namespace, callType, argv):
        # Inherit characteristics from Node:
        super().__init__()

        self.name = name
        self.namespace = namespace
        self.callType = callType

        if self.callTypes[self.callType] == "Method":
            # First argument is actually the name of the object whose method is being called:
            self.objName = argv[0]
            self.argv = argv[1:]
        else:
            self.argv = argv

        # No block declaration:
        self.block = False


    def __str__(self):
        if self.namespace == "":
            if self.callTypes[self.callType] == "Parent":
                baseStr = "base::" # TODO: Is this the right syntax?
            else:
                baseStr = ""
        else:
            baseStr = self.namespace + "::"

        if self.callTypes[self.callType] == "Method":
            baseStr += str(self.objName) + "."

        return baseStr + self.name + "(" + str(ConcatComma(self.argv)) + ")"


'''
TorqueScript function declaration
'''
class FuncDecl(Node):
    '''
    Constructs a FuncDecl object
    @param  name        Name of the function being declared
    @param  namespace   Namespace of function being declared
    @param  package     Package of function being declared
    @param  hasBody     Boolean value indicating if function has body (block of code)
    @param  end         Code index of end of declaration
    @param  argc        Number of arguments passed to function
    @param  argv        List of arguments passed to function
    '''
    def __init__(self, name, namespace, package, hasBody, end, argc, argv):
        # Inherit characteristics from Node:
        super().__init__()

        self.name = name
        self.namespace = namespace
        self.package = package # TODO: Unused
        self.hasBody = hasBody # TODO: Unused
        self.end = end
        self.argc = argc
        self.argv = argv

        # Block declaration:
        self.block = True


    def __str__(self):
        if self.namespace == "":
            return "function " + self.name + "(" + str(ConcatComma(self.argv)) + ")"
        else:
            return "function " + self.namespace + "::" + self.name + "(" + str(ConcatComma(self.argv)) + ")"


'''
TorqueScript if statement
'''
class If(Node):
    '''
    Constructs an If object
    @param  condition   Condition of if statement
    '''
    def __init__(self, condition):
        # Inherit characteristics from Node:
        super().__init__()

        self.condition = condition

        # Handle to else statement, if any:
        self.elseHandle = None

        # Block declaration:
        self.block = True


    def __str__(self):
        return "if (" + str(self.condition) + ")"
    

'''
TorqueScript object creation
'''
class ObjCreation(Node):
    '''
    Constructs ObjCreation object
    @param  parentName  Name of parent object
    @param  mistery     Some value I do not know what is about
    @param  argv        List of arguments passed to object
    '''
    def __init__(self, parentName, is_dblock, is_internal, is_message, argv):
        # Inherit characteristics from Node:
        super().__init__()

        self.parentName = parentName
        self.is_dblock = is_dblock

        # First argument is object type:
        self.objType = argv[0]
        self.argv = argv[1:]

        if self.argv and self.parentName:
            # Second argument is object name:
            self.argv[0] = str(self.argv[0]) + " : " + self.parentName
        else:
            self.argv[0] = str(self.argv[0])

        # Block declaration:
        self.block = True
        self.is_object = True


    def __str__(self):
        if self.is_dblock:
            return "datablock " + self.objType + "( " + str(ConcatComma(self.argv)) + " )"
        else:
            return "new " + self.objType + "( " + str(ConcatComma(self.argv)) + " )"


'''
TorqueScript return statement
'''
class Return(Node):
    '''
    Constructs a Return object
    @param  value   Return value
    '''
    def __init__(self, value):
        # Inherit characteristics from Node:
        super().__init__()

        self.value = value

    def __str__(self):
        if self.value:
            return "return " + str(self.value)
        else:
            return "return"


'''
TorqueScript while statement
'''
class While(Node):
    '''
    Constructs an While object
    @param  condition   Condition of while statement
    '''
    def __init__(self, condition):
        # Inherit characteristics from Node:
        super().__init__()

        self.condition = condition

        # Block declaration:
        self.block = True


    def __str__(self):
        return "while (" + str(self.condition) + ")"


'''
Tree of TorqueScript statements (Nodes)
'''
class Tree:
    '''
    Constructs a Tree object
    @param  root    Root node of tree
    '''
    def __init__(self, root):
        self.root = root

        # Pointer to node being currently manipulated:
        self.curNode = root
        # Characters to be prepended to each line of code for indentation:
        self.indent = ""

    '''
    Appends a node to the current node of the tree
    @param  node    Node to be appended
    '''
    def append(self, node):
        self.curNode.append(node)

    '''
    Replaces the current node by the given one
    @param  new     Node to replace the current one by
    '''
    def replace(self, new):
        old = self.curNode

        parent = old.parent
        children = old.children

        # Replace reference on parent's children list:
        if parent is not None:
            parent.children[parent.children.index(old)] = new

        # Replace references on children's parent field:
        for child in children:
            child.parent = new

        new.parent = parent
        new.children = children

        self.curNode = new

    '''
    Rewinds tree (resets current node to root)
    '''
    def rewind(self):
        self.curNode = self.root

    '''
    Focuses (change current node pointer to) on child node at given index
    @param  idx     Index of child on children list (default -1 - last appended child)
    '''
    def focusChild(self, idx=-1):
        self.curNode = self.curNode.children[idx]

    '''
    Focuses (change current node pointer to) on parent node
    '''
    def focusParent(self):
        self.curNode = self.curNode.parent

    '''
    Retrieves focused (current) node
    '''
    def getFocused(self):
        return self.curNode

    '''
    Formats tree as text (source code)
    @param  sink    Stream to dump output to (default stdout)
    '''
    def format(self, sink=stdout):
        # Get current node:
        thisNode = self.curNode

        # Print indented line of code:
        print(self.indent + str(thisNode), end="", file=sink)

        # If declares a block:
        if thisNode.block:
            # Print newline:
            print("", file=sink)
            # Open brackets:
            print(self.indent + "{", file=sink)
            # Indent:
            self.indent += "\t" * thisNode.block
        else:
            print(";", file=sink)

        # Call recursively for all children:
        for child in thisNode.children:
            self.curNode = child
            self.format(sink=sink)

        # If declares a block:
        if thisNode.block:
            # Unindent:
            self.indent = self.indent[:-thisNode.block]
            # Close brackets (objects need "};" ) :
            if thisNode.is_object:
                print(self.indent + "};", file=sink)
            else:
                print(self.indent + "}", file=sink)

        # Restore current node:
        self.curNode = thisNode
