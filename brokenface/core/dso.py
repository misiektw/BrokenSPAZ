from sys import stdout
from os.path import basename, getsize
from util import binary

'''
Table of strings, represented as a dictionary where the keys are the offsets (addresses) of the strings in the file and the
values are the strings themselves
'''
class StringTable(dict):
    '''
    Constructs a StringTable object (dictionary of strings)
    @param  binReader    Binary reader to parse the table from
    '''
    def __init__(self, binReader):
        # Inherit all characteristics of a dictionary:
        super().__init__(self)

        self.binLen = binReader.unpackUint32()

        # Split all strings, compute their offsets and add the entries to the dictionary:
        offset = 0
        while offset < self.binLen:
            self[offset] = binReader.readString()
            offset += len(self[offset]) + 1

    '''
    Gets a string or substring of the table
    @param  key     Key of entry to be retrieved
    '''
    def __getitem__(self, key):
        # If out of bounds:
        if key < 0 or key >= self.binLen:
            raise KeyError

        try:
            # Try default dict operator:
            return super().__getitem__(key)
        except KeyError:
            # If null byte:
            if key + 1 in self:
                raise KeyError

            # Decrease until a valid key is found:
            k = key
            while k >= 0 and k not in self:
                k -= 1

            if k < 0:
                raise KeyError
            else:
                # Return substring:
                return self[k][key-k:]


'''
Table of floating point numbers, represented as a list of floats
'''
class FloatTable(list):
    '''
    Constructs a FloatTable object (list of floats)
    @param  binReader    Binary reader to parse the table from
    '''
    def __init__(self, binReader):
        # Inherit all characteristics of a list:
        super().__init__(self)

        self.binLen = binReader.unpackUint32()

        for _ in range(0, self.binLen):
            self.append(binReader.unpackFloat32())


'''
Reference stream that constitutes the script, represented as a BinaryReader
'''
class ByteCode(binary.Reading):
    '''
    Constructs a ByteCode object (list of integers)
    @param  binReader    Binary reader to parse the bytecode from
    @param  ctrlCode     Special code that indicates that the following data is part of the code
    '''
    def __init__(self, binReader, ctrlCode=0xff):
        # Inherit all characteristics of binary.Reading:
        super().__init__(b'', "little")

        self.ctrlCode = ctrlCode
        self.ctrlByte = bytes([ctrlCode])

        # A list of indexes of the codes into the stream, so that the bytecode can be accessed by code and not only by byte:
        self.idxTable = []
        self.idxPtr = 0

        self.codLen = binReader.unpackUint32() # Number of codes

        startPtr = binReader.pointer

        for _ in range(0, self.codLen):
            # Get byte:
            bt = binReader.read8()

            if bt == self.ctrlByte:
                # Get next 2 bytes as part of same code:
                bt += binReader.read16()

            # Append packed code to stream:
            self.append(bt)

            # Store the index of the code in the stream:
            self.idxTable.append(binReader.pointer - startPtr - 1)

        self.binLen = len(self.byteStream) # Number of bytes

    '''
    Retrieves the code currently pointed at
    '''
    def getCode(self):
        # Get code:
        code = self.unpackUint8()

        if code == self.ctrlCode:
            # Get the actual 2-bytes long code:
            code = self.unpackUint16()

        self.idxPtr += 1
        
        return code

    '''
    Same as getCode, but without moving the pointer
    '''
    def lookupCode(self):
        return self.lookupUnpackUint8()

    '''
    Insert a code value into the bytecode
    @param  idx     Index of the bytecode to be inserted
    @param  code    1- or 2-bytes long unsigned integer to be inserted
    '''
    def insertCode(self, idx, code):
        if code < 255:
            self.packInsertUint8(self.idxTable[idx], code)
            inserted = 1
        else:
            self.insert(self.idxTable[idx], self.ctrlByte)
            self.packInsertUint16(self.idxTable[idx] + 1, code)
            inserted = 3

        # Insert index of the newly inserted code in the index table
        self.idxTable.insert(idx, self.idxTable[idx])

        # Update the following indices:
        for index in self.idxTable[idx+1:]:
            index += inserted

    '''
    Retrieves the string offset currently pointed at
    '''
    def getStringOffset(self):
        # String offsets are 2-bytes long, taking two codes:
        offset = self.unpackUint16()

        self.idxPtr += 2

        return offset

    '''
    Retrieves the index of the current code
    '''
    def getIndex(self):
        return self.idxPtr

    '''
    Dump chunk of bytecode
    @param  start   Start code index of chunk
    @param  end     End code index of chunk
    '''
    def dump(self, start, end):
        try:
            return self.byteStream[self.idxTable[start]:self.idxTable[end]]
        except IndexError:
            return self.byteStream[self.idxTable[start]:]

    '''
    Patches the string offsets into the blank locations of the stream as described in the Identification Table
    @param  identTable  Identification Table described in the file
    '''
    def patchStrings(self, identTable):
        for offset, locations in identTable.items():
            for loc in locations:
                self.replace(self.idxTable[loc], offset)


'''
Identification Table that maps the strings to the opcode stream, represented as a dictionary where the keys are the offsets
of the strings and the values are lists of indexes of the stream
'''
class IdentTable(dict):
    '''
    Constructs an IdentTable object (dictionary of lists of integers)
    @param  binReader   Binary reader to parse the table from
    '''
    def __init__(self, binReader):
        # Inherit all characteristics of a dictionary:
        super().__init__(self)

        tableLen = binReader.unpackUint32()

        # For each entry of the table:
        for _ in range(0, tableLen):
            offset = binReader.read32()[:2] # Get offset field (offset is just 2-bytes long)
            count = binReader.unpackUint32() # Get count field
            self[offset] = []
            # For each location to patch:
            for _ in range(0, count):
                self[offset].append(binReader.unpackUint32())


'''
Raise this exception when something went wrong during parsing
'''
class ParsingError(Exception):
    '''
    Constructs a new ParsingError object
    @param  msg     Specific message to be appended on the beginning of error message
    @param  name    Name of the file being parsed that raised the exception
    '''
    def __init__(self, msg, name):
        self.message = msg + ". File \"" + name + "\" might be corrupted or encoded in a different standard"


'''
Raise this exception when a method that depends on the parsed file is called before parsing
'''
class NotParsedError(Exception):
    '''
    Constructs a new NotParsedError object
    @param  method  Method where the exception was raised
    '''
    def __init__(self, method):
        self.message = "File should be parsed before calling method \"" + method + "\""


'''
Structure of a DSO file and methods for parsing it
'''
class File():
    '''
    Constructs a File object
    @param  path    Path of file to be parsed
    '''
    def __init__(self, path):
        # Save file path:
        self.path = path

        # Save file name:
        self.name = basename(path)

        # Dump contents to a binary reader:
        with open(path, "rb") as fd:
            self.binReader = binary.Reading(fd.read(), "little")

        # Not parsed yet:
        self.parsed = False

    '''
    Parses the file into tables and bytecode
    '''
    def parse(self):
        # Parse the version of script:
        self.version = self.binReader.unpackUint32()

        # Parse the Global String Table:
        self.globalStringTable = StringTable(self.binReader)

        # Parse the Global Float Table:
        self.globalFloatTable = FloatTable(self.binReader)

        # Parse the Function String Table:
        self.functionStringTable = StringTable(self.binReader)

        # Parse the Function Float Table:
        self.functionFloatTable = FloatTable(self.binReader)

        # Parse the Code:
        self.byteCode = ByteCode(self.binReader)

        # Parse the Ident Table:
        self.identTable = IdentTable(self.binReader)

        if getsize(self.path) != self.binReader.pointer:
            raise ParsingError("Parsing did not reach EOF", self.name)

        # Patch bytecode, resolving all references to strings:
        self.byteCode.patchStrings(self.identTable)

        self.parsed = True

    '''
    Dumps the structures of the parsed file
    @param  sink    Output to dump contents to
    '''
    def dump(self, sink=stdout):
        if not self.parsed:
            raise NotParsedError("dump")

        print("Script version: {}".format(self.version), file=sink)
        print("", file=sink)

        print("Global String Table:", file=sink)
        print(self.globalStringTable, file=sink)
        print("", file=sink)

        print("Global Float Table:", file=sink)
        print(self.globalFloatTable, file=sink)
        print("", file=sink)

        print("Function String Table:", file=sink)
        print(self.functionStringTable, file=sink)
        print("", file=sink)

        print("Function float Table:", file=sink)
        print(self.functionFloatTable, file=sink)
        print("", file=sink)

        print("Byte Code:", file=sink)
        print(self.byteCode.byteStream, file=sink)
        print("", file=sink)

        print("Byte Code indexes:", file=sink)
        print(self.byteCode.idxTable, file=sink)
        print("", file=sink)

        print("Ident Table:", file=sink)
        print(self.identTable, file=sink)
        print("", file=sink)
