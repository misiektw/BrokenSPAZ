from sys import stdout
import logging

from core import dso, torque

class Decoding:
    def __init__(self, dsoFile, inFunction=False, offset=0, sink=stdout):
        self.file = dsoFile
        self.inFunction = inFunction
        self.offset = offset
        self.sink = sink

        if inFunction:
            self.currentStringTable = self.file.functionStringTable
            self.currentFloatTable = self.file.functionFloatTable
        else:
            self.currentStringTable = self.file.globalStringTable
            self.currentFloatTable = self.file.globalFloatTable

        self.curvar = None
        self.curobj = None
        self.curfield = None

        self.argFrame = []

        self.binStack = []
        self.intStack = []
        self.strStack = []

        self.tree = torque.Tree(torque.File(self.file.name))

        self.ip = 0

        logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(lineno)d: %(message)s")

        logging.info("globalStringTable id: {}".format(hex(id(self.file.globalStringTable))))
        logging.info("functionStringTable id: {}".format(hex(id(self.file.functionStringTable))))

    def updateIP(self):
        self.ip = self.file.byteCode.idxPtr

    def getCode(self):
        try:
            return self.file.byteCode.getCode()
        except IndexError as e:
            logging.error("IP: {}: {}: Unable to access code: {}".format(self.ip, repr(e), self.file.byteCode.getIndex()))
            quit()

    def lookupCode(self):
        try:
            return self.file.byteCode.lookupCode()
        except IndexError as e:
            logging.error("IP: {}: {}: Unable to access code: {}".format(self.ip, repr(e), self.file.byteCode.getIndex()))
            quit()

    def insertCode(self, idx, code):
        try:
            self.file.byteCode.insertCode(idx, code)
        except IndexError as e:
            logging.error("IP: {}: {}: Unable to access code: {}".format(self.ip, repr(e), idx))
            quit()

    def getStringOffset(self):
        try:
            return self.file.byteCode.getStringOffset()
        except IndexError as e:
            logging.error("IP: {}: {}: Unable to access string offset: {}".format(self.ip, repr(e), self.file.byteCode.getIndex()))
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
            return self.file.globalStringTable[offset]
        except KeyError as e:
            logging.error("IP: {}: {}: Unable to access table {} at given offset: {}".format(self.ip, repr(e), hex(id(self.currentStringTable)), hex(offset)))

    def dumpInstruction(self):
        return self.file.byteCode.dump(self.ip, self.file.byteCode.getIndex())

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

        self.tree.append(torque.FuncDecl(funcName, namespace, package, hasBody, end, argc, argv))
        self.tree.focusChild()

        logging.debug("IP: {}: {}: Function declaration: {}, {}, {}, {}, {}, {}, {}".format(self.ip, self.dumpInstruction(), funcName, namespace, package, hasBody, end, argc, argv))

        # Is this right?
        #self.inFunction = True
        #self.currentStringTable = self.file.functionStringTable
        #self.currentFloatTable = self.file.functionFloatTable

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

        self.tree.append(torque.ObjDecl(parent, isDataBlock, isInternal, isMessage, failJump, argv))
        self.tree.focusChild()

        logging.debug("IP: {}: {}: Object creation: {}, {}, {}, {}, {}, {}".format(self.ip, self.dumpInstruction(), parent, isDataBlock, isInternal, isMessage, failJump, argv))

    def opEndObject(self):
        self.tree.getFocused().id = self.getCode() # TODO: Find out what this is about
        self.intStack[-1] = self.tree.getFocused().id

        self.tree.focusParent()

        logging.debug("IP: {}: {}: Ended object".format(self.ip, self.dumpInstruction()))

    def opReturn(self):
        ret = self.getCode()

        self.tree.append(torque.Return(ret))

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

        self.tree.append(torque.Variable(self.curvar[0], self.curvar[1]))

        logging.debug("IP: {}: {}: Saved variable: {}".format(self.ip, self.dumpInstruction(), self.curvar))

    def opSavevarStr(self):
        self.curvar = (self.curvar, self.strStack[-1])

        self.tree.append(torque.Variable(self.curvar[0], self.curvar[1]))

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

        self.tree.append(torque.FuncCall(funcName, namespace, callType, argv))

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
            while self.ip < self.file.byteCode.codLen:
                opCode = self.getCode()
                self.callOp[opCode](self)
                self.updateIP()
        except KeyError as e:
            logging.error("IP: {}: {}: Unable to access current operation: {}".format(self.ip, repr(e), opCode))
            return
