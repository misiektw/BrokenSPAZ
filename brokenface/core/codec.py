from sys import stdout
import logging

from core import dso, torque

class StringStack(list):
    def load(self, string):
        if self:
            self[-1] = string
        else:
            self.append(string)

    def advance(self, ch=None):
        if ch is not None:
            if ch == "\n":
                self.append(torque.ConcatNl([self.pop()]))
            elif ch == "\t":
                self.append(torque.ConcatTab([self.pop()]))
            elif ch == " ":
                self.append(torque.ConcatSpc([self.pop()]))
            elif ch == ",":
                self.append(torque.ConcatComma([self.pop()]))
            elif ch == "\x00":
                self.append(torque.StringEqual([self.pop()]))
            else:
                self.append(torque.Concat([self.pop(), "\"" + ch + "\""]))

        # To be overwritten by next load:
        self.append(None)

    def rewind(self):
        s2 = self.pop()
        s1 = self.pop()

        if isinstance(s2, list):
            if isinstance(s1, list):
                self.append(s1 + s2)
            elif torque.isConcatOp(s1):
                s1.operands.append(torque.Concat(s2))
                self.append(s1)
            else:
                s2.insert(0, s1)
                self.append(s2)
        else:
            if isinstance(s1, list):
                s1.append(s2)
                self.append(s1)
            elif torque.isConcatOp(s1):
                s1.operands.append(s2)
                self.append(s1)
            else:
                self.append([s1, s2])

    def terminateRewind(self):
        self.pop()


class Decoding:
    def __init__(self, dsoFile, inFunction=0, offset=0):
        self.file = dsoFile
        self.inFunction = inFunction
        self.offset = offset

        self.curvar = None
        self.curobj = None
        self.curfield = None

        self.argFrame = []

        self.binStack = []
        self.intStack = []
        self.fltStack = []
        self.strStack = StringStack()

        self.treeStack = []

        self.tree = torque.Tree(torque.File(self.file.name))

        self.ip = 0

        self.callStack = []

        self.endBlock = {}

    def updateIP(self):
        self.ip = self.file.byteCode.pointer

    def getCode(self):
        return self.file.byteCode.getCode()

    def lookupCode(self):
        return self.file.byteCode.lookupCode()

    def getUint(self):
        return self.file.byteCode.getUint()

    def getStringOffset(self):
        return self.file.byteCode.getStringOffset()

    def getGlobalStringByOffset(self, offset):
        return self.file.globalStringTable[offset]

    def getGlobalString(self):
        return self.getGlobalStringByOffset(self.getStringOffset())

    def getFunctionStringByOffset(self, offset):
        return self.file.functionStringTable[offset]

    def getFunctionString(self):
        return self.getFunctionStringByOffset(self.getStringOffset())

    def getStringByOffset(self, offset):
        if self.inFunction and self.file.functionStringTable:
            return self.getFunctionStringByOffset(offset)
        else:
            return self.getGlobalStringByOffset(offset)

    def getString(self):
        return self.getStringByOffset(self.getStringOffset())

    def setGlobalString(self, offset, string):
        self.file.globalStringTable[offset] = string

    def setFunctionString(self, offset, string):
        self.file.functionStringTable[offset] = string

    def setString(self, offset, string):
        if self.inFunction and self.file.functionStringTable:
            return self.setFunctionString(offset, string)
        else:
            return self.setGlobalString(offset, string)

    def getFloatOffset(self):
        return self.file.byteCode.getFloatOffset()

    def getGlobalFloatByOffset(self, offset):
        return self.file.globalFloatTable[offset]

    def getGlobalFloat(self):
        return self.getGlobalFloatByOffset(self.getFloatOffset())

    def getFunctionFloatByOffset(self, offset):
        return self.file.functionFloatTable[offset]

    def getFunctionFloat(self):
        return self.getFunctionFloatByOffset(self.getFloatOffset())

    def getFloatByOffset(self, offset):
        if self.inFunction and self.file.functionFloatTable:
            return self.getFunctionFloatByOffset(offset)
        else:
            return self.getGlobalFloatByOffset(offset)

    def getFloat(self):
        return self.getFloatByOffset(self.getFloatOffset())

    def dumpInstruction(self):
        return self.file.byteCode.dump(self.ip, self.file.byteCode.pointer)

    def opFuncDecl(self):
        funcName = self.getGlobalString()

        offset = self.getStringOffset()

        if offset == 0:
            # Just read the place reserved for offset and do nothing:
            namespace = ""
        else:
            namespace = self.getGlobalStringByOffset(offset)

        package = self.getGlobalString()
        hasBody = self.getCode()

        end = self.file.byteCode.idxTable[self.getCode()]

        argc = self.getCode()

        argv = []
        for _ in range(0, argc):
            offset = self.getStringOffset()
            string = self.getGlobalStringByOffset(offset)

            if string[0] != "%":
                string = "%" + string

            self.setGlobalString(offset, string)

            argv.append(string)

        decl = torque.FuncDecl(funcName, namespace, package, hasBody, end, argc, argv)

        if end not in self.endBlock:
            self.endBlock[end] = []

        self.endBlock[end].append(decl)

        self.tree.append(decl)
        self.tree.focusChild()

        logging.debug("IP: {}: {}: Declare function: {}, {}, {}, {}, {}, {}".format(self.ip, self.dumpInstruction(), funcName, namespace, package, hasBody, end, argc))

        self.inFunction += 1

    def opCreateObject(self):
        parent = self.getString()
        isDataBlock = self.getCode()
        end = self.file.byteCode.idxTable[self.getCode()]

        # TODO:
        if isDataBlock:
            raise NotImplementedError

        argv = self.argFrame.pop()

        for string in argv[1:]:
            if isinstance(string, str) and string[0] != "%":
                string = "%" + string

        self.treeStack.append(self.tree)
        self.tree = torque.Tree(torque.ObjDecl(parent, isDataBlock, argv))

        logging.debug("IP: {}: {}: Create object: {}, {}, {}".format(self.ip, self.dumpInstruction(), parent, isDataBlock, end))

    def opAddObject(self):
        placeAtRoot = self.getCode()

        if placeAtRoot:
            self.intStack[-1] = self.tree.root
        else:
            self.intStack.append(self.tree.root)

        logging.debug("IP: {}: {}: Add object".format(self.ip, self.dumpInstruction()))

    def opEndObject(self):
        # Restore old tree:
        self.tree = self.treeStack.pop()

        if self.callStack[-2] is Decoding.opCreateObject and self.callStack[-1] is Decoding.opAddObject:
            self.intStack[-1].carryIndent = 0

        placeAtRoot = self.getCode()

        if not placeAtRoot:
            self.tree.append(self.intStack.pop())

        logging.debug("IP: {}: {}: End object".format(self.ip, self.dumpInstruction()))

    def opJmpiffnot(self):
        target = self.file.byteCode.idxTable[self.getCode()] - self.offset
        condition = self.fltStack.pop()

        if target > self.ip:
            ifStatement = torque.If(condition)

            if target not in self.endBlock:
                self.endBlock[target] = []

            self.endBlock[target].append(ifStatement)

            self.tree.append(ifStatement)
            self.tree.focusChild()
        else:
            if condition != self.tree.curNode.condition:
                raise ValueError("Loop condition mismatch")

            self.tree.replace(torque.While(torque.Not([condition])))

        logging.debug("IP: {}: {}: Jump if float condition not met to: {}".format(self.ip, self.dumpInstruction(), target))

    def opJmpifnot(self):
        target = self.file.byteCode.idxTable[self.getCode()] - self.offset
        condition = self.intStack.pop()

        if target > self.ip:
            ifStatement = torque.If(condition)

            if target not in self.endBlock:
                self.endBlock[target] = []

            self.endBlock[target].append(ifStatement)

            self.tree.append(ifStatement)
            self.tree.focusChild()
        else:
            if condition != self.tree.curNode.condition:
                raise ValueError("Loop condition mismatch")

            self.tree.replace(torque.While(torque.Not([condition])))

        logging.debug("IP: {}: {}: Jump if uint/boolean condition not met to: {}".format(self.ip, self.dumpInstruction(), target))

    def opJmpiff(self):
        target = self.file.byteCode.idxTable[self.getCode()] - self.offset
        condition = self.fltStack.pop()

        if target > self.ip:
            ifStatement = torque.If(condition)

            if target not in self.endBlock:
                self.endBlock[target] = []

            self.endBlock[target].append(ifStatement)

            self.tree.append(ifStatement)
            self.tree.focusChild()
        else:
            if condition != self.tree.curNode.condition:
                raise ValueError("Loop condition mismatch")

            self.tree.replace(torque.While(torque.Not([condition])))

        logging.debug("IP: {}: {}: Jump if float condition not met to: {}".format(self.ip, self.dumpInstruction(), target))

    def opJmpif(self):
        target = self.file.byteCode.idxTable[self.getCode()] - self.offset
        condition = self.intStack.pop()

        if target > self.ip:
            ifStatement = torque.If(condition)

            if target not in self.endBlock:
                self.endBlock[target] = []

            self.endBlock[target].append(ifStatement)

            self.tree.append(ifStatement)
            self.tree.focusChild()
        else:
            if condition != self.tree.curNode.condition:
                raise ValueError("Loop condition mismatch")

            self.tree.replace(torque.While(torque.Not([condition])))

        logging.debug("IP: {}: {}: Jump if uint/boolean condition met to: {}".format(self.ip, self.dumpInstruction(), target))

    def opJmp(self):
        target = self.file.byteCode.idxTable[self.getCode()] - self.offset

        if target > self.file.byteCode.pointer:
            elseStatement = torque.Else()

            if target not in self.endBlock:
                self.endBlock[target] = []

            self.endBlock[target].append(elseStatement)

            self.tree.getFocused().elseHandle = elseStatement
        else:
            raise NotImplementedError("Backward jump not implemented for OP_JMP")

        logging.debug("IP: {}: {}: Jump to: {}".format(self.ip, self.dumpInstruction(), target))

    def opReturn(self):
        if self.strStack:
            ret = self.strStack[-1]
        else:
            ret = None

        self.tree.append(torque.Return(ret))

        logging.debug("IP: {}: {}: Return".format(self.ip, self.dumpInstruction()))

    def opCmpeq(self):
        self.intStack.append(torque.Equal([self.fltStack.pop(), self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Compare if equal".format(self.ip, self.dumpInstruction()))

    def opCmplt(self):
        self.intStack.append(torque.Less([self.fltStack.pop(), self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Compare if less".format(self.ip, self.dumpInstruction()))

    def opCmple(self):
        self.intStack.append(torque.LessOrEqual([self.fltStack.pop(), self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Compare if less or equal".format(self.ip, self.dumpInstruction()))

    def opCmpgr(self):
        self.intStack.append(torque.Greater([self.fltStack.pop(), self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Compare if greater".format(self.ip, self.dumpInstruction()))

    def opCmpge(self):
        self.intStack.append(torque.GreaterOrEqual([self.fltStack.pop(), self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Compare if greater or equal".format(self.ip, self.dumpInstruction()))

    def opCmpne(self):
        self.intStack.append(torque.NotEqual([self.fltStack.pop(), self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Compare if not equal".format(self.ip, self.dumpInstruction()))

    def opXor(self):
        self.intStack.append(torque.Xor([self.intStack.pop(), self.intStack.pop()]))

        logging.debug("IP: {}: {}: Bitwise xor".format(self.ip, self.dumpInstruction()))

    def opMod(self):
        self.intStack.append(torque.Mod([self.intStack.pop(), self.intStack.pop()]))

        logging.debug("IP: {}: {}: Get modulo".format(self.ip, self.dumpInstruction()))

    def opBitand(self):
        self.intStack.append(torque.BitAnd([self.intStack.pop(), self.intStack.pop()]))

        logging.debug("IP: {}: {}: Bitwise and".format(self.ip, self.dumpInstruction()))

    def opBitor(self):
        self.intStack.append(torque.BitOr([self.intStack.pop(), self.intStack.pop()]))

        logging.debug("IP: {}: {}: Bitwise or".format(self.ip, self.dumpInstruction()))

    def opNot(self):
        self.intStack.append(torque.Not([self.intStack.pop()]))

        logging.debug("IP: {}: {}: Negate uint/boolean value".format(self.ip, self.dumpInstruction()))

    def opNotf(self):
        self.intStack.append(torque.Not([self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Negate float value".format(self.ip, self.dumpInstruction()))

    def opOnescomplement(self):
        self.intStack.append(torque.Complement([self.intStack.pop(), self.intStack.pop()]))

        logging.debug("IP: {}: {}: Bitwise complement".format(self.ip, self.dumpInstruction()))

    def opShr(self):
        self.intStack.append(torque.ShiftRight([self.intStack.pop(), self.intStack.pop()]))

        logging.debug("IP: {}: {}: Shift right".format(self.ip, self.dumpInstruction()))

    def opShl(self):
        self.intStack.append(torque.ShiftLeft([self.intStack.pop(), self.intStack.pop()]))

        logging.debug("IP: {}: {}: Shift left".format(self.ip, self.dumpInstruction()))

    def opAnd(self):
        self.intStack.append(torque.And([self.intStack.pop(), self.intStack.pop()]))

        logging.debug("IP: {}: {}: Logical and".format(self.ip, self.dumpInstruction()))

    def opOr(self):
        self.intStack.append(torque.Or([self.intStack.pop(), self.intStack.pop()]))

        logging.debug("IP: {}: {}: Logical or".format(self.ip, self.dumpInstruction()))

    def opAdd(self):
        self.fltStack.append(torque.Add([self.fltStack.pop(), self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Sum floats".format(self.ip, self.dumpInstruction()))

    def opSub(self):
        self.fltStack.append(torque.Sub([self.fltStack.pop(), self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Subtract floats".format(self.ip, self.dumpInstruction()))

    def opMul(self):
        self.fltStack.append(torque.Mul([self.fltStack.pop(), self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Multiply floats".format(self.ip, self.dumpInstruction()))

    def opDiv(self):
        self.fltStack.append(torque.Div([self.fltStack.pop(), self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Divide floats".format(self.ip, self.dumpInstruction()))

    def opNeg(self):
        self.fltStack.append(torque.Neg([self.fltStack.pop()]))

        logging.debug("IP: {}: {}: Invert sign of float".format(self.ip, self.dumpInstruction()))

    def opSetcurvarArray(self):
        self.curvar = torque.ArrayAccess(self.strStack[-1])

        logging.debug("IP: {}: {}: Set current array variable".format(self.ip, self.dumpInstruction()))

    def opSetcurvar(self):
        offset = self.getStringOffset()
        string = self.getGlobalStringByOffset(offset)

        if string[0] != "$" and string[0] != "%":
            if self.inFunction:
                string = "%" + string
            else:
                string = "$" + string

        self.setGlobalString(offset, string)

        self.curvar = string

        logging.debug("IP: {}: {}: Set current variable: {}".format(self.ip, self.dumpInstruction(), self.curvar))

    def opLoadvarUint(self):
        self.intStack.append(self.curvar)

        logging.debug("IP: {}: {}: Load variable of type uint: {}".format(self.ip, self.dumpInstruction(), self.curvar))

    def opLoadvarFlt(self):
        self.fltStack.append(self.curvar)

        logging.debug("IP: {}: {}: Load variable of type float: {}".format(self.ip, self.dumpInstruction(), self.curvar))

    def opLoadvarStr(self):
        self.strStack.load(self.curvar)

        logging.debug("IP: {}: {}: Load variable of type string: {}".format(self.ip, self.dumpInstruction(), self.curvar))

    def opSavevarUint(self):
        name = self.curvar
        value = self.intStack[-1]

        self.curvar = (name, value)

        self.tree.append(torque.Assignment(name, value))

        logging.debug("IP: {}: {}: Save uint value into variable".format(self.ip, self.dumpInstruction()))

    def opSavevarFlt(self):
        name = self.curvar
        value = self.fltStack[-1]

        self.curvar = (name, value)

        self.tree.append(torque.Assignment(name, value))

        logging.debug("IP: {}: {}: Save float value into variable".format(self.ip, self.dumpInstruction()))

    def opSavevarStr(self):
        name = self.curvar
        value = self.strStack[-1]

        if isinstance(value, list):
            value = torque.Concat(value)

        self.curvar = (name, value)

        self.tree.append(torque.Assignment(name, value))

        logging.debug("IP: {}: {}: Save string value into variable".format(self.ip, self.dumpInstruction()))

    def opSetcurobject(self):
        self.curobj = self.strStack[-1]

        logging.debug("IP: {}: {}: Set current object".format(self.ip, self.dumpInstruction()))

    def opSetcurobjectNew(self):
        self.curobj = None

        logging.debug("IP: {}: {}: Set new current object".format(self.ip, self.dumpInstruction()))

    def opSetcurfield(self):
        self.curfield = self.getGlobalString()

        logging.debug("IP: {}: {}: Set current field: {}".format(self.ip, self.dumpInstruction(), self.curfield))

    def opLoadfieldUint(self):
        self.intStack.append(self.curfield)

        logging.debug("IP: {}: {}: Load field of type string: {}".format(self.ip, self.dumpInstruction(), self.curfield))

    def opLoadfieldFlt(self):
        self.fltStack.append(self.curfield)

        logging.debug("IP: {}: {}: Load field of type string: {}".format(self.ip, self.dumpInstruction(), self.curfield))

    def opLoadfieldStr(self):
        self.strStack.load(self.curfield)

        logging.debug("IP: {}: {}: Load field of type string: {}".format(self.ip, self.dumpInstruction(), self.curfield))

    def opSavefieldUint(self):
        if self.curobj is None:
            # Assignment to field during object creation:
            name = self.curfield
        else:
            # Assignment to field of current object:
            name = self.curobj + "." + self.curfield

        value = self.intStack[-1]

        self.curfield = (name, value)

        self.tree.append(torque.Assignment(name, value))

        logging.debug("IP: {}: {}: Save uint value into field".format(self.ip, self.dumpInstruction()))

    def opSavefieldFlt(self):
        if self.curobj is None:
            # Assignment to field during object creation:
            name = self.curfield
        else:
            # Assignment to field of current object:
            name = self.curobj + "." + self.curfield

        value = self.fltStack[-1]

        self.curfield = (name, value)

        self.tree.append(torque.Assignment(name, value))

        logging.debug("IP: {}: {}: Save float value into field".format(self.ip, self.dumpInstruction()))

    def opSavefieldStr(self):
        if self.curobj is None:
            # Assignment to field during object creation:
            name = self.curfield
        else:
            # Assignment to field of current object:
            name = self.curobj + "." + self.curfield

        value = self.strStack[-1]

        self.curfield = (name, value)

        self.tree.append(torque.Assignment(name, value))

        logging.debug("IP: {}: {}: Save string value into field".format(self.ip, self.dumpInstruction()))

    def opStrToUint(self):
        self.intStack.append(self.strStack.pop())

        logging.debug("IP: {}: {}: Pop string into uint stack".format(self.ip, self.dumpInstruction()))

    def opStrToFlt(self):
        self.fltStack.append(self.strStack.pop())

        logging.debug("IP: {}: {}: Pop string into float stack".format(self.ip, self.dumpInstruction()))

    def opStrToNone(self):
        popd = self.strStack.pop()

        # Return value being discarded means procedure call:
        if isinstance(popd, torque.FuncCall) and self.callStack[-1] is Decoding.opCallfunc:
            self.tree.append(popd)

        logging.debug("IP: {}: {}: Pop string out".format(self.ip, self.dumpInstruction()))

    def opFltToUint(self):
        self.intStack.append(self.fltStack.pop())

        logging.debug("IP: {}: {}: Pop float into uint stack".format(self.ip, self.dumpInstruction()))

    def opFltToStr(self):
        self.strStack.load(self.fltStack.pop())

        logging.debug("IP: {}: {}: Pop float into string stack".format(self.ip, self.dumpInstruction()))

    def opFltToNone(self):
        self.fltStack.pop()

        logging.debug("IP: {}: {}: Pop float out".format(self.ip, self.dumpInstruction()))

    def opUintToFlt(self):
        self.fltStack.append(self.intStack.pop())

        logging.debug("IP: {}: {}: Pop uint into float stack".format(self.ip, self.dumpInstruction()))

    def opUintToStr(self):
        self.strStack.load(self.intStack.pop())

        logging.debug("IP: {}: {}: Pop uint into string stack".format(self.ip, self.dumpInstruction()))

    def opUintToNone(self):
        popd = self.intStack.pop()

        # Return value being discarded means object declared, but not assigned:
        if isinstance(popd, torque.ObjDecl) and self.callStack[-1] is Decoding.opEndObject:
            self.tree.append(popd)

        logging.debug("IP: {}: {}: Pop uint out".format(self.ip, self.dumpInstruction()))

    def opLoadimmedUint(self):
        self.intStack.append(self.getUint())

        logging.debug("IP: {}: {}: Load uint: {}".format(self.ip, self.dumpInstruction(), self.intStack[-1]))

    def opLoadimmedFlt(self):
        self.fltStack.append(self.getFloat())

        logging.debug("IP: {}: {}: Load float: {}".format(self.ip, self.dumpInstruction(), self.fltStack[-1]))

    def opLoadimmedStr(self):
        self.strStack.load("\"" + self.getGlobalString() + "\"")

        logging.debug("IP: {}: {}: Load string: {}".format(self.ip, self.dumpInstruction(), self.strStack[-1]))

    def opLoadimmedIdent(self):
        self.strStack.load("\"" + self.getString().encode("unicode_escape").decode() + "\"")

        logging.debug("IP: {}: {}: Load string (ident): {}".format(self.ip, self.dumpInstruction(), self.strStack[-1]))

    def opTagToStr(self):
        self.strStack.load(self.getGlobalString())

        logging.debug("IP: {}: {}: Load tagged string: {}".format(self.ip, self.dumpInstruction(), self.strStack[-1]))

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

    def opAdvanceStr(self):
        self.strStack.advance()

        logging.debug("IP: {}: {}: Advance string on stack".format(self.ip, self.dumpInstruction()))

    def opAdvanceStrAppendchar(self):
        self.strStack.advance(chr(self.getCode()))

        logging.debug("IP: {}: {}: Advance string on stack and append char".format(self.ip, self.dumpInstruction()))

    def opAdvanceStrComma(self):
        self.strStack.advance(",")

        logging.debug("IP: {}: {}: Advance string on stack and append comma".format(self.ip, self.dumpInstruction()))

    def opAdvanceStrNul(self):
        self.strStack.advance("\x00")

        logging.debug("IP: {}: {}: Advance string on stack (null)".format(self.ip, self.dumpInstruction()))

    def opRewindStr(self):
        self.strStack.rewind()

        logging.debug("IP: {}: {}: Rewind string stack".format(self.ip, self.dumpInstruction()))

    def opTerminateRewindStr(self):
        self.strStack.terminateRewind()

        logging.debug("IP: {}: {}: Terminate and rewind string stack".format(self.ip, self.dumpInstruction()))

    def opCompareStr(self):
        s2 = self.strStack.pop()
        op = self.strStack.pop()

        op.operands.append(s2)

        self.intStack.append(op)

        logging.debug("IP: {}: {}: Compare strings".format(self.ip, self.dumpInstruction()))

    def opPush(self):
        self.argFrame[-1].append(self.strStack[-1])

        logging.debug("IP: {}: {}: Push string to argument frame".format(self.ip, self.dumpInstruction()))

    def opPushFrame(self):
        self.argFrame.append([])

        logging.debug("IP: {}: {}: Push empty argument frame".format(self.ip, self.dumpInstruction()))

    callOp = {
        0:      opFuncDecl,
        1:      opCreateObject,

        4:      opAddObject,
        5:      opEndObject,
        6:      opJmpiffnot,
        7:      opJmpifnot,
        8:      opJmpiff,
        9:      opJmpif,
        10:     opJmpifnot,
        11:     opJmpif,
        12:     opJmp,
        13:     opReturn,
        14:     opCmpeq,
        15:     opCmplt,
        16:     opCmple,
        17:     opCmpgr,
        18:     opCmpge,
        19:     opCmpne,
        20:     opXor,
        21:     opMod,
        22:     opBitand,
        23:     opBitor,
        24:     opNot,
        25:     opNotf,
        26:     opOnescomplement,
        27:     opShr,
        28:     opShl,
        29:     opAnd,
        30:     opOr,
        31:     opAdd,
        32:     opSub,
        33:     opMul,
        34:     opDiv,
        35:     opNeg,
        36:     opSetcurvar,
        37:     opSetcurvar,
        38:     opSetcurvar,
        39:     opSetcurvar,
        40:     opSetcurvarArray,
        41:     opSetcurvarArray,
        42:     opSetcurvarArray,
        43:     opSetcurvarArray,
        44:     opLoadvarUint,
        45:     opLoadvarFlt,
        46:     opLoadvarStr,
        47:     opSavevarUint,
        48:     opSavevarFlt,
        49:     opSavevarStr,
        50:     opSetcurobject,
        51:     opSetcurobjectNew,
        52:     opSetcurfield,

        54:     opLoadfieldUint,
        55:     opLoadfieldFlt,
        56:     opLoadfieldStr,
        57:     opSavefieldUint,
        58:     opSavefieldFlt,
        59:     opSavefieldStr,
        60:     opStrToUint,
        61:     opStrToFlt,
        62:     opStrToNone,
        63:     opFltToUint,
        64:     opFltToStr,
        65:     opFltToNone,
        66:     opUintToFlt,
        67:     opUintToStr,
        68:     opUintToNone,
        69:     opLoadimmedUint,
        70:     opLoadimmedFlt,
        71:     opLoadimmedStr,
        72:     opLoadimmedIdent,
        73:     opTagToStr,
        74:     opCallfunc,
        75:     opCallfunc,

        77:     opAdvanceStr,
        78:     opAdvanceStrAppendchar,
        79:     opAdvanceStrComma,
        80:     opAdvanceStrNul,
        81:     opRewindStr,
        82:     opTerminateRewindStr,
        83:     opCompareStr,
        84:     opPush,
        85:     opPushFrame
    }

    def decode(self):
        while self.ip < self.file.byteCode.binLen:
            try:
                if self.ip in self.endBlock:
                    for end in self.endBlock.pop(self.ip):
                        self.tree.focusParent()
                        if isinstance(end, torque.If) and end.elseHandle is not None:
                            self.tree.append(end.elseHandle)
                            self.tree.focusChild()
                        elif isinstance(end, torque.FuncDecl):
                            self.inFunction -= 1
                opCode = self.getCode()
                self.callOp[opCode](self)
                self.callStack.append(self.callOp[opCode])
                self.updateIP()
            except Exception as e:
                if e.__class__ is KeyError and opCode == 0xcdcd:
                    logging.debug("IP: {}: Got (supposed) end control sequence: Terminating".format(self.ip))
                    return
                else:
                    raise e
