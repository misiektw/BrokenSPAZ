import sys
import logging

from DSOFile import DSOFile

from TorqueFile import TorqueFile
from TorqueFunctionCall import TorqueFunctionCall
from TorqueFunctionDeclaration import TorqueFunctionDeclaration
from TorqueObject import TorqueObject
from TorqueReturn import TorqueReturn
from TorqueVariable import TorqueVariable

class TorqueDecoding:

    metadata = {
        "META_ELSE":            100,
        "META_END_IF":          101,
        "META_END_WHILE_FLT":   102,
        "META_END_WHILE":       103,
        "META_END_FUNC":        104,
        "META_END_BINARY_OP":   105,
        "META_SKIP":            106,
        "META_END_WHILE_B":     107
    }

    def __init__(self, dso, inFunction=False, offset=0, sink=sys.stdout):
        self.dso = dso
        self.inFunction = inFunction
        self.offset = offset
        self.sink = sink

        if inFunction:
            self.currentStringTable = self.dso.functionStringTable
            self.currentFloatTable = self.dso.functionFloatTable
        else:
            self.currentStringTable = self.dso.globalStringTable
            self.currentFloatTable = self.dso.globalFloatTable

        self.curvar = None
        self.curobj = None
        self.curfield = None

        self.argFrame = []

        self.binStack = []
        self.intStack = []
        self.strStack = []

        self.tree = TorqueFile(self.dso.name)
        self.currentNode = self.tree

        self.ip = 0

        logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(lineno)d: %(message)s")

        logging.info("globalStringTable id: {}".format(hex(id(self.dso.globalStringTable))))
        logging.info("functionStringTable id: {}".format(hex(id(self.dso.functionStringTable))))

    def updateIP(self):
        self.ip = self.dso.byteCode.idxPtr

    def getCode(self):
        try:
            return self.dso.byteCode.getCode()
        except IndexError as e:
            logging.error("IP: {}: {}: Unable to access code: {}".format(self.ip, repr(e), self.dso.byteCode.getIndex()))
            quit()

    def lookupCode(self):
        try:
            return self.dso.byteCode.lookupCode()
        except IndexError as e:
            logging.error("IP: {}: {}: Unable to access code: {}".format(self.ip, repr(e), self.dso.byteCode.getIndex()))
            quit()

    def insertCode(self, idx, code):
        try:
            self.dso.byteCode.insertCode(idx, code)
        except IndexError as e:
            logging.error("IP: {}: {}: Unable to access code: {}".format(self.ip, repr(e), idx))
            quit()

    def getStringOffset(self):
        try:
            return self.dso.byteCode.getStringOffset()
        except IndexError as e:
            logging.error("IP: {}: {}: Unable to access string offset: {}".format(self.ip, repr(e), self.dso.byteCode.getIndex()))
            quit()

    def getString(self):
        offset = self.getStringOffset()
        try:
            return self.currentStringTable[offset]
        except KeyError as e:
            logging.error("IP: {}: {}: Unable to access table {} at given offset: {}".format(self.ip, repr(e), hex(id(self.currentStringTable)), hex(offset)))
            quit()

    def getStringByOffset(self, offset):
        try:
            return self.currentStringTable[offset]
        except KeyError as e:
            logging.error("IP: {}: {}: Unable to access table {} at given offset: {}".format(self.ip, repr(e), hex(id(self.currentStringTable)), hex(offset)))
            quit()

    def getGlobalString(self):
        offset = self.getStringOffset()
        try:
            return self.dso.globalStringTable[offset]
        except KeyError as e:
            logging.error("IP: {}: {}: Unable to access table {} at given offset: {}".format(self.ip, repr(e), hex(id(self.currentStringTable)), hex(offset)))

    def dumpInstruction(self):
        return self.dso.byteCode.dump(self.ip, self.dso.byteCode.getIndex())

    def opFuncDecl(self):
        funcName = self.getString()

        offset = self.getStringOffset()

        if offset == 0:
            # Just read the place reserved for offset and do nothing:
            namespace = ""
        else:
            namespace = self.getStringByOffset(offset)

        package = self.getString()
        hasBody = self.getCode()
        end = self.getCode()

        argc = self.getCode()

        argv = []
        for _ in range(0, argc):
            argv.append(self.getString())

        self.currentNode.append(TorqueFunctionDeclaration(funcName, namespace, package, hasBody, end, argc, argv))
        self.currentNode = self.currentNode.children[-1]

        logging.debug("IP: {}: {}: Function declaration: {}, {}, {}, {}, {}, {}, {}".format(self.ip, self.dumpInstruction(), funcName, namespace, package, hasBody, end, argc, argv))

        # Is this right?
        #self.inFunction = True
        #self.currentStringTable = self.dso.functionStringTable
        #self.currentFloatTable = self.dso.functionFloatTable

    def opCreateObject(self):
        # A 0 has been pushed to the int stack because it will contain a handle to the object
        assert self.intStack[-1] == 0

        # Replace that 0 with the code of the object creation:
        parent = self.getString()

        isDataBlock = self.getCode()
        isInternal = self.getCode()
        isMessage = self.getCode()
        failJump = self.getCode()

        argv = self.argFrame.pop()

        self.currentNode.append(TorqueObject(parent, isDataBlock, isInternal, isMessage, failJump, argv))
        self.currentNode = self.currentNode.children[-1]

        logging.debug("IP: {}: {}: Object creation: {}, {}, {}, {}, {}, {}".format(self.ip, self.dumpInstruction(), parent, isDataBlock, isInternal, isMessage, failJump, argv))

    def opEndObject(self):
        self.currentNode.id = self.getCode() # TODO: Find out what this is about
        self.intStack[-1] = self.currentNode.id

        self.currentNode = self.currentNode.parent

        logging.debug("IP: {}: {}: Ended object".format(self.ip, self.dumpInstruction()))

    def opReturn(self):
        ret = self.getCode()

        self.currentNode.append(TorqueReturn(ret))

        logging.debug("IP: {}: {}: Returned: {}".format(self.ip, self.dumpInstruction(), ret))

    def opSetcurvarArray(self):
        self.curvar = self.strStack[-1]

        logging.debug("IP: {}: {}: Created variable: {}".format(self.ip, self.dumpInstruction(), self.curvar))

    def opSetcurvar(self):
        self.curvar = self.getGlobalString()

        logging.debug("IP: {}: {}: Created variable: {}".format(self.ip, self.dumpInstruction(), self.curvar))

    def opLoadvarStr(self):
        self.strStack.append(self.curvar)

        logging.debug("IP: {}: {}: Loaded variable string: {}".format(self.ip, self.dumpInstruction(), self.curvar))

    def opSavevarUint(self):
        self.curvar = (self.curvar, self.intStack[-1])

        self.currentNode.append(TorqueVariable(self.curvar[0], self.curvar[1]))

        logging.debug("IP: {}: {}: Saved variable: {}".format(self.ip, self.dumpInstruction(), self.curvar))

    def opSavevarStr(self):
        self.curvar = (self.curvar, self.strStack[-1])

        self.currentNode.append(TorqueVariable(self.curvar[0], self.curvar[1]))

        logging.debug("IP: {}: {}: Saved variable: {}".format(self.ip, self.dumpInstruction(), self.curvar))

    def opSetcurobject(self):
        self.curobj = self.strStack[-1]

        logging.debug("IP: {}: {}: Created object: {}".format(self.ip, self.dumpInstruction(), self.curobj))

    def opSetcurfield(self):
        self.curfield = self.getString()

        logging.debug("IP: {}: {}: Set field: {}".format(self.ip, self.dumpInstruction(), self.curfield))

    def opStrToNone(self):
        self.strStack.pop()

        logging.debug("IP: {}: {}: Popped string out".format(self.ip, self.dumpInstruction()))

    def opUintToNone(self):
        self.intStack.pop()

        logging.debug("IP: {}: {}: Popped integer out".format(self.ip, self.dumpInstruction()))

    # ????
    def opLoadimmedUint(self):
        self.intStack.append(self.getCode() + self.getCode()) # TODO: Is that it?

        logging.debug("IP: {}: {}: Loaded immediate of type unsigned integer: {}".format(self.ip, self.dumpInstruction(), self.intStack[-1]))

    def opLoadimmedIdent(self):
        self.strStack.append(self.getString())

        logging.debug("IP: {}: {}: Loaded immediate of type string: {}".format(self.ip, self.dumpInstruction(), self.strStack[-1]))

    def opTagToStr(self):
        self.strStack.append(self.getString())

        logging.debug("IP: {}: {}: Pushed tagged string: {}".format(self.ip, self.dumpInstruction(), self.strStack[-1]))

    def opCallfunc(self):
        funcName = self.getString()

        offset = self.getStringOffset()

        if offset == 0:
            # Just read the place reserved for offset and do nothing:
            namespace = ""
        else:
            namespace = self.getStringByOffset(offset)

        callType = self.getCode()

        argv = self.argFrame[-1]

        self.currentNode.append(TorqueFunctionCall(funcName, namespace, callType, argv))

        logging.debug("IP: {}: {}: Function call: {}, {}, {}, {}".format(self.ip, self.dumpInstruction(), funcName, namespace, callType, argv))

    def opAdvanceStr(self):

        logging.debug("IP: {}: {}: Advanced string (????)".format(self.ip, self.dumpInstruction()))

    def opPush(self):
        self.argFrame[-1].append(self.strStack[-1])

        logging.debug("IP: {}: {}: Pushed string into argument frame: {}".format(self.ip, self.dumpInstruction(), self.argFrame[-1][-1]))

    def opPushFrame(self):
        self.argFrame.append([])

        logging.debug("IP: {}: {}: Pushed argument frame".format(self.ip, self.dumpInstruction()))

    callOp = {
        0:      opFuncDecl,
        1:      opCreateObject,

        5:      opEndObject,

        13:     opReturn,

        36:     opSetcurvar,
        37:     opSetcurvar,

        39:     opSetcurvar,

        46:     opLoadvarStr,
        47:     opSavevarUint,

        49:     opSavevarStr,
        50:     opSetcurobject,

        52:     opSetcurfield,

        62:     opStrToNone,

        68:     opUintToNone,
        69:     opLoadimmedUint,

        72:     opLoadimmedIdent,
        73:     opTagToStr,
        74:     opCallfunc,
        75:     opCallfunc,

        77:     opAdvanceStr,

        84:     opPush,
        85:     opPushFrame
    }

    def decode(self):
        try:
            while self.ip < self.dso.byteCode.length:
                opCode = self.getCode()
                self.callOp[opCode](self)
                self.updateIP()
        except KeyError as e:
            logging.error("IP: {}: {}: Unable to access current operation: {}".format(self.ip, repr(e), opCode))
            return
