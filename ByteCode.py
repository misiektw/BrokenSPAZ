from BinaryReading import BinaryReading

'''
Reference stream that constitutes the script, represented as a BinaryReader
'''
class ByteCode(BinaryReading):
    '''
    Constructs a ByteCode object (list of integers)
    @param  binReader    Binary reader to parse the bytecode from
    @param  ctrlCode     Special code that indicates that the following data is part of the code
    '''
    def __init__(self, binReader, ctrlCode=0xff):
        # Inherit all characteristics of BinaryReading:
        BinaryReading.__init__(self, b'', "little")

        self.ctrlCode = ctrlCode
        self.ctrlByte = bytes([ctrlCode])

        # A list of indexes of the codes into the stream, so that the bytecode can be accessed by code and not only by byte:
        self.idxTable = []
        self.idxPtr = 0

        tableLen = binReader.unpackUint32()
        startPtr = binReader.pointer

        for _ in range(0, tableLen):
            # Get byte:
            bt = binReader.read8()

            if bt == self.ctrlByte:
                # Get next 2 bytes as part of same code:
                bt += binReader.read16()

            # Append packed code to stream:
            self.append(bt)

            # Store the index of the code in the stream:
            self.idxTable.append(binReader.pointer - startPtr - 1)

        self.length = len(self.idxTable) # Number of codes
        self.size = len(self.byteStream) # Number of bytes

    '''
    Retrieves the code currently pointed at
    '''
    def getCode(self):
        # Get byte:
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
            self.insert(idx, self.ctrlByte)
            self.packInsertUint16(self.idxTable[idx], code)
            inserted = 3

        # Insert index of the newly inserted code in the index table
        self.idxTable.insert(idx, self.idxTable[idx])

        # Update the following indexes:
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
