from struct import unpack

'''
Table of floating point numbers, represented as a list of floats
'''
class FloatTable(list):
    '''
    Constructs a FloatTable object (list of floats)
    @param  data        Binary data that constitutes the table
    @param  precision   Floating-point precision ("float"/"double")
    '''
    def __init__(self, data, precision):
        # Inherit all characteristics of a list:
        list.__init__(self)

        if precision == "float":
            short = "f"
            size = 4
        else:
            short = "d"
            size = 8

        # Parse all floats:
        for idx in range(0, len(data), size):
            self.append(unpack(short, data[idx:idx+size])[0])
