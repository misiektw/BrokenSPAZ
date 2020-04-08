from StringTable import StringTable
from FloatTable import FloatTable
from ByteCode import ByteCode
from IdentTable import IdentTable

'''
Structure of a DSO file and methods for parsing it
'''
class DSOFile():
    '''
    Constructs a DSOFile object
    @param  binReader    Binary reader to parse the table from
    '''
    def __init__(self, binReader):
        # Parse the version of script:
        self.version = binReader.unpackUint32()

        print("Script version: {}".format(self.version))
        print("")

        # Parse the Global String Table:
        self.globalStringTable = StringTable(binReader)

        print("Global String Table:")
        print(self.globalStringTable)
        print("")

        # Parse the Global Float Table:
        self.globalFloatTable = FloatTable(binReader)

        print("Global Float Table:")
        print(self.globalFloatTable)
        print("")

        # Parse the Function String Table:
        self.functionStringTable = StringTable(binReader)

        print("Function String Table:")
        print(self.functionStringTable)
        print("")

        # Parse the Function Float Table:
        self.functionFloatTable = FloatTable(binReader)

        print("Function float Table:")
        print(self.functionFloatTable)
        print("")

        # Parse the Code:
        self.byteCode = ByteCode(binReader)

        print("Byte Code:")
        print(self.byteCode.byteStream)
        print("")

        print("Byte Code indexes:")
        print(self.byteCode.idxTable)
        print("")

        # Parse the Ident Table:
        self.identTable = IdentTable(binReader)

        print("Ident Table:")
        print(self.identTable)
        print("")

    '''
    Patches the code, resolving all references to strings
    '''
    def patchStrings(self):
        self.byteCode.patchStrings(self.identTable)

        print("Patched Byte Code:")
        print(self.byteCode.byteStream)
        print("")