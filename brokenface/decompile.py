#! /usr/bin/env python3

import argparse
import logging

from pathlib import Path
from os import remove
from sys import stdout, stderr

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
    logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s]: %(filename)s: %(lineno)d: %(message)s", stream=stdout)
else:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s]: %(filename)s: %(lineno)d: %(message)s", stream=stdout)

success = []
failed = []

for path in [Path(f) for f in fnames]:
    logging.info("Decompiling file: {}".format(path.name))

    logging.info("Parsing file: {}".format(path.name))
    try:
        myFile = dso.File(path)
        myFile.parse()
    except Exception as e:
        logging.error("Failed to parse file: {}: Got exception: {}".format(path.name, repr(e)))
        failed.append(path)
        continue

    logging.info("Successfully parsed file: {}".format(path.name))

    if parseOnly:
        outPath = path.with_suffix(path.suffix + ".txt")
        with open(outPath, "w") as fd:
            myFile.dump(sink=fd)

        logging.info("Parse only option is enabled: Output stored in: {}".format(outPath))
        success.append(path)
    else:
        logging.info("Decoding file: {}".format(path.name))
        try:
            decoder = codec.Decoding(myFile)
            decoder.decode()
        except Exception as e:
            logging.error("Failed to decode file: {}: Got exception: {}".format(path.name, repr(e)))
            failed.append(path)
            continue

        logging.info("Successfully decoded file: {}".format(path.name))

        decoder.tree.rewind()

        outPath = path.with_suffix(path.suffix + ".cs")

        logging.info("Formatting file: {}".format(path.name))
        try:
            with open(outPath, "w") as fd:
                decoder.tree.format(sink=fd)
        except Exception as e:
            logging.error("Failed to format file: {}: Got exception: {}".format(path.name, repr(e)))
            failed.append(path)

            if outPath.is_file():
                remove(outPath)

            continue

        logging.info("Successfully formatted file: {}".format(path.name))

        logging.info("Successfully decompiled file: {}".format(path.name))
        logging.info("Output stored in: {}".format(outPath))

        success.append(path)

if failed:
    logging.info("The following files failed to be decompiled:")

    for path in failed:
        logging.info(str(path))

logging.info("Successfully decompiled {} out of {} input files".format(len(success), len(fnames)))
