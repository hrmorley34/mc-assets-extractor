#!/usr/bin/python3
# -*- encoding: utf-8 -*-

import argparse
import logging
from pathlib import Path
import re
import shutil
import json

# Set up args
parser = argparse.ArgumentParser(description="Extracts assets from hashed format")
parser.add_argument(
    "mcfolder",
    help="Minecraft data location (.minecraft) - must contain assets/indexes and assets/objects",
)
parser.add_argument(
    "-t",
    "--table",
    dest="table",
    default="latest",
    help="Version of table to read - defaults to latest",
)

outparser = parser.add_mutually_exclusive_group()
outparser.add_argument(
    "-o",
    "--output",
    dest="loc",
    default="./assets/",
    help="Folder to write files to - defaults to './assets/'",
)
outparser.add_argument(
    "-l", "--list", dest="list", action="store_true", help="List the files in the table"
)

filtparser = parser.add_mutually_exclusive_group()
filtparser.add_argument(
    "-r",
    "--regex",
    dest="regex",
    default=None,
    help="Regular expression of which files to write",
)
filtparser.add_argument(
    "-g",
    "--glob",
    dest="glob",
    default=None,
    help="Glob of which files to write (eg. minecraft/**/*.ogg)",
)

verbparser = parser.add_mutually_exclusive_group()
verbparser.add_argument(
    "-v",
    "--verbose",
    dest="debug",
    action="count",
    default=0,
    help="Increase debug level",
)
verbparser.add_argument(
    "-q",
    "--quiet",
    dest="debug",
    action="store_const",
    const=-1,
    help="Only output errors, not warnings",
)


def expandpath(path) -> Path:
    " Fully expand a path "
    return Path(path).expanduser().resolve().absolute()


if __name__ == "__main__":
    # Parse args
    args = parser.parse_args()

    logging.basicConfig(format="%(levelname)s: %(message)s", level=30 - 10 * args.debug)

    mcfolder = expandpath(args.mcfolder)
    if not mcfolder.exists():
        raise FileNotFoundError(f"Folder {mcfolder} does not exist")
    if not (mcfolder / "assets").exists():
        raise FileNotFoundError(f"Folder {mcfolder}/assets does not exist")
    if not (mcfolder / "assets" / "objects").exists():
        raise FileNotFoundError(f"Folder {mcfolder}/assets/objects does not exist")

    tablename = args.table

    if tablename.lower() == "latest":
        indexes_folder = mcfolder / "assets" / "indexes"
        if not indexes_folder.exists():
            raise FileNotFoundError(f"Folder {indexes_folder} does not exist")

        jsons_by_version = {}
        for path in indexes_folder.glob("*.json"):
            try:
                version = tuple(map(int, path.stem.split(".")))
                jsons_by_version[version] = path
            except ValueError:
                continue

        if len(jsons_by_version) == 0:
            raise FileNotFoundError(f"No index tables found in {indexes_folder}")
        else:
            maxversion = max(jsons_by_version)
            table_json = jsons_by_version[maxversion]

    elif (mcfolder / "assets" / "indexes" / f"{tablename}.json").exists():
        table_json = mcfolder / "assets" / "indexes" / f"{tablename}.json"

    elif (mcfolder / "assets" / "indexes" / tablename).exists():
        table_json = mcfolder / "assets" / "indexes" / tablename

    elif expandpath(tablename).exists():
        table_json = expandpath(tablename)

    else:
        raise FileNotFoundError("No index table")

    logging.info(f"JSON file found: {table_json}")

    if not args.list:
        outputfolder = expandpath(args.loc)
        if not outputfolder.exists():
            logging.warning(f"{outputfolder} not found - creating")
            outputfolder.mkdir(parents=True, exist_ok=True)

    with open(table_json, mode="r") as f:
        json_data = json.load(f)
        logging.info(f"Read json from {table_json}")

    if args.regex is not None:
        regexmatch = re.compile(args.regex)
        logging.info(f"Compiled regex: {regexmatch}")

        jobjects = {}
        for k in json_data["objects"]:
            if regexmatch.match(k):
                logging.debug(f"Matched {k}")
                jobjects[k] = json_data["objects"][k]
            else:
                logging.debug(f"Failed to match {k}")
                continue
    elif args.glob is not None:
        jobjects = {}
        for k in json_data["objects"]:
            if Path(k).match(args.glob):
                logging.debug(f"Matched {k}")
                jobjects[k] = json_data["objects"][k]
            else:
                logging.debug(f"Failed to match {k}")
                continue
    else:
        jobjects = json_data["objects"]

    if len(jobjects) == 0:
        logging.warning("Zero items match the filter.")
    elif args.list:
        logging.info(f"Listing {len(jobjects)} items")
        for k, v in sorted(jobjects.items()):
            print("{}: {}".format(v["hash"], k))
    else:
        logging.info(f"Starting: {len(jobjects)} items")
        for k, v in jobjects.items():
            h = v["hash"]

            logging.debug(f"Finding hash {h}")
            hfile = mcfolder / "assets" / "objects" / h[:2] / h
            if hfile.exists():
                ofile = outputfolder / k
                ofile.parents[0].mkdir(parents=True, exist_ok=True)
                if ofile.exists():
                    logging.warning(f"{ofile} already exists - overwriting")

                logging.debug(f"Copying file {hfile}...")
                shutil.copy2(hfile, ofile)
                logging.debug("Copied file")
            else:
                logging.warning(f"Can't find hash {h} (at {hfile})")

        logging.info("Finished.")

    exit(0)
