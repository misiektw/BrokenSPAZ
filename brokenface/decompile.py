#! /usr/bin/env python3

import argparse
import logging
from os.path import realpath

from core import dso, codec

def getArgs():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "fnames",
        metavar="FILE_NAME",
        type=str,
        nargs="+",
        help="name of the file to be decompiled"
    )

    parser.add_argument(
        "--parse-only",
        dest="parseOnly",
        action="store_const",
        const="parseOnly",
        default=False,
        help="only parse the file and dump the structures"
    )

    parser.add_argument(
        "--debug",
        dest="debug",
        action="store_const",
        const="debug",
        default=False,
        help="set logging level to DEBUG"
    )

    opt = parser.parse_args()

    return opt.fnames, opt.parseOnly, opt.debug

fnames, parseOnly, debug = getArgs()

if debug:
    logLevel = logging.DEBUG
else:
    logLevel = logging.INFO

success = 0

for f in fnames:
    myFile = dso.File(realpath(f))
    myFile.parse()

    if parseOnly:
        with open(myFile.name + ".txt", "w") as fd:
            myFile.dump(sink=fd)
    else:
        decoder = codec.Decoding(myFile, logLevel=logLevel)

        if decoder.decode():
            success += 1

        decoder.tree.rewind()

        with open(realpath(f) + ".txt", "w") as fd:
            decoder.tree.dump(sink=fd)

print("Successfully decompiled {} out of {} input files".format(success, len(fnames)))
