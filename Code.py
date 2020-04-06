from FileReading import FileReading

'''
Reference stream that constitutes the script, represented as a list of integers
'''
class Code(list, FileReading):
    '''
    Constructs a Code object (list of integers)
    @param  size        Size of the stream (not the size of the binary data itself)
    @param  fd          File descriptor
    @param  specialByte Special byte that indicates that the following data is part of the code
    '''
    def __init__(self, size, fd, specialCode=0xff):
        # Inherit all characteristics of a list:
        list.__init__(self)

        # Inherit all characteristics of a FileReading object for reading 2-byte long little-endian unsigned words:
        FileReading.__init__(self, fd, 2, "little", False)

        # The code size is a number of opcodes and arguments, not a number of bytes:
        for _ in range(0, size):
            # TODO: Deal with the case of 2 0xFF
            code = self.unpackByte()
            if code == specialCode:
                # Get 2 bytes instead:
                code = self.unpackWord()
            self.append(code)

    '''
    Patches the string offsets into the blank locations of the stream as described in the Identification Table
    @param  identTable  Identification Table described in the file
    '''
    def patch(self, identTable):
        for offset, locations in identTable.items():
            for loc in locations:
                self[loc] = offset
