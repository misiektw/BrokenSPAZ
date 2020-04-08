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
        dict.__init__(self)

        tableLen = binReader.unpackUint32()

        # For each entry of the table:
        for _ in range(0, tableLen):
            offset = binReader.read32()[:2] # Get offset field (offset is just 2-bytes long)
            count = binReader.unpackUint32() # Get count field
            self[offset] = []
            # For each location to patch:
            for _ in range(0, count):
                self[offset].append(binReader.unpackUint32())
