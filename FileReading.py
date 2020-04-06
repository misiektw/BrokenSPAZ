'''
Generic methods for reading and unpacking bytes and words from a binary file
'''
class FileReading:
    '''
    Constructs a FileReading object
    @param  fd          File descriptor
    @param  wordSize    Size of the words to be read from the file
    @param  endian      Endianess of the words ("big"/"little")
    @param  signed      Signedness of the words (True/False)
    '''
    def __init__(self, fd, wordSize, endian, signed):
        self.fd = fd
        self.wordSize = wordSize
        self.endian = endian
        self.signed = signed

    '''
    Reads bytes from file
    @param  n       Number of bytes to be read from file
    @return bytes   Bytes read from file
    '''
    def read(self, n):
        return self.fd.read(n)

    '''
    Reads a single byte from file
    @return bytes   Byte read from file
    '''
    def readByte(self):
        return self.read(1)

    '''
    Reads a word from file
    @return bytes   Bytes read from file
    '''
    def readWord(self):
        return self.read(self.wordSize)

    '''
    Reads a byte from file and unpacks it into an integer
    @return int Unpacked byte
    '''
    def unpackByte(self):
        return int.from_bytes(self.readByte(), byteorder=self.endian, signed=self.signed)

    '''
    Reads a word from file and unpacks it into an integer
    @return int Unpacked word
    '''
    def unpackWord(self):
        return int.from_bytes(self.readWord(), byteorder=self.endian, signed=self.signed)
