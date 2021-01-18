#! /usr/bin/env python3

import argparse
import logging

from pathlib import Path
from os import remove
from sys import stdout, stderr

from core import dso, codec

def compare_dso(file1, file2):
    files = {file1:[], file2:[]}
    for file in files:
        file.append()


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
        "--debug",
        dest="debug",
        action="store_const",
        const="debug",
        default=False,
        help="set logging level to DEBUG"
    )
    parser.add_argument(
        "--compare",
        dest="compare",
        action="store_const",
        const="compare",
        default=False,
        help="compare two DSO files"
    )


    opt = parser.parse_args()

    return opt.fnames, opt.debug, opt.compare


fnames, debug, compare = getArgs()
#fnames, debug, compare = ["setup.cs.dso"], True, False
#fnames, debug, compare = ["datablocks.cs.dso"], True, False
#fnames, debug, compare = ["globalTuning.cs.dso"], True
#fnames, debug, compare = ["researchScreen.cs.dso"], True

if debug:
    logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s]: %(filename)s: %(lineno)d: %(message)s", stream=stdout)
else:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s]: %(filename)s: %(lineno)d: %(message)s", stream=stdout)

success = []
failed = []

if compare:
    try:
        f1, f2 = [ Path(f) for f in fnames ]
    except:
        logging.error('Need two DSO files for compare.'); exit(-1)
    else:
        dso.File(f1).compare(dso.File(f2))
        logging.info(f'Finished comparing {f1} and {f2}')
        exit(0)

for path in [Path(f) for f in fnames]:
    logging.info("Parsing file: {}".format(path.name))
    try:
        myFile = dso.File(path)
        myFile.parse()
    except Exception as e:
        if debug: logging.exception("Failed to parse file: {}: Got exception: {}".format(path.name, repr(e)))
        else: logging.error("Failed to parse file: {}: Got exception: {}".format(path.name, repr(e)))
        failed.append(path)
        continue

    logging.info("Successfully parsed file: {}".format(path.name))

    if debug:
        outPath = path.with_suffix(path.suffix + ".txt")
        with open(outPath, "w") as fd:
            myFile.dump(sink=fd)

        logging.debug("Debug enabled. Additional output stored in: {}".format(outPath))
   
    logging.info("Decoding file: {}".format(path.name))
    try:
        decoder = codec.Decoding(myFile)
        decoder.decode()
    except Exception as e:
        if debug: 
            logging.exception("Failed to decode file: {}: Got exception: {}".format(path.name, repr(e)))
            logging.warning('Writing partial decode to file')
        else: 
            logging.error("Failed to decode file: {}: Got exception: {}".format(path.name, repr(e)))
        failed.append(path)
    else:
        logging.info("Successfully decoded file: {}".format(path.name))

    decoder.tree.rewind()
    outPath = path.with_suffix(path.suffix + ".cs")

    try:
        if not outPath in failed or debug:
            logging.info("Formatting file: {}".format(path.name))
            with open(outPath, "w") as fd:
                decoder.tree.format(sink=fd)
    except Exception as e:
        logging.error("Failed to format file: {}: Got exception: {}".format(path.name, repr(e)))
        failed.append(path)
        if outPath.is_file() and not debug:
            remove(outPath)
        continue

    if path in failed and debug:
        logging.info("Partially formatted file: {}. Output stored in: {}".format(path.name, outPath))
    elif path in failed:
        logging.info("Failed to format file: {}.".format(path.name))
    
    success.append(path)

if failed:
    logging.info("The following failed to be decompiled fully:")

    for path in failed:
        logging.info(str(path))

logging.info("Fully decompiled {} out of {} input files".format(len(success), len(fnames)))
