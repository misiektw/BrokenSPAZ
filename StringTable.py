'''
Table of strings, represented as a dictionary where the keys are the offsets (addresses) of the strings in the file and the
values are the strings themselves
'''
class StringTable(dict):
    '''
    Constructs a StringTable object (dictionary of strings)
    @param  data    Binary data that constitutes the table
    '''
    def __init__(self, data):
        # Inherit all characteristics of a dictionary:
        dict.__init__(self)

        # Split all strings, compute their offsets and add the entries to the dictionary:
        offset = 0
        for byte_stream in data.split(b'\x00')[:-1]:
            self[offset] = byte_stream.decode() # Decode byte stream as string
            offset += len(byte_stream) + 1 # Update offset
