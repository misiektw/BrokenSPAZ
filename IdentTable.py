from FileReading import FileReading

'''
Identification Table that maps the strings to the opcode stream, represented as a dictionary where the keys are the offsets
of the strings and the values are lists of indexes of the stream
'''
class IdentTable(dict, FileReading):
    '''
    Constructs an IdentTable object (dictionary of lists of integers)
    @param  size    Size of the table (not of the binary data itself)
    @param  fd      File descriptor
    '''
    def __init__(self, size, fd):
        # Inherit all characteristics of a dictionary:
        dict.__init__(self)

        # Inherit all characteristics of a FileReading object for reading 4-byte long little-endian unsigned words:
        FileReading.__init__(self, fd, 4, "little", False)

        # For each entry of the table:
        for _ in range(0, size):
            offset = self.unpackWord() # Get offset field
            count = self.unpackWord() # Get count field
            self[offset] = []
            # For each location to patch:
            for _ in range(0, count):
                self[offset].append(self.unpackWord())
