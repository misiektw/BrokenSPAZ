from struct import pack, unpack

'''
Generic methods for reading and unpacking bytes and words from a byte stream
'''
class BinaryReading():
    '''
    Constructs a BinaryReading object
    @param  byteStream  Bytes to be copied
    @param  endian      Endianess of byte stream
    '''
    def __init__(self, byteStream, endian):
        self.byteStream = byteStream
        self.endian = endian
        self.pointer = 0

    '''
    Reads bytes from byte stream
    @param  n       Number of bytes to be read
    @return bytes   Bytes read
    '''
    def read(self, n):
        rd = self.byteStream[self.pointer:self.pointer+n]

        if len(rd) != n:
            raise IndexError("Index out of range")

        self.pointer += n

        return rd

    '''
    Reads a single byte from byte stream
    @return bytes   Byte read
    '''
    def read8(self):
        return self.read(1)

    '''
    Reads two bytes from byte stream
    @return bytes   Bytes read
    '''
    def read16(self):
        return self.read(2)

    '''
    Reads four bytes from byte stream
    @return bytes   Bytes read
    '''
    def read32(self):
        return self.read(4)

    '''
    Reads eight bytes from byte stream
    @return bytes   Bytes read
    '''
    def read64(self):
        return self.read(8)

    '''
    Reads bytes until a null byte is found and return the resultant string
    @return string  String read
    '''
    def readString(self):
        byteStream = b''
        rd = self.read8()
        while rd != b'\x00':
            byteStream += rd
            rd = self.read8()

        return byteStream.decode()

    '''
    Reads a byte and unpacks it into an unsigned integer
    @return int 8-bits long unsigned integer
    '''
    def unpackUint8(self):
        return int.from_bytes(self.read8(), byteorder=self.endian, signed=False)

    '''
    Reads two bytes and unpacks it into an unsigned integer
    @return int 16-bits long unsigned integer
    '''
    def unpackUint16(self):
        return int.from_bytes(self.read16(), byteorder=self.endian, signed=False)

    '''
    Reads four bytes and unpacks it into an unsigned integer
    @return int 32-bits long unsigned integer
    '''
    def unpackUint32(self):
        return int.from_bytes(self.read32(), byteorder=self.endian, signed=False)

    '''
    Reads four bytes and unpacks it into a float
    @return int 32-bits long float
    '''
    def unpackFloat32(self):
        return unpack("f", self.read32())[0]

    '''
    The same as read, but without moving the reading pointer
    @param  n       Number of bytes to be looked up
    @return bytes   Bytes looked up
    '''
    def lookup(self, n):
        rd = self.byteStream[self.pointer:self.pointer+n]

        if len(rd) != n:
            raise IndexError("Index out of range")

        return rd

    '''
    Looks up a single byte from byte stream
    @return bytes   Byte looked up
    '''
    def lookup8(self):
        return self.lookup(1)

    '''
    Lookus up a byte and unpacks it into an unsigned integer
    @return int 8-bits long unsigned integer
    '''
    def lookupUnpackUint8(self):
        return int.from_bytes(self.lookup8(), byteorder=self.endian, signed=False)

    '''
    Appends data to the end of the stream
    @param  data    Binary data to be appended
    '''
    def append(self, data):
        self.byteStream += data

    '''
    Inserts data in the stream
    @param  idx     Index of the stream to insert data
    @param  data    Binary data to be inserted
    '''
    def insert(self, idx, data):
        self.byteStream = self.byteStream[:idx] + data + self.byteStream[idx:]

    '''
    Packs an 1-byte long unsigned integer and inserts it in the stream
    @param  idx     Index of the stream to insert data
    @param  num     Integer number to be inserted
    '''
    def packInsertUint8(self, idx, num):
        self.insert(idx, pack("B", num))

    '''
    Packs a 2-byte long unsigned integer and inserts it in the stream
    @param  idx     Index of the stream to insert data
    @param  num     Integer number to be inserted
    '''
    def packInsertUint16(self, idx, num):
        self.insert(idx, pack("H", num))

    '''
    Replaces data in the stream, overwriting what was stored in the place previously
    @param  idx     Index of the stream to be replace data
    @param  data    Binary data to be placed
    '''
    def replace(self, idx, data):
        self.byteStream = self.byteStream[:idx] + data + self.byteStream[idx+len(data):]
