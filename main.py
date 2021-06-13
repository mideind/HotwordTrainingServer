#!/usr/bin/env python3
"""

    Hotword Training Server

    Copyright (C) 2021 Miðeind ehf.
    Original author: Sveinbjorn Thordarson

       This program is free software: you can redistribute it and/or modify
       it under the terms of the GNU General Public License as published by
       the Free Software Foundation, either version 3 of the License, or
       (at your option) any later version.
       This program is distributed in the hope that it will be useful,
       but WITHOUT ANY WARRANTY; without even the implied warranty of
       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
       GNU General Public License for more details.
       
    You should have received a copy of the GNU General Public License
    along with this program.  If not, see http://www.gnu.org/licenses/.


    Main web application. Run via uvicorn, e.g. "uvicorn main:app".


"""

from typing import List, Tuple, cast

import os
import json
import struct
import base64
import logging
import subprocess
from io import BytesIO
from uuid import uuid1
from pathlib import Path
from functools import lru_cache

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import Response, JSONResponse, HTMLResponse


__version__ = 0.1

PROGRAM_NAME = "Hotword Training Server"

TMP_DIR = "tmp"  # Relative to repo root
MAX_FILESIZE = 500 * 1024  # 500 KB
MODEL_SUFFIX = "pmdl"
NUM_WAV_REQ = 3  # TODO: Make this variable

MODEL_MIMETYPE = "application/octet-stream"  # Generic data mimetype
JSON_MIMETYPE = "application/json"
WAV_MIMETYPE = "audio/wav"


app = FastAPI(title=PROGRAM_NAME)


def err(msg: str) -> JSONResponse:
    """ Return error response with description message. """
    return JSONResponse(content={"err": True, "errmsg": msg})


@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    """ Web server root. """
    return """
    <html>
        <head>
            <title>{0} v{1}</title>
        </head>
        <body>
            <h1>{0} v{1}</h1>
            <ul>
                <li><a href="/docs">Documentation</a></li>
                <li><a href="/test">Testing</a></li>
            </ul>
        </body>
    </html>
    """.format(
        PROGRAM_NAME, __version__
    )


@app.get("/test", response_class=HTMLResponse)
async def test():
    """ Test model generation via upload form. """
    return """
    <html>
        <head>
            <title>Testing - {0} v{1}</title>
        </head>
        <body>
            <form action="/train" enctype="multipart/form-data" method="post">
                <input name="files" type="file" multiple>
                <input type="submit">
            </form>
        </body>
    </HTML>
    """.format(
        PROGRAM_NAME, __version__
    )


@lru_cache(maxsize=2)
def read_api_key(key_name: str) -> str:
    """ Read the given key from a text file in keys directory. Cached. """
    path = os.path.join(os.path.dirname(__file__), "keys", key_name + ".txt")
    try:
        with open(path) as f:
            return f.read().strip()
    except FileNotFoundError:
        pass
    return ""


def gen_outpaths(num: int = 4) -> Tuple:
    """ Generate random filenames to use when we write to filesystem. """
    names = []
    for n in range(0, num):
        fnid = str(uuid1())
        path = Path(f"{TMP_DIR}/{fnid}")
        while path.exists():
            fnid = str(uuid1())
            path = Path(f"{TMP_DIR}/{fnid}")
        names.append(os.path.abspath(str(path)))
    return tuple(names)


def cleanup(filepaths: Tuple) -> None:
    """ Delete all files in filepaths, if they exist. """
    for fn in filepaths:
        path = Path(fn)
        if path.exists():
            try:
                os.remove(path)
            except Exception as e:
                logging.error(f"Unable to delete file at path {path}: {e}")


def is_valid_wav(data: bytes) -> bool:
    """ Make sure that data is a WAV file w. correct audio format. """
    fh = BytesIO(data)
    riff, size, fformat = struct.unpack("<4sI4s", fh.read(12))
    # logging.info("Riff: %s, Chunk Size: %i, format: %s" % (riff, size, fformat))

    if riff != b"RIFF" or fformat != b"WAVE":
        return False

    # Read header
    chunk_header = fh.read(8)
    subchunkid, subchunksize = struct.unpack("<4sI", chunk_header)

    if subchunkid != b"fmt ":
        return False

    # aformat, channels, samplerate, byterate, blockalign, bps = struct.unpack(
    #     "HHIIHH", fh.read(16)
    # )

    # if channels != 1 or samplerate != 16000:
    #     return False

    # logging.info(
    #     "Format: %i, Channels %i, Sample Rate: %i"
    #     % (aformat, channels, samplerate)
    # )

    return True


@app.post("/train", response_class=Response)
async def train(
    files: List[UploadFile] = File(...), text: bool = True, api_key: str = None
) -> Response:
    """Receives uploaded WAV training files as multipart/form-data, runs
    the training process on them and returns the resulting model file."""

    # Check for API key
    key = read_api_key("APIKey")
    if key and api_key != key:
        return err("Invalid API Key")

    # Make sure we have the correct number of files
    numfiles = len(files)
    if numfiles != NUM_WAV_REQ:
        return err(f"Incorrect number of files: {numfiles} ({NUM_WAV_REQ} required)")

    # Inspect, load and verify all uploaded files
    file_contents: List[bytes] = []
    for f in files:
        # Check content-type
        if f.content_type != WAV_MIMETYPE:
            return err(f"Wrong mimetype for file {f.filename}: {f.content_type}")

        # Read contents of file into memory
        # TODO: More efficient to do a seek first to see if file size is excessive
        contents = cast(bytes, await f.read())

        # Check if file size is excessive
        if len(contents) > MAX_FILESIZE:
            return err(f"File {f.filename} exceeds max size ({MAX_FILESIZE} bytes)")

        # Make sure this is 16-bit mono WAV audio at 16Khz
        if not is_valid_wav(contents):
            return err(f"Wrong file format: {f.filename}. Should be WAV.")

        file_contents.append(contents)

    # Make sure current working directory is the repo root
    basepath, _ = os.path.split(os.path.realpath(__file__))
    os.chdir(basepath)

    # Write uploaded files to tmp/ directory on filesystem
    try:
        filepaths = gen_outpaths()
        for ix, fdata in enumerate(file_contents):
            with open(filepaths[ix], "wb") as fh:
                fh.write(fdata)
    except Exception as e:
        cleanup(filepaths)
        return err(f"Error writing to filesystem: {e}")

    # Run model training script
    try:
        # Script accepts audio file paths as arguments, with
        # final path arg as model output destination
        cmd = ["./gen_model.sh"]
        cmd.extend(filepaths)
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            return err(
                f"Model generation exited with code {0}.\n{1}\n{2}".format(
                    result.returncode, result.stderr, result.stdout
                )
            )
    except Exception as e:
        cleanup(filepaths)
        return err(f"Error generating model: {e}")

    # Read model from filesystem
    model_outpath = filepaths[3]
    with open(model_outpath, "rb") as fh:
        model_bytes = fh.read()

    # Delete generated files
    cleanup(filepaths)

    model_filename = f"model-{str(uuid1())}.{MODEL_SUFFIX}"

    if text:
        # Return JSON response
        b: bytes = base64.standard_b64encode(model_bytes)
        json_response = {
            "err": False,
            "name": model_filename,
            "data": b.decode("ascii"),
        }
        return Response(
            content=json.dumps(json_response),
            status_code=200,
            media_type=JSON_MIMETYPE,
        )
    else:
        # Return a file with correct header
        headers = {"Content-Disposition": f"attachment; filename={model_filename}"}
        return Response(
            content=model_bytes,
            status_code=200,
            media_type=MODEL_MIMETYPE,
            headers=headers,
        )


if __name__ == "__main__":
    """
    Command line invocation for testing purposes.
    In production, use uvicorn to run this web application:

        uvicorn main:app --host [hostname] --port [portnum]

    """
    import uvicorn  # type: ignore

    uvicorn.run(app, host="0.0.0.0", port=8000)
