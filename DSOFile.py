from FileReading import FileReading
from StringTable import StringTable
from FloatTable import FloatTable
from Code import Code
from IdentTable import IdentTable

'''
Structure of a DSO file and methods for parsing it
'''
class DSOFile(FileReading):
    '''
    Constructs a DSOFile object
    @param  fname   Name of the file to be read
    '''
    def __init__(self, fname):
        with open(fname, "rb") as fd:
            # Inherit all characteristics of a FileReading object for reading 4-byte long little-endian unsigned words:
            FileReading.__init__(self, fd, 4, "little", False)

            # Parse the version of script:
            self.version = self.unpackWord()

            # Parse the Global String Table:
            self.globalStringTableSize = self.unpackWord()
            self.globalStringTable = StringTable(self.read(self.globalStringTableSize))

            # Parse the Global Float Table:
            self.globalFloatTableSize = self.unpackWord()
            self.globalFloatTable = FloatTable(self.read(self.globalFloatTableSize * 4), "float")

            # Parse the Function String Table:
            self.functionStringTableSize = self.unpackWord()
            self.functionStringTable = StringTable(self.read(self.functionStringTableSize))

            # Parse the Function Float Table:
            self.functionFloatTableSize = self.unpackWord()
            self.functionFloatTable = FloatTable(self.read(self.functionFloatTableSize * 4), "float")

            # Parse the Code:
            self.codeSize = self.unpackWord()
            self.code = Code(self.codeSize, fd)

            # Parse the Ident Table:
            self.identTableSize = self.unpackWord()
            self.identTable = IdentTable(self.identTableSize, fd)

    '''
    Patches the code, resolving all references to strings
    '''
    def patch(self):
        self.code.patch(self.identTable)
