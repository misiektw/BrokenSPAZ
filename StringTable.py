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
        dict.__init__(self)

        tableLen = binReader.unpackUint32()

        # Split all strings, compute their offsets and add the entries to the dictionary:
        offset = 0
        while offset < tableLen:
            self[offset] = binReader.readString()
            offset += len(self[offset]) + 1
