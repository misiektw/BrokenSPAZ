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
        list.__init__(self)

        tableLen = binReader.unpackUint32()

        for _ in range(0, tableLen):
            self.append(binReader.unpackFloat32())
