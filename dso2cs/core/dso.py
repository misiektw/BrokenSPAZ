from sys import stdout
from os.path import getsize
from collections import OrderedDict
from core import binary
import logging

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
        super().__init__(self)

        # Get length, in bytes, of this field:
        self.binLen = binReader.unpackUint32()
        # Store every string and their respective offsets:
        offset = 0
        while offset < self.binLen:
            self[offset] = binReader.readString(self.binLen - offset -1)
            #print(self.binLen-offset-1, offset, self[offset])
            offset += len(self[offset]) + 1
        
    '''
    Gets a string or substring of the table
    @param  key     Key of entry to be retrieved
    '''
    def __getitem__(self, key):
        # If out of bounds:
        if key < 0 or key >= self.binLen:
            raise KeyError

        try:
            # Try default dict operator:
            return super().__getitem__(key)
        except:
            raise KeyError

    def compare(self, other):
        return [ [[k1,self[k1]], [k2,other[k2]]] 
                        for k1,k2 in zip(self,other) if k1!=k2 or self[k1]!=other[k2] ]
        
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
        super().__init__(self)

        # Get length, in entries, of this field:
        length = binReader.unpackUint32()
        # Store floats:
        for _ in range(0, length):
            val = round(binReader.unpackFloat64(), ndigits=6) #4 bytes have rounding error
            if val == round(val): val = round(val)
            self.append(val)

    def compare(self, other):
        return [ [i,[v1,v2]] for i, (v1,v2) in enumerate(zip(self,other)) if v1 != v2 ]

'''
Code stream that constitutes the script, represented as a BinaryReader
'''
class ByteCode(binary.Reading):
    '''
    Constructs a ByteCode object
    @param  binReader   Binary reader to parse the bytecode from
    @param  extCtrlCode Control code to indicate 2-bytes long code value
    @param  endCtrlCode Control code to indicate EOF
    '''
    def __init__(self, binReader, extCtrlCode=0xff, endCtrlCode=0xcdcd):
        # Inherit all characteristics of binary.Reading:
        super().__init__(b'', "little")

        self.extCtrlCode = extCtrlCode
        self.endCtrlCode = endCtrlCode

        self.extCtrlByte = bytes([extCtrlCode])

        # For indexing the bytecode by code:
        self.idxTable = [] # List of code indices
        self.dumpTab = OrderedDict()    # Table for debugging
        self.dumpTab.compare = 'pass' #TODO

        self.codLen = binReader.unpackUint32() # Number of codes
        self.lb_pair_count = binReader.unpackUint32() # Line break pair count
        logging.debug('Linebreak count (not used) {}'.format(self.lb_pair_count))

        # Get start offset of bytecode:
        offset = binReader.pointer
        for _ in range(0, self.codLen):
            # Read byte:
            bt = binReader.read8()
            # If extension control code:
            if bt == self.extCtrlByte:
                # Get next 4 bytes as part of same code:
                bt += binReader.read32()
                # Add address for debugging
                self.dumpTab[binReader.pointer - offset - 1] = int.from_bytes(bt[1:], byteorder='little', signed=False)
            else:
                self.dumpTab[binReader.pointer - offset - 1] = int.from_bytes(bt, byteorder='little', signed=False)
            # Append packed code to stream:
            self.append(bt)
            # Store the index of the code in the stream:
            self.idxTable.append(binReader.pointer - offset - 1)
        
        #Make sure idxTable and dumpTab are synchronized
        assert [ i for i,d in zip(self.idxTable, self.dumpTab.keys()) if i != d ] == [], f"idxTable and dumpTable differ!"

        self.binLen = len(self.byteStream) # Number of bytes
        
        #Read linebreaks. Used for VM debugging?
        self.lb_pairs = []
        for _ in range(0, self.lb_pair_count*2):
            self.lb_pairs.append((binReader.unpackUint32()))

    '''
    Retrieves the code currently pointed at
    '''
    def getCode(self):
        # Get code:
        code = self.unpackUint8()

        # If extension control code: (not sure if valid in v41)
        if code == self.extCtrlCode:
            # Get the actual 4-bytes long code:
            code = self.unpackUint32()
        
        return code

    '''
    Retrieves next two bytes as uint
    '''
    def getUint(self):
        # If first byte is extension control code (used for storing int > 255):
        if self.lookup8() == self.extCtrlByte:
            # Discard first byte:
            self.read8()
            # Get 4-bytes long stream:
            bt = self.read32()
            # Get 4-bytes long unsigned integer:
            return int.from_bytes(bt, byteorder="little", signed=False)
        else:
            return self.unpackUint8()

    '''
    Retrieves next two bytes as string offset
    '''
    def getStringOffset(self):
        # First look if string was patched in, because it can have 0xff as lowest byte
        self.in_patchlocks = self.pointer in self.patchlocs #Helper flag to resolve table access in getStringByOffset
        if self.in_patchlocks:
            #Return patched in string offset
            return self.unpackUint32()
        # Then look for control code. This happens if function table is >255 (in v.41)
        elif self.lookup8() == self.extCtrlByte:
            # Discard 0xFF:
            self.read8()
            offset = self.unpackUint32()
            logging.debug(f'String offset {offset} from control code')
            return offset
        else:
            #Just next byte
            return self.unpackUint8()

    '''
    Retrieves next two bytes as float offset
    '''
    def getFloatOffset(self):
        if self.lookup8() == self.extCtrlCode:
            # Discard 0xFF:
            self.read8()
            return self.unpackUint32()
        # Float table locations in one byte after LOADIMMED_FLT.
        # Probably max. 254, and then from control code.
        return self.unpackUint8()

    '''
    Dump chunk of bytecode
    @param  start   Start byte index of chunk
    @param  end     End byte index of chunk
    '''
    def dump(self, start, end):
        return self.byteStream[start:end]

    '''
    Patches the string offsets into the locations listed in the IdentTable
    @param  identTable  IdentTable described in the file
    @param  stringTable globalStringTable described in the file
    '''
    def patchStrings(self, identTable, stringTable):
        self.patchlocs = [] # torque convoluted magic will go here
        for patch, indexes in identTable.items():
            # Check if offset patch is in StringTable and add it if it's not.
            # Unused function variables are patched in anyway, 
            # but offset is outside of globalStringTable bounds, go figure....
            pval = int.from_bytes(patch, byteorder='little', signed=False) 
            if pval not in  stringTable:
                logging.debug(f'Patch not in string table. Probably unused variable. Adding dummy at {pval}')
                #Add missing key as unused variable and increase binLen to match it.
                var = f'%unused_var{pval}'.encode()
                stringTable[pval] = var
                stringTable.binLen = stringTable.binLen + len(var)
                
            #Patch locations in code stream. 
            for idx in indexes:
                loc  = self.idxTable[idx]
                assert self.byteStream[loc] == 0, "Patching should replace zero!!!"

                self.insert(loc, patch, discard=1)      # Patch location (code index)
                self.binLen = self.binLen +3             #Increase code length

                self.dumpTab[loc] = stringTable[pval]  #put string in dumpTab instead offset 
                
                #We replaced 1 byte with 4, so idxTable and patch locations need to increase as well.
                self.idxTable[idx+1:] = [ v+3 for v in self.idxTable[idx+1:]] #Upadate index table
                for i, pl in enumerate(self.patchlocs): 
                        if pl > loc: self.patchlocs[i]=pl+3
                self.patchlocs.append(loc) # List patched location (byte index)
                #Also shift dumpTab keys to match IPs if key value bigger than current location
                offset_keys = { k+3:self.dumpTab.pop(k) for k in self.dumpTab.copy() if k>loc }
                self.dumpTab.update(offset_keys)

        #Sanity checks
        assert self.binLen == len(self.byteStream), "Bytestream length diffre after patching!"
        assert self.binLen == self.idxTable[-1] + 1, "Last code index doesnt match code length!"
        #Make sure idxTable and dumpTab are synchronized
        assert [ i for i,d in zip(self.idxTable, self.dumpTab.keys()) if i != d ] == [], f"idxTable and dumpTable differ!"

    def __eq__(self, other):
        return self.idxTable == other.idxTable

    def compare(self, other):
        s = self.dumpTab
        o = other.dumpTab
        #tabdif = [ [ (k1, s[k1]),'vs',(k2, o[k2]) ] 
        #                    for k1,k2 in zip(s,o) if s[k1] != o[k2] ]
        oi = list(o)
        try:
            diff =  [ [ [k1, s[k1]], 'vs' , [k2, o[k2]] ] for i,(k1,k2) in enumerate(zip(s,o)) 
                            if s[k1] != o[k2] and s[k1]!=o[oi[i+1]] and s[k1]!=o[oi[i-1]] ][:10]
        finally:
            return "First 10 differences: ", diff

'''
Identification Table that maps the strings to the opcode stream, represented as a dictionary where the keys are the offsets
of the strings and the values are lists of indices of the stream
'''
class IdentTable(dict):
    '''
    Constructs an IdentTable object (dictionary of lists of integers)
    @param  binReader   Binary reader to parse the table from
    '''
    def __init__(self, binReader):
        # Inherit all characteristics of a dictionary:
        super().__init__(self)

        # Get length, in entries, of this field:
        length = binReader.unpackUint32()

        # For each entry of the table:
        for _ in range(0, length):
            offset = binReader.read32() # Get offset field (offset is just 2-bytes long)
            count = binReader.unpackUint32() # Get count field
            self[offset] = []
            # For each location to patch:
            for _ in range(0, count):
                # Store locations into "offset" entry:
                self[offset].append(binReader.unpackUint32())

'''
Raise this exception when something went wrong during parsing
'''
class ParsingError(Exception):
    '''
    Constructs a new ParsingError object
    @param  msg     Specific message to be appended on the beginning of error message
    @param  name    Name of the file being parsed that raised the exception
    '''
    def __init__(self, msg, name):
        self.message = msg + ". File \"" + name + "\" might be corrupted or encoded in a different standard"


'''
Raise this exception when a method that depends on the parsed file is called before parsing
'''
class NotParsedError(Exception):
    '''
    Constructs a new NotParsedError object
    @param  method  Method where the exception was raised
    '''
    def __init__(self, method):
        self.message = "File should be parsed before calling method \"" + method + "\""


'''
Structure of a DSO file and methods for parsing it
'''
class File():
    '''
    Constructs a File object
    @param  path    Path of file to be parsed
    '''
    def __init__(self, path):
        # Save file path:
        self.path = path

        # Save file name:
        self.name = path.name

        # Dump contents to a binary reader:
        with open(path, "rb") as fd:
            self.binReader = binary.Reading(fd.read(), "little")

        # Not parsed yet:
        self.parsed = False

    '''
    Parses the file into tables and bytecode
    '''
    def parse(self):
        # Parse the version of script:
        self.version = self.binReader.unpackUint32()
        logging.info('DSO file version: {}'.format(self.version))
        # Parse the Global String Table:
        self.globalStringTable = StringTable(self.binReader)
        logging.debug('Global string table size: {}'.format(len(self.globalStringTable)))
        # Parse the Function String Table:
        self.functionStringTable = StringTable(self.binReader)
        logging.debug('Function string table size: {}'.format(len(self.functionStringTable)))
        # Parse the Global Float Table:
        self.globalFloatTable = FloatTable(self.binReader)
        logging.debug('Float table size: {}'.format(len(self.globalFloatTable)))
        # Parse the Function Float Table:
        self.functionFloatTable = FloatTable(self.binReader)
        logging.debug('Function float table size: {}'.format(len(self.functionFloatTable)))
        
        # Parse the ByteCode:
        self.byteCode = ByteCode(self.binReader)
        logging.debug('Bytecode size: {}'.format(self.byteCode.binLen))
        # Parse the Ident Table:
        self.identTable = IdentTable(self.binReader)
        logging.debug('Ident table size: {}'.format(len(self.identTable)))

        if getsize(self.path) != self.binReader.pointer:
            raise ParsingError("Parsing did not reach EOF", self.name)

        # Patch bytecode, resolving all references to strings:
        self.byteCode.patchStrings(self.identTable, self.globalStringTable)
        logging.debug('Bytecode size after patching: {}'.format(self.byteCode.binLen))
        self.parsed = True

    '''
    Dumps the structures of the parsed file
    @param  sink    Output to dump contents to
    '''
    def dump(self, sink=stdout):
        if not self.parsed:
            raise NotParsedError("dump")

        print("Script version: {}".format(self.version), file=sink)
        print("", file=sink)

        for name, func in {'Global Str':self.globalStringTable, 'Function Str': self.functionStringTable, 
                        'Global Flt': self.globalFloatTable, 'Function Flt': self.functionFloatTable,
                        'Dump tab': self.byteCode.dumpTab, 'Bytecode': self.byteCode.byteStream, 
                        'idxTable': self.byteCode.idxTable, 'Patch loc': self.byteCode.patchlocs}.items():

            print(f"Dump for {name} {type(func)}:", file=sink)
            print(func, file=sink)
            print("", file=sink)

    '''
        Compare two dso File objects
        @param other dso File object
    '''

    def compare(self, other):
        self.parse()
        other.parse()
        

        for name, func in {'Global Str':'globalStringTable', 'Function Str': 'functionStringTable',
                        'Global Flt': 'globalFloatTable', 'Function Flt': 'functionFloatTable',
                        'Dump tab': 'byteCode'}.items():
            
            s, o = self.__dict__[func], other.__dict__[func]
            if s != o:
                logging.info(f'There are differences in {name} {type(s)} values:')
                print(s.compare(o))
            else:
                logging.info(f'{name} {type(s)} tables identical.')

        #TODO
            # Make decoding compare