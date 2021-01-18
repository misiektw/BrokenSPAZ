from sys import stdout
import logging

from core import dso, torque
from core.opcodes import OPCODES, opByName

'''
Class for simulating the data structure used by Torque VM
'''
class StringStack(list):
    '''
    Loads a string into the top of the stack (does not change top pointer)
    @param  string  String to be loaded
    '''
    def load(self, string):
        if self:
            self[-1] = string
        else:
            self.append(string)

    '''
    Advances the top pointer to after the string currenty pointed at (push == load + advance)
    @param  ch  Character to be appended to the end of current string
    '''
    def advance(self, ch=None):
        if ch is not None:
            if ch == "\n":
                # Use Torque "NL" operator:
                self.append(torque.ConcatNl([self.pop()]))
            elif ch == "\t":
                # Use Torque "TAB" operator:
                self.append(torque.ConcatTab([self.pop()]))
            elif ch == " ":
                # Use Torque "SPC" operator:
                self.append(torque.ConcatSpc([self.pop()]))
            elif ch == ",":
                # Separate current string and the one to be loaded with a comma:
                self.append(torque.ConcatComma([self.pop()]))
            elif ch == "\x00":
                # Torque only separates strings in the stack with a null byte if they are going to be compared:
                self.append(torque.StringEqual([self.pop()]))
            else:
                # Use Torque "@" operator:
                self.append(torque.Concat([self.pop(), "\"" + ch + "\""]))

        # If no char is given, the strings being pushed are either for a concatenation, or for an array access
        # Method rewin takes care of the rest

        # To be overwritten by next load:
        self.append(None)

    '''
    Rewinds top of stack, joining the two strings at the top into a single structure at the top
    '''
    def rewind(self):
        s2 = self.pop()
        s1 = self.pop()

        # In summary:
        #   If the operation was defined in method advance, take the loaded string and append it to the operands
        #   If both are normal strings, operation is unknown at this point, so just join them in a list
        #   If at least one of them is a list (probably because of consecutive rewinds):
        #       Append to operands, if there is a concatenation operation involved
        #       Join everything into one single list otherwise

        if isinstance(s2, list):
            if isinstance(s1, list):
                self.append(s1 + s2) # list + list
            elif hasattr(s1, "isString") and s1.isString:
                s1.operands.append(torque.Concat(s2)) # concat(x, concat(s2))
                self.append(s1)
            else:
                s2.insert(0, s1) # list(s1, x)
                self.append(s2)
        else:
            if isinstance(s1, list):
                s1.append(s2) # list(x, s2)
                self.append(s1)
            elif hasattr(s1, "isString") and s1.isString:
                s1.operands.append(s2) # concat(x, s2)
                self.append(s1)
            else:
                self.append([s1, s2]) # list(s1, s2)

    '''
    Writes null byte at the top (discarding whatever was there), then rewinds to previous top
    '''
    def terminateRewind(self):
        # Effectively a pop that discards the value:
        self.pop()


'''
Methods for decoding a DSO file's bytecode
'''
class Decoding:
    '''
    Constructs a Decoding object
    @param  dsoFile     Parsed dso.File object to be decoded
    @param  inFunction  Indicates if start is inside a function and at which depth (for partial decompilation only)
    @param  offset      Start offset of bytecode (for partial decompilation only)
    '''
    def __init__(self, dsoFile, inFunction=0, offset=0):
        self.file = dsoFile
        self.inFunction = inFunction
        self.in_object = 0 # if inside object, with nesting ++
        self.offset = offset

        # For storing current variable, object and field:
        self.curvar = None
        self.curobj = None
        self.curfield = None

        # Arument frame for function calls and object creations:
        self.argFrame = []

        # Stacks for each data type:
        self.binStack = []
        self.intStack = []
        self.fltStack = []
        self.strStack = StringStack()

        # Stack of torque.Tree:
        self.treeStack = []

        # Main tree of file:
        self.tree = torque.Tree(torque.File(self.file.name))
        
        # Stack of opcode calls performed:
        self.callStack = []

        # Instruction pointer:
        self.ip = 0

        # Dictionary for storing which addresses mark the end of code blocks and from which syntatic structures:
        self.endBlock = {}

    '''
    Retrieves next code of bytecode
    '''
    def getCode(self):
        return self.file.byteCode.getCode()

    '''
    Check next code of bytecode without advancing IP
    '''
    def chkNextCode(self):
        return self.file.byteCode.lookupUnpackUint8()

    '''
    Retrieves next data of bytecode as uint
    '''
    def getUint(self):
        return self.file.byteCode.getUint()

    '''
    Retrieves next data of bytecode as string offset
    '''
    def getStringOffset(self):
        return self.file.byteCode.getStringOffset()

    '''
    Retrieves string value at top of stack. (For compat with compileEval.cc)
    '''
    def getStringValue(self):
        if self.strStack:
            return self.strStack[-1]
        else:
            return None

    '''
    Retrieves string of Global String Table
    @param  offset      Offset of string to be retrieved
    @param  encoding    Encoding of the string
    '''
    def getGlobalStringByOffset(self, offset, encoding="utf-8"):
        return self.file.globalStringTable[offset].decode(encoding)

    '''
    Retrieves next data of bytecode as string offset then retrieves global string at that offset
    @param  encoding    Encoding of the string
    '''
    def getGlobalString(self, encoding="utf-8"):
        return self.getGlobalStringByOffset(self.getStringOffset(), encoding)

    '''
    Retrieves string of Function String Table
    @param  offset      Offset of string to be retrieved
    @param  encoding    Encoding of the string
    '''
    def getFunctionStringByOffset(self, offset, encoding="utf-8"):
        return self.file.functionStringTable[offset].decode(encoding)

    '''
    Retrieves next data of bytecode as string offset then retrieves function string at that offset
    @param  encoding    Encoding of the string
    '''
    def getFunctionString(self, encoding="utf-8"):
        return self.getFunctionStringByOffset(self.getStringOffset(), encoding)

    '''
    Retrieves string of string table accordingly to the context
    @param  offset      Offset of string to be retrieved
    @param  encoding    Encoding of the string
    '''
    def getStringByOffset(self, offset, encoding="utf-8"):
        if self.file.byteCode.in_patchlocks:
            return self.getGlobalStringByOffset(offset, encoding)
        if self.inFunction and self.file.functionStringTable:
            try:
                return self.getFunctionStringByOffset(offset, encoding)
            except KeyError:
                logging.warning(f'String of offset {offset} was not in FunctionTable, trying global.')
                # some variables in function are stored in global table
                return self.getGlobalStringByOffset(offset, encoding)
        else:
            return self.getGlobalStringByOffset(offset, encoding)

    '''
    Retrieves next data of bytecode as string offset then retrieves string at that offset
    @param  encoding    Encoding of the string
    '''
    def getString(self, encoding="utf-8"):
        return self.getStringByOffset(self.getStringOffset(), encoding)

    '''
    Replaces global string at given offset by given string
    @param  offset      Offset of string to be set
    @param  string      String to replace with
    @param  encoding    Encoding of the string
    '''
    def setGlobalString(self, offset, string, encoding="utf-8"):
        self.file.globalStringTable[offset] = string.encode(encoding)

    '''
    Replaces function string at given offset by given string
    @param  offset      Offset of string to be set
    @param  string      String to replace with
    @param  encoding    Encoding of the string
    '''
    def setFunctionString(self, offset, string, encoding="utf-8"):
        self.file.functionStringTable[offset] = string.encode(encoding)

    '''
    Replaces string at given offset by given string
    @param  offset      Offset of string to be set
    @param  string      String to replace with
    @param  encoding    Encoding of the string
    '''
    def setString(self, offset, string, encoding="utf-8"):
        if self.inFunction and self.file.functionStringTable:
            return self.setFunctionString(offset, string, encoding)
        else:
            return self.setGlobalString(offset, string, encoding)

    '''
    Retrieves next data of bytecode as float offset
    '''
    def getFloatOffset(self):
        return self.file.byteCode.getFloatOffset()

    '''
    Retrieves float of Global Float Table
    @param  offset  Offset of float to be retrieved
    '''
    def getGlobalFloatByOffset(self, offset):
        return self.file.globalFloatTable[offset]

    '''
    Retrieves next data of bytecode as float offset then retrieves global float at that offset
    '''
    def getGlobalFloat(self):
        return self.getGlobalFloatByOffset(self.getFloatOffset())

    '''
    Retrieves float of Function Float Table
    @param  offset  Offset of float to be retrieved
    '''
    def getFunctionFloatByOffset(self, offset):
        return self.file.functionFloatTable[offset]

    '''
    Retrieves next data of bytecode as float offset then retrieves function float at that offset
    '''
    def getFunctionFloat(self):
        return self.getFunctionFloatByOffset(self.getFloatOffset())

    '''
    Retrieves float of float table accordingly to the context
    @param  offset  Offset of float to be retrieved
    '''
    def getFloatByOffset(self, offset):
        if self.inFunction and self.file.functionFloatTable:
            return self.getFunctionFloatByOffset(offset)
        else:
            return self.getGlobalFloatByOffset(offset)

    '''
    Retrieves next data of bytecode as float offset then retrieves float at that offset
    '''
    def getFloat(self):
        return self.getFloatByOffset(self.getFloatOffset())

    '''
    Converts given code index into byte index
    @param  code    Code index to be converted
    '''
    def getByteIndex(self, code):
        return self.file.byteCode.idxTable[code]

    '''
    Retrieves index of next byte to be read
    '''
    def getCurByteIndex(self):
        return self.file.byteCode.pointer

    '''
    Records Torque code block structure and its end address
    @param  key     Offset of end of code block (key of dictionary)
    @param  val     core.torque object which contains the code block (value to be appended)
    '''
    def recordEndOfBlock(self, key, val):
        if key not in self.endBlock:
            self.endBlock[key] = []

        self.endBlock[key].append(val)

    '''
    Dumps bytecode of current instruction (assuming all its parameters have been read already)
    '''
    def dumpInstruction(self):
        return self.file.byteCode.dump(self.ip, self.file.byteCode.pointer)

    '''
    Routine called for OP_FUNC_DECL (declare a function)

    Instantiates a torque.FuncDecl object, appends it to the tree and focuses on it
    '''
    def opFuncDecl(self):
        # Get function name:
        funcName = self.getGlobalString()

        # Get function namespace:
        offset = self.getStringOffset()

        namespace = self.getGlobalStringByOffset(offset) if offset else ""

        # Get function package:
        # TODO: Should we use this somewhere?
        package = self.getGlobalString()

        # Get boolean indicating if function has body:
        # TODO: Should we use this somewhere?
        hasBody = self.getCode()

        # Get end of function declaration (first instruction after its end):
        end = self.getByteIndex(self.getCode())

        # Get argc of function (number of arguments):
        argc = self.getCode()

        
        # Get argv of function (list of arguments):
        argv = []
        for _ in range(0, argc): 
            offset = self.getStringOffset()
            string = self.getGlobalStringByOffset(offset)
            # Mark parameter as local variable if not already done:
            if string[0] != "%":
                self.setGlobalString(offset, "%" + string)
            argv.append(string)

        # Instantiate object:
        decl = torque.FuncDecl(funcName, namespace, package, hasBody, end, argc, argv)

        # Store end of declaration block:
        self.recordEndOfBlock(end, decl)

        # Append object to tree:
        self.tree.append(decl)

        # Focus on object (next instructions are in the scope of this declaration):
        self.tree.focusChild()

        # Indicate flow has entered another function:
        self.inFunction += 1

        logging.debug("IP: {}: {}: Declare function: {}, {}, {}, {}, {}, {}".format(
            self.ip, self.dumpInstruction(), funcName, namespace, package, hasBody, end, argc))

    '''
    Routine called for OP_CREATE_OBJECT (create an an object)

    Instantiates a torque.ObjCreation object, creates a new tree and appends it to the root
    '''
    def opCreateObject(self):
        # Get parent object:
        parent = self.getString()

        #Mistery codes demistified
        # "datablock" instead of "new"
        is_dblock   = self.getUint()
        is_internal = self.getCode() # not used
        is_message  = self.getCode() # not used
        
        # Get end of object creation (first instruction after its end):
        end = self.getByteIndex(self.getCode())

        # Get argv of object (list of arguments):
        argv = self.argFrame.pop()

        # Concated variables/strings are passed as lists, because OP_ADVANCE_STR is called earlier.
        for i, arg in enumerate(argv):
            if i>0 and isinstance(arg, list):
                argv[i] = torque.Concat(arg)

        # Store current tree on stack:
        self.treeStack.append(self.tree)

        # Instantiate object and add it to the root of a new tree:
        self.tree = torque.Tree(torque.ObjCreation(parent, is_dblock, is_internal, is_message, argv))
        self.in_object += 1
        
        logging.debug("IP: {}: {}: Create object {}: parent {}, {}, end {}".format(
            self.ip, self.dumpInstruction(), self.in_object, parent, (is_dblock, is_internal, is_message), end))

    '''
    Routine called for OP_ADD_OBJECT (add object to stack)

    Adds object to the int stack
    '''
    def opAddObject(self):
        # Get boolean value:
        placeAtRoot = self.getCode()

        if placeAtRoot:
            # Overwrite value pushed before its creation by it:
            self.intStack[-1] = self.tree.root
        else:
            # Push it to stack:
            self.intStack.append(self.tree.root)

        logging.debug("IP: {}: {}: Add object".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_END_OBJECT (end object creation)

    Restores previous tree
    '''
    def opEndObject(self):
        # Restore previous tree:
        self.tree = self.treeStack.pop()

        # If object has no body:
        if self.callStack[-2] is Decoding.opCreateObject and self.callStack[-1] is Decoding.opAddObject:
            # Do not create a block of code:
            self.intStack[-1].block = 0

        # Get boolean value:
        placeAtRoot = self.getCode()

        if not placeAtRoot:
            # Append the object to the tree already since it will not be assigned to anything:
            self.tree.append(self.intStack.pop())

        self.in_object -= 1
        logging.debug("IP: {}: {}: End object {}".format(self.ip, self.dumpInstruction(), self.in_object))


    '''
    Routine called for OP_JMPIFFNOT (jump if condition retrieved from float stack not met)

    Appends a torque.If if its a forward jump or updates/replaces current node by a torque.While if it is a backward jump
    '''
    def opJmpiffnot(self):
        # Get jump target:
        target = self.getByteIndex(self.getCode()) - self.offset

        # Get branch condition:
        if self.binStack:
            condition = self.binStack.pop()
            condition.operands.append(self.fltStack.pop())
        else:
            condition = self.fltStack.pop()

        # If forward jump:
        if target > self.getCurByteIndex():
            # Assume it is an If:
            statement = torque.If(condition)

            # Store target as end of If block:
            self.recordEndOfBlock(target, statement)

            # Append object to tree:
            self.tree.append(statement)

            # Focus on it:
            self.tree.focusChild()
        # If backward jump:
        elif target < self.getCurByteIndex():
            if isinstance(self.tree.getFocused(), torque.While):
                # If while statement was compiled as unconditional jump + conditional jump, condition is not set by now:
                self.tree.getFocused().condition = torque.Not([condition])
            else:
                # If while statement was compiled as conditional jump + conditional jump, it was assumed it was an if:
                if condition != self.tree.getFocused().condition:
                    raise ValueError("Loop condition mismatch: {}: {}: {}".format(condition, self.tree.getFocused().condition, target))

                # Replace if by while statement (invert condition):
                self.tree.replace(torque.While(torque.Not([condition])))

        logging.debug("IP: {}: {}: Jump if float condition not met to: {}".format(self.ip, self.dumpInstruction(), target))

    '''
    Routine called for OP_JMPIFNOT (jump if condition retrieved from int stack not met)

    Appends a torque.If if its a forward jump or updates/replaces current node by a torque.While if it is a backward jump
    '''
    def opJmpifnot(self):
        # Get jump target:
        target = self.getByteIndex(self.getCode()) - self.offset

        # Get branch condition:
        if self.binStack:
            condition = self.binStack.pop()
            condition.operands.append(self.intStack.pop())
        else:
            condition = self.intStack.pop()

        # If forward jump:
        if target > self.getCurByteIndex():
            # Assume it is an If:
            statement = torque.If(condition)

            # Store target as end of If block:
            self.recordEndOfBlock(target, statement)

            # Append object to tree:
            self.tree.append(statement)

            # Focus on it:
            self.tree.focusChild()
        # If backward jump:
        elif target < self.getCurByteIndex():
            if isinstance(self.tree.getFocused(), torque.While):
                # If while statement was compiled as unconditional jump + conditional jump, condition is not set by now:
                self.tree.getFocused().condition = torque.Not([condition])
            else:
                # If while statement was compiled as conditional jump + conditional jump, it was assumed it was an if:
                if condition != self.tree.getFocused().condition:
                    raise ValueError("Loop condition mismatch: {}: {}: {}".format(condition, self.tree.getFocused().condition, target))

                # Replace if by while statement (invert condition):
                self.tree.replace(torque.While(torque.Not([condition])))

        logging.debug("IP: {}: {}: Jump if uint/boolean condition not met to: {}".format(self.ip, self.dumpInstruction(), target))

    '''
    Routine called for OP_JMPIFF (jump if condition retrieved from float stack met)

    Appends a torque.If if its a forward jump or updates/replaces current node by a torque.While if it is a backward jump
    '''
    def opJmpiff(self):
        # Get jump target:
        target = self.getByteIndex(self.getCode()) - self.offset

        # Get branch condition:
        if self.binStack:
            condition = self.binStack.pop()
            condition.operands.append(self.fltStack.pop())
        else:
            condition = self.fltStack.pop()

        # If forward jump:
        if target > self.getCurByteIndex():
            # Assume it is an If:
            statement = torque.If(torque.Not([condition]))

            # Store target as end of If block:
            self.recordEndOfBlock(target, statement)

            # Append object to tree:
            self.tree.append(statement)

            # Focus on it:
            self.tree.focusChild()
        # If backward jump:
        elif target < self.getCurByteIndex():
            if isinstance(self.tree.getFocused(), torque.While):
                # If while statement was compiled as unconditional jump + conditional jump, condition is not set by now:
                self.tree.getFocused().condition = condition
            else:
                # If while statement was compiled as conditional jump + conditional jump, it was assumed it was an if:
                if condition != self.tree.getFocused().condition:
                    raise ValueError("Loop condition mismatch: {}: {}: {}".format(condition, self.tree.getFocused().condition, target))

                # Replace if by while statement:
                self.tree.replace(torque.While(condition))

        logging.debug("IP: {}: {}: Jump if float condition not met to: {}".format(self.ip, self.dumpInstruction(), target))

    '''
    Routine called for OP_JMPIF (jump if condition retrieved from int stack met)

    Appends a torque.If if its a forward jump or updates/replaces current node by a torque.While if it is a backward jump
    '''
    def opJmpif(self):
        # Get jump target:
        target = self.getByteIndex(self.getCode()) - self.offset

        # Get branch condition:
        if self.binStack:
            condition = self.binStack.pop()
            condition.operands.append(self.intStack.pop())
        else:
            condition = self.intStack.pop()

        # If forward jump:
        if target > self.getCurByteIndex():
            # Assume it is an If:
            statement = torque.If(torque.Not([condition]))

            # Store target as end of If block:
            self.recordEndOfBlock(target, statement)

            # Append object to tree:
            self.tree.append(statement)

            # Focus on it:
            self.tree.focusChild()
        # If backward jump:
        elif target < self.getCurByteIndex():
            if isinstance(self.tree.getFocused(), torque.While):
                # If while statement was compiled as unconditional jump + conditional jump, condition is not set by now:
                self.tree.getFocused().condition = condition
            else:
                # If while statement was compiled as conditional jump + conditional jump, it was assumed it was an if:
                if condition != self.tree.getFocused().condition:
                    raise ValueError("Loop condition mismatch: {}: {}: {}".format(condition, self.tree.getFocused().condition, target))

                # Replace if by while statement:
                self.tree.replace(torque.While(condition))

        logging.debug("IP: {}: {}: Jump if uint/boolean condition met to: {}".format(self.ip, self.dumpInstruction(), target))

    '''
    Routine called for OP_JMP (jump unconditionally)

    Appends either a torque.Else, a torque.Break or a torque.While to the tree
    '''
    def opJmp(self):
        target = self.getByteIndex(self.getCode()) - self.offset

        # If forward jump:
        if target > self.getCurByteIndex():
            # If the current code block ends on this instruction:
            if self.getCurByteIndex() in self.endBlock and self.tree.getFocused() in self.endBlock[self.getCurByteIndex()]:
                # If the target is right after the end of a block, it is a break from a loop:
                if target in self.endBlock:
                    statement = torque.Break()
                    self.tree.append(statement)
                # Otherwise, it is an else:
                else:
                    statement = torque.Else()
                    self.recordEndOfBlock(target, statement)
                    # Associate to the current if statement
                    self.tree.getFocused().elseHandle = statement
            else:
                # Since it is an unconditional branch, condition is unknown at this point:
                statement = torque.While("")
                self.recordEndOfBlock(target, statement)
                self.tree.append(statement)
                self.tree.focusChild()
        else:
            raise NotImplementedError("Backward jump not implemented for OP_JMP")

        logging.debug("IP: {}: {}: Jump to: {}".format(self.ip, self.dumpInstruction(), target))

    '''
    Routine called for OP_JMPIFNOT_NP (jump if boolean condition not met - I believe this is used for && operation short-circuit)

    Retrieves a boolean condition from the int stack and appends it as operand of a torque.And operation
    '''
    def opJmpifnotNp(self):
        target = self.getByteIndex(self.getCode()) - self.offset

        if self.binStack:
            # Get previous condition:
            previousCond = self.binStack.pop()
            previousCond.operands.append(self.intStack.pop())
            self.binStack.append(torque.And([previousCond]))
        else:
            self.binStack.append(torque.And([self.intStack.pop()]))

        logging.debug("IP: {}: {}: Jump if binary condition not met to: {}".format(self.ip, self.dumpInstruction(), target))

    '''
    Routine called for OP_JMPIF_NP (jump if boolean condition met - I believe this is used for || operation short-circuit)

    Retrieves a boolean condition from the int stack and appends it as operand of a torque.Or operation
    '''
    def opJmpifNp(self):
        target = self.getByteIndex(self.getCode()) - self.offset

        if self.binStack:
            # Get previous condition:
            previousCond = self.binStack.pop()
            previousCond.operands.append(self.intStack.pop())
            self.binStack.append(torque.Or([previousCond]))
        else:
            self.binStack.append(torque.Or([self.intStack.pop()]))

        logging.debug("IP: {}: {}: Jump if binary condition met to: {}".format(self.ip, self.dumpInstruction(), target))

    '''
    Routine called for OP_RETURN (return from function/script)

    Appends a torque.Return object to the tree
    '''
    def opReturn(self):
        # Omit last byte. In v.41 its always return.
        if self.ip < self.file.byteCode.binLen-1:
            # If a return value was loaded:
            ret = self.getStringValue()
            
            #String concat (@) doesnt have OP before return. So lets do it here?
            if isinstance(ret, list):
                while (len(ret)>1):
                    if isinstance(ret[1], str):
                        ret[1]=torque.Concat(ret[:2])
                        ret = ret[1:]
                ret=ret[0]
            
            if len(self.strStack)==0  \
                and isinstance(self.tree.curNode, torque.FuncDecl) \
                and self.tree.curNode.end == self.ip+1:
                    pass    #skip return if empty and function ends on next ip
            else:
                self.tree.append(torque.Return(ret))
        
            # Torque 1.7.5 (dso v41) seems to always puts 2 return codes even if its not needed.
            # Try to discard second OP_RETURN when its not needed.
            
            if self.chkNextCode() == opByName['OP_RETURN']: 
                if not isinstance(self.tree.curNode , torque.If):
                    if not isinstance(self.tree.curNode, torque.Else):
                        self.getCode() # just skip code
                    else:
                        #Fine, but dont repeat last stack value
                        self.strStack.pop()

       

        logging.debug("IP: {}: {}: Return".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_CMPEQ (compare if floats are equal)

    Appends a torque.Equal operation to the int stack
    '''
    def opCmpeq(self):
        self.intStack.append(torque.Equal([self.fltStack.pop(), self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Compare if equal".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_CMPLT (compare if a float is less than another one)

    Appends a torque.Less operation to the int stack
    '''
    def opCmplt(self):
        self.intStack.append(torque.Less([self.fltStack.pop(), self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Compare if less".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_CMPLE (compare if a float is less than or equal to another one)

    Appends a torque.LessOrEqual operation to the int stack
    '''
    def opCmple(self):
        self.intStack.append(torque.LessOrEqual([self.fltStack.pop(), self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Compare if less or equal".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_CMPGR (compare if a float is greater than another one)

    Appends a torque.Greater operation to the int stack
    '''
    def opCmpgr(self):
        self.intStack.append(torque.Greater([self.fltStack.pop(), self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Compare if greater".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_CMPGE (compare if a float is greater than or equal to another one)

    Appends a torque.GreaterOrEqual operation to the int stack
    '''
    def opCmpge(self):
        self.intStack.append(torque.GreaterOrEqual([self.fltStack.pop(), self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Compare if greater or equal".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_CMPNE (compare if a float is not equal to another one)

    Appends a torque.NotEqual operation to the int stack
    '''
    def opCmpne(self):
        self.intStack.append(torque.NotEqual([self.fltStack.pop(), self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Compare if not equal".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_XOR (perform a bitwise xor operation between two integers)

    Appends a torque.Xor operation to the int stack
    '''
    def opXor(self):
        self.intStack.append(torque.Xor([self.intStack.pop(), self.intStack.pop()]))

        logging.debug("IP: {}: {}: Bitwise xor".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_MOD (perform a modulo operation between two integers)

    Appends a torque.Mod operation to the int stack
    '''
    def opMod(self):
        self.intStack.append(torque.Mod([self.intStack.pop(), self.intStack.pop()]))

        logging.debug("IP: {}: {}: Get modulo".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_BITAND (perform a bitwise and operation between two integers)

    Appends a torque.BitAnd operation to the int stack
    '''
    def opBitand(self):
        self.intStack.append(torque.BitAnd([self.intStack.pop(), self.intStack.pop()]))

        logging.debug("IP: {}: {}: Bitwise and".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_BITOR (perform a bitwise or operation between two integers)

    Appends a torque.BitOr operation to the int stack
    '''
    def opBitor(self):
        self.intStack.append(torque.BitOr([self.intStack.pop(), self.intStack.pop()]))

        logging.debug("IP: {}: {}: Bitwise or".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_NOT (negate an integer)

    Appends a torque.Not operation to the int stack
    '''
    def opNot(self):
        self.intStack.append(torque.Not([self.intStack.pop()]))

        logging.debug("IP: {}: {}: Negate uint/boolean value".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_NOTF (negate a float)

    Appends a torque.Not operation to the int stack
    '''
    def opNotf(self):
        self.intStack.append(torque.Not([self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Negate float value".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_ONESCOMPLEMENT (perform an one's complement operation between two integers)

    Appends a torque.Complement operation to the int stack
    '''
    def opOnescomplement(self):
        self.intStack.append(torque.Complement([self.intStack.pop(), self.intStack.pop()]))

        logging.debug("IP: {}: {}: Bitwise complement".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_SHR (shift an integer to the right by another integer value)

    Appends a torque.ShiftRight operation to the int stack
    '''
    def opShr(self):
        self.intStack.append(torque.ShiftRight([self.intStack.pop(), self.intStack.pop()]))

        logging.debug("IP: {}: {}: Shift right".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_SHL (shift an integer to the left by another integer value)

    Appends a torque.ShiftLeft operation to the int stack
    '''
    def opShl(self):
        self.intStack.append(torque.ShiftLeft([self.intStack.pop(), self.intStack.pop()]))

        logging.debug("IP: {}: {}: Shift left".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_AND (perform a boolean and operation between two integers)

    Appends a torque.And operation to the int stack
    '''
    def opAnd(self):
        self.intStack.append(torque.And([self.intStack.pop(), self.intStack.pop()]))

        logging.debug("IP: {}: {}: Logical and".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_OR (perform a boolean or operation between two integers)

    Appends a torque.Or operation to the int stack
    '''
    def opOr(self):
        self.intStack.append(torque.Or([self.intStack.pop(), self.intStack.pop()]))

        logging.debug("IP: {}: {}: Logical or".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_ADD (add two floats)

    Appends a torque.Add operation to the float stack
    '''
    def opAdd(self):
        #Deal with ++ first
        if self.op_setcurvar_create and self.fltStack[-2] == 1:
            self.op_setcurvar_create = False
            self.fltStack.append(torque.AddPP([self.fltStack.pop(),self.fltStack.pop()]))
        else:
            self.fltStack.append(torque.Add([self.fltStack.pop(), self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Sum floats".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_SUB (subtract two floats)

    Appends a torque.Sub operation to the float stack
    '''
    def opSub(self):
        if self.op_setcurvar_create and self.fltStack[-2] == 1:
            self.op_setcurvar_create = False
            self.fltStack.append(torque.SubPP([self.fltStack.pop(),self.fltStack.pop()]))
        else:
            self.fltStack.append(torque.Sub([self.fltStack.pop(), self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Subtract floats".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_MUL (multiply two floats)

    Appends a torque.Mul operation to the float stack
    '''
    def opMul(self):
        self.fltStack.append(torque.Mul([self.fltStack.pop(), self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Multiply floats".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_DIV (divide one float by another)

    Appends a torque.Div operation to the float stack
    '''
    def opDiv(self):
        self.fltStack.append(torque.Div([self.fltStack.pop(), self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Divide floats".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_NEG (invert the sign of a float)

    Appends a torque.Neg operation to the float stack
    '''
    def opNeg(self):
        self.fltStack.append(torque.Neg([self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Invert sign of float".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_SETCURVAR (set name/symbol of current variable)

    Retrieves the symbol from the Global String Table and sets current variable to it
    '''
    def opSetcurvar(self):
        offset = self.getStringOffset()
        string = self.getGlobalStringByOffset(offset)
        self.op_setcurvar_create = False

        # This shouldnt be necessary? Variables are stored with $/% and may interfere with fields?
        if string[0] != "$" and string[0] != "%":
            if self.inFunction:
                # Append local variable prefix:
                string = "%" + string
            else:
                # Append global variable prefix:
                string = "$" + string

            # Save change:
            self.setGlobalString(offset, string)

        self.curvar = string
        self.curobj = None      # According to T2D compileEval.cc this is a must

        logging.debug("IP: {}: {}: Set current variable: {}".format(self.ip, self.dumpInstruction(), self.curvar))

    '''
    Routine called for OP_SETCURVAR_CREATE (set name/symbol of current variable)
    Retrieves the symbol from the Global String Table and sets current variable to it
    Edge cases: ++ operator generates this before opAdd

    '''

    def opSetcurvarCreate(self):
        offset = self.getStringOffset()
        string = self.getGlobalStringByOffset(offset)
        self.op_setcurvar_create = True

        self.curvar = string
        self.curobj = None      # According to T2D compileEval.cc this is a must

        logging.debug("IP: {}: {}: Set current variable (create): {}".format(self.ip, self.dumpInstruction(), self.curvar))

    '''
    Routine called for OP_SETCURVAR_ARRAY and OP_SETCURVAR_ARRAY_CREATE (set name/symbol and index of current array variable)

    Retrieves the symbol and index from string stack and append them to tree as torque.ArrayAccess
    '''
    def opSetcurvarArray(self):
        self.curvar = torque.ArrayAccess(self.strStack[-1])     # StringTable->insert(mBuffer + mStart);
        self.curobj = None      # According to T2D compileEval.cc this is a must

        logging.debug("IP: {}: {}: Set current array variable".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_SETCURVAR_ARRAY_CREATE (set name/symbol and index of current array variable)

    Retrieves the symbol and index from string stack and append them to tree as torque.ArrayAccess
    '''
    def opSetcurvarArrayCreate(self):
        self.curvar = torque.ArrayAccess(self.strStack[-1])     # StringTable->insert(mBuffer + mStart);
        # If it is ++ operator then remove it from tree, because previous assignment put it there
        # it happens in case of $Array[var++]/$Array[var--]
        arr_ind = self.curvar.operands[1]
        if isinstance(arr_ind, torque.AddPP) or isinstance(arr_ind, torque.AddPP):
            if arr_ind == self.tree.curNode.children[-1]:
                self.tree.curNode.children.pop()

        self.curobj = None      # According to T2D compileEval.cc this is a must

        logging.debug("IP: {}: {}: Set current array variable".format(self.ip, self.dumpInstruction()))


    '''
    Routine called for OP_LOADVAR_UINT (load current variable value to int stack)

    Appends current variable symbol to the int stack
    '''
    def opLoadvarUint(self):
        self.intStack.append(self.curvar)

        logging.debug("IP: {}: {}: Load variable of type uint: {}".format(self.ip, self.dumpInstruction(), self.curvar))

    '''
    Routine called for OP_LOADVAR_FLT (load current variable value to float stack)

    Appends current variable symbol to the float stack
    '''
    def opLoadvarFlt(self):
        self.fltStack.append(self.curvar)

        logging.debug("IP: {}: {}: Load variable of type float: {}".format(self.ip, self.dumpInstruction(), self.curvar))

    '''
    Routine called for OP_LOADVAR_STR (load current variable value to string stack)

    Appends current variable symbol to the string stack
    '''
    def opLoadvarStr(self):
        self.strStack.load(self.curvar)

        logging.debug("IP: {}: {}: Load variable of type string: {}".format(self.ip, self.dumpInstruction(), self.curvar))

    '''
    Routine called for OP_SAVEVAR_UINT (save uint value into current variable)

    Retrieves the value from int stack and appends a torque.Assignment object to the tree
    '''
    def opSavevarUint(self):
        name = self.curvar
        value = self.intStack[-1]

        self.curvar = (name, value)

        self.tree.append(torque.Assignment(name, value))

        logging.debug("IP: {}: {}: Save uint value into variable".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_SAVEVAR_FLT (save float value into current variable)

    Retrieves the value from float stack and appends a torque.Assignment object to the tree
    '''
    def opSavevarFlt(self):
        name = self.curvar
        value = self.fltStack[-1]

        self.curvar = (name, value)

        if self.op_setcurvar_create and (isinstance(value, torque.AddPP) or isinstance(value, torque.SubPP)):
            # ++/-- operators are compiled twice
            pass
        else:
            self.tree.append(torque.Assignment(name, value))

        logging.debug("IP: {}: {}: Save float value into variable".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_SAVEVAR_STR (save string value into current variable)

    Retrieves the value from string stack and appends a torque.Assignment object to the tree
    '''
    def opSavevarStr(self):
        name = self.curvar
        
        value = self.getStringValue()

        if isinstance(value, list):
            value = torque.Concat(value)

        self.curvar = (name, value)

        self.tree.append(torque.Assignment(name, value))

        logging.debug("IP: {}: {}: Save string value into variable".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_SETCUROBJECT (set name/symbol of current object)

    Retrieves the symbol from the string stack and sets current object to it
    '''
    def opSetcurobject(self):
        self.curobj = self.getStringValue()

        logging.debug("IP: {}: {}: {}: Set current object to ".format(self.ip, self.dumpInstruction(), self.curobj))

    '''
    Routine called for OP_SETCUROBJECT_NEW (unset name/symbol of current object)

    Sets current object to None
    '''
    def opSetcurobjectNew(self):
        self.curobj = None

        logging.debug("IP: {}: {}: Set new current object".format(self.ip, self.dumpInstruction()))

    def opSetcurobjectNewInt(self):
        self.curobj = None

        logging.debug("IP: {}: {}: Set new current object".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_SETCURFIELD (set name/symbol of current object field)

    Retrieves the symbol from the Global String Table and sets current field to it
    '''
    def opSetcurfield(self):
        self.curfield = self.getGlobalString()

        logging.debug("IP: {}: {}: Set current field: {}".format(self.ip, self.dumpInstruction(), self.curfield))

    '''
    Routine called for OP_SETCURVAR_ARRAY (set name/symbol and index of current array field)

    Retrieves the symbol and index from string stack and append them to tree as torque.ArrayAccess
    '''
    def opSetcurfieldArray(self):
        self.curfield = torque.ArrayAccess([self.curfield, self.getStringValue()])

        logging.debug("IP: {}: {}: Set current array field".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_LOADFIELD_UINT (load current field value to int stack)

    Appends current field symbol to the int stack
    '''
    def opLoadfieldUint(self):
        if self.curobj:
            field = torque.FieldAccess([self.curobj, self.curfield])
            ##field = str(self.curobj) + '.' + str(self.curfield)
        else:
            field = self.curfield

        self.intStack.append(field)

        logging.debug("IP: {}: {}: Load field of type string: {}".format(self.ip, self.dumpInstruction(), field))

    '''
    Routine called for OP_LOADFIELD_FLT (load current field value to float stack)

    Appends current field symbol to the float stack
    '''
    def opLoadfieldFlt(self):
        if self.curobj:
            field = torque.FieldAccess([self.curobj, self.curfield])
            #field = str(self.curobj) + '.' + str(self.curfield)
        else:
            field = self.curfield
        self.fltStack.append(field)

        logging.debug("IP: {}: {}: Load field of type string: {}".format(self.ip, self.dumpInstruction(), field))

    '''
    Routine called for OP_LOADFIELD_STR (load current field value to string stack)

    Appends current field symbol to the string stack
    '''
    def opLoadfieldStr(self):
        if self.curobj:
            self.strStack.load(torque.FieldAccess([self.curobj, self.curfield]))
            #self.strStack.load(str(self.curobj) + '.' + str(self.curfield))
        else:
            self.strStack.load(self.curfield)

        logging.debug("IP: {}: {}: Load field (string): {} from object{}".format(self.ip, self.dumpInstruction(), self.curfield, self.curobj))
        '''
        case OP_LOADFIELD_STR:
            if(curObject) {
               val = curObject->getDataField(curField, curFieldArray);
               STR.setStringValue( val );  }
            else {
               // The field is not being retrieved from an object. Maybe it's
               // a special accessor?
               getFieldComponent( prevObject, prevField, prevFieldArray, curField, valBuffer, VAL_BUFFER_SIZE );
               STR.setStringValue( valBuffer ); }
        '''

    '''
    Routine called for OP_SAVEFIELD_UINT (save uint value into current field)

    Retrieves the value from int stack and appends a torque.Assignment object to the tree
    '''
    def opSavefieldUint(self):
        if self.curobj is None:
            # Assignment to field during object creation:
            name = self.curfield
        else:
            # Assignment to field of current object:
            name = torque.FieldAccess([self.curobj, self.curfield])

        value = self.intStack[-1]

        self.curfield = (name, value)

        self.tree.append(torque.Assignment(name, value))

        logging.debug("IP: {}: {}: Save uint value into field".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_SAVEFIELD_FLT (save float value into current field)

    Retrieves the value from float stack and appends a torque.Assignment object to the tree
    '''
    def opSavefieldFlt(self):
        if self.curobj is None:
            # Assignment to field during object creation:
            name = self.curfield
        else:
            # Assignment to field of current object:
            name = torque.FieldAccess([self.curobj, self.curfield])

        value = self.fltStack[-1]

        self.curfield = (name, value)

        self.tree.append(torque.Assignment(name, value))

        logging.debug("IP: {}: {}: Save float value into field".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_SAVEFIELD_STR (save string value into current field)

    Retrieves the value from string stack and appends a torque.Assignment object to the tree
    '''
    def opSavefieldStr(self):
        if self.curobj is None:
            # Assignment to field during object creation:
            name = self.curfield
        else:
            # Assignment to field of current object:
            name = torque.FieldAccess([self.curobj, self.curfield])

        value = self.getStringValue()

        self.curfield = (name, value)

        self.tree.append(torque.Assignment(name, value))

        logging.debug("IP: {}: {}: Save string value into field".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_STR_TO_UINT (convert string to uint)

    Pushes popped value from string stack into int stack
    '''
    def opStrToUint(self):
        self.intStack.append(self.getStringValue())

        logging.debug("IP: {}: {}: Add top of string into uint stack".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_STR_TO_FLT (convert string to float)

    Pushes popped value from string stack into float stack
    '''
    def opStrToFlt(self):
        self.fltStack.append(self.getStringValue())

        logging.debug("IP: {}: {}: Add top of string stack into float stack".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_STR_TO_NONE (discard string on top of stack)

    Pops top of string stack out
    '''
    def opStrToNone(self):
        popd = self.strStack.pop()

        # Return value being discarded means procedure call:
        if isinstance(popd, torque.FuncCall) and self.callStack[-1] is Decoding.opCallfunc:
            self.tree.append(popd)

        logging.debug("IP: {}: {}: Pop string out".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_FLT_TO_UINT (convert float to uint)

    Pushes popped value from float stack into int stack
    '''
    def opFltToUint(self):
        self.intStack.append(self.fltStack.pop())

        logging.debug("IP: {}: {}: Pop float into uint stack".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_FLT_TO_STR (convert float to string)

    Pushes popped value from float stack into string stack
    '''
    def opFltToStr(self):
        self.strStack.load(self.fltStack.pop())

        logging.debug("IP: {}: {}: Pop float into string stack".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_FLT_TO_NONE (discard float on top of stack)

    Pops top of float stack out
    '''
    def opFltToNone(self):
        self.fltStack.pop()

        logging.debug("IP: {}: {}: Pop float out".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_UINT_TO_FLT (convert uint to float)

    Pushes popped value from uint stack into float stack
    '''
    def opUintToFlt(self):
        self.fltStack.append(self.intStack.pop())

        logging.debug("IP: {}: {}: Pop uint into float stack".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_UINT_TO_STR (convert uint to string)

    Pushes popped value from uint stack into string stack
    '''
    def opUintToStr(self):
        # If there is a concatenation of boolean conditions in progress:
        if self.binStack:
            condition = self.binStack.pop()
            condition.operands.append(self.intStack.pop())
        else:
            condition = self.intStack.pop()

        self.strStack.load(condition)

        logging.debug("IP: {}: {}: Pop uint into string stack".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_UINT_TO_NONE (discard uint on top of stack)

    Pops top of uint stack out
    '''
    def opUintToNone(self):
        popd = self.intStack.pop()

        # Return value being discarded means object declared, but not assigned:
        if isinstance(popd, torque.ObjCreation) and self.callStack[-1] is Decoding.opEndObject:
            self.tree.append(popd)

        logging.debug("IP: {}: {}: Pop uint out".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_LOADIMMED_UINT (load uint into stack)

    Appends uint to stack
    '''
    def opLoadimmedUint(self):
        self.intStack.append(self.getUint())

        logging.debug("IP: {}: {}: Load uint: {}".format(self.ip, self.dumpInstruction(), self.intStack[-1]))

    '''
    Routine called for OP_LOADIMMED_FLT (load float into stack)

    Appends float to stack
    '''
    def opLoadimmedFlt(self):
        self.fltStack.append(self.getFloat())

        logging.debug("IP: {}: {}: Load float: {}".format(self.ip, self.dumpInstruction(), self.fltStack[-1]))

    '''
    Routine called for OP_LOADIMMED_STR (load string into stack)

    Appends string to stack
    '''
    def opLoadimmedStr(self):
        offset = self.getStringOffset()
        
        # Torque 1.7.5 compiler seems to be bugged. 
        # All numbers in fields and function calls are read with this OP.
        all_to_num = False
        fld_to_num = False

        try:
            if (self.in_object and fld_to_num) or all_to_num:
                # String table may contain numbers... so... untorque them...
                string = round(eval(self.getStringByOffset(offset)), ndigits=7) 
                # And since we know now its a number we can do some trimming
                if string == int(string):
                        string = int(string)
            else:
                raise Exception
        except:
            # Escaping might fail on some cases:
            try:
                    string = "\"" + self.getStringByOffset(offset, "unicode_escape") + "\""
            except UnicodeDecodeError:
                    string = "\"" + self.getStringByOffset(offset) + "\""

        self.strStack.load(string)

        logging.debug("IP: {}: {}: Load string: {}".format(self.ip, self.dumpInstruction(), self.getStringValue()))

    def opDocBlockStr(self):
        #TODO
        logging.warning('OP_DOCBLOCK_STR not implemented!')
        logging.debug("IP: {}: {}: Load string: {}".format(self.ip, self.dumpInstruction(), self.getStringValue()))

    '''
    Routine called for OP_LOADIMMED_IDENT (load "ident" (string) into stack)

    Appends string to stack
    '''
    def opLoadimmedIdent(self):
        offset = self.getStringOffset()
        
        # Escaping might fail on some cases:
        try:
            string = self.getStringByOffset(offset, "unicode_escape")
        except UnicodeDecodeError:
            string = self.getStringByOffset(offset)

        self.strStack.load(string)

        logging.debug("IP: {}: {}: Load string (ident): {}".format(self.ip, self.dumpInstruction(), self.getStringValue()))

    '''
    Routine called for OP_TAG_TO_STR (load "tagged" string into stack)

    Appends (global) string to stack
    '''
    def opTagToStr(self):
        self.strStack.load(self.getGlobalString())

        logging.debug("IP: {}: {}: Load tagged string: {}".format(self.ip, self.dumpInstruction(), self.getStringValue()))

    '''
    Routine called for OP_CALLFUNC and OP_CALLFUNC_RESOLVE (call function)

    Appends torque.FuncCall object to the tree
    '''
    def opCallfunc(self):
        funcName = self.getGlobalString()

        offset = self.getStringOffset()

        if offset == 0:
            # Just read the place reserved for offset and do nothing:
            namespace = ""
        else:
            namespace = self.getGlobalStringByOffset(offset)

        callType = self.getCode()

        argv = self.argFrame.pop()

        for i in range(0, len(argv)):
            if isinstance(argv[i], list):
                argv[i] = torque.Concat(argv[i])

        self.strStack.load(torque.FuncCall(funcName, namespace, callType, argv))

        logging.debug("IP: {}: {}: Call function: {}, {}, {}".format(self.ip, self.dumpInstruction(), funcName, namespace, callType))

    '''
    Routine called for OP_ADVANCE_STR (advance top pointer of stack to end of top string)

    Calls method advance from string stack
    '''
    def opAdvanceStr(self):
        self.strStack.advance()

        logging.debug("IP: {}: {}: Advance string on stack".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_ADVANCE_STR_APPENDCHAR (advance top pointer of stack to end of top string and append character)

    Calls method advance from string stack
    '''
    def opAdvanceStrAppendchar(self):
        self.strStack.advance(chr(self.getCode()))

        logging.debug("IP: {}: {}: Advance string on stack and append char".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_ADVANCE_STR_COMMA (advance top pointer of stack to end of top string and append comma)

    Calls method advance from string stack
    '''
    def opAdvanceStrComma(self):
        self.strStack.advance(",")

        logging.debug("IP: {}: {}: Advance string on stack and append comma".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_ADVANCE_STR_NUL (advance top pointer of stack to end of top string and append null byte)

    Calls method advance from string stack
    '''
    def opAdvanceStrNul(self):
        self.strStack.advance("\x00")

        logging.debug("IP: {}: {}: Advance string on stack (null)".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_REWIND_STR (rewind top pointer of stack to previous element)

    Calls method rewind from string stack
    '''
    def opRewindStr(self):
        self.strStack.rewind()

        logging.debug("IP: {}: {}: Rewind string stack".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_TERMINATE_REWIND_STR (discard top string then rewind top pointer of stack to previous element)

    Calls method terminateRewind from string stack
    '''
    def opTerminateRewindStr(self):
        self.strStack.terminateRewind()

        logging.debug("IP: {}: {}: Terminate and rewind string stack".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_COMPARE_STR (compare two strings)

    Retrieves torque.StringEqual operation from string stack and appends it to int stack
    '''
    def opCompareStr(self):
        s2 = self.strStack.pop()
        op = self.strStack.pop()

        op.operands.append(s2)

        self.intStack.append(op)

        logging.debug("IP: {}: {}: Compare strings".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_PUSH (push string into argument frame)

    Appends string from stack to argument frame
    '''
    def opPush(self):
        self.argFrame[-1].append(self.getStringValue())
        logging.debug("IP: {}: {}: Push string to argument frame".format(self.ip, self.dumpInstruction()))

    '''
    Routine called for OP_PUSH_FRAME (push new argument frame)

    Appends empty list to list of argument frames
    '''
    def opPushFrame(self):
        self.argFrame.append([])

        logging.debug("IP: {}: {}: Push empty argument frame".format(self.ip, self.dumpInstruction()))

    '''
    Dictionary of calls by opcode
    '''
    callOp = {
0:opFuncDecl,
1:opCreateObject,
2:opAddObject,
3:opEndObject,
4:opJmpiffnot,
5:opJmpifnot,
6:opJmpiff,
7:opJmpif,
8:opJmpifnotNp,
9:opJmpifNp,
10:opJmp,
11:opReturn,
12:opCmpeq,
13:opCmpgr,
14:opCmpge,
15:opCmplt,
16:opCmple,
17:opCmpne,
18:opXor,
19:opMod,
20:opBitand,
21:opBitor,
22:opNot,
23:opNotf,
24:opOnescomplement,
25:opShr,
26:opShl,
27:opAnd,
28:opOr,
29:opAdd,
30:opSub,
31:opMul,
32:opDiv,
33:opNeg,
34:opSetcurvar,
35:opSetcurvarCreate,
36:opSetcurvarArray,
37:opSetcurvarArrayCreate,
38:opLoadvarUint,
39:opLoadvarFlt,
40:opLoadvarStr,
41:opSavevarUint,
42:opSavevarFlt,
43:opSavevarStr,
44:opSetcurobject,
45:opSetcurobjectNew,
46:opSetcurobjectNewInt,
47:opSetcurfield,
48:opSetcurfieldArray,
49:opLoadfieldUint,
50:opLoadfieldFlt,
51:opLoadfieldStr,
52:opSavefieldUint,
53:opSavefieldFlt,
54:opSavefieldStr,
55:opStrToUint,
56:opStrToFlt,
57:opStrToNone,
58:opFltToUint,
59:opFltToStr,
60:opFltToNone,
61:opUintToFlt,
62:opUintToStr,
63:opUintToNone,
64:opLoadimmedUint,
65:opLoadimmedFlt,
66:opTagToStr,
67:opLoadimmedStr,
68:opDocBlockStr,
69:opLoadimmedIdent,
70:opCallfunc,
71:opCallfunc,
72:opAdvanceStr,
73:opAdvanceStrAppendchar,
74:opAdvanceStrComma,
75:opAdvanceStrNul,
76:opRewindStr,
77:opTerminateRewindStr,
78:opCompareStr,
79:opPush,
80:opPushFrame,
    }
    
    '''
    Decodes parsed file
    '''
    def decode(self):
        while self.ip < self.file.byteCode.binLen:
            try:
                # If one or more code block have ended:
                if self.ip in self.endBlock:
                    for end in self.endBlock.pop(self.ip):
                        self.tree.focusParent()
                        if isinstance(end, torque.If) and end.elseHandle is not None:
                            # Append else to tree:
                            self.tree.append(end.elseHandle)
                            self.tree.focusChild()
                        elif isinstance(end, torque.FuncDecl):
                            # Exit function:
                            self.inFunction -= 1

                
                # Get current opcode:
                opCode = self.getCode()
                
                #Dump stacks from previous call
                logging.debug("\nStacks: SS {} IS {} FS {} BS {}".format(self.strStack, self.intStack, self.fltStack, self.binStack))
                #Show some info about curent call that about to happen
                logging.debug('CS:{} IP:{} OP:{} {} af: {} cv:{} cf:{} co:{}'.format(
                    len(self.callStack), self.ip, opCode, OPCODES[opCode], self.argFrame, self.curvar, self.curfield, self.curobj))
                logging.debug("Next 10 codes: {}".format(
                    [ self.file.byteCode.dumpTab[k] for k in self.file.byteCode.dumpTab if self.ip+10 > k >= self.ip ]) )
                
                if len(self.callStack) > 167:  
                    _ = "This is for debugging breakpoint"
                
                # Call its respective routine:
                self.callOp[opCode](self)

                # Record call:
                self.callStack.append(self.callOp[opCode])

                # Update instruction pointer and count:
                self.ip = self.getCurByteIndex()
            except Exception as e:
                if e.__class__ is KeyError and opCode == self.file.byteCode.endCtrlCode:
                    logging.debug("IP: {}: Got (supposed) end control sequence: Terminating".format(self.ip))
                    return
                else:
                    raise e
