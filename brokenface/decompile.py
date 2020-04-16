#! /usr/bin/env python3

from sys import argv
from os.path import realpath

from core import dso, codec

myFile = dso.File(realpath(argv[1]))
myFile.parse()

with open("/tmp/dso-dump.txt", "w") as fd:
    myFile.dump(sink=fd)

decoder = codec.Decoding(myFile)
decoder.decode()

decoder.tree.rewind()

with open("/tmp/decompiled.txt", "w") as fd:
    decoder.tree.dump(sink=fd)
