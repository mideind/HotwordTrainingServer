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


"""


from typing import List, Tuple, cast

import os
import struct
import subprocess
from io import BytesIO
from uuid import uuid1
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import Response, JSONResponse, HTMLResponse


__version__ = 0.1


app = FastAPI()


def err(msg: str) -> JSONResponse:
    return JSONResponse(content={"err": True, "errmsg": msg})


@app.get("/", response_class=HTMLResponse)  # type: ignore
async def root() -> str:
    return """
<html>
    <head><title>Hotword Training Server v{0}</title></head>
    <body>
        <h1>Hotword Training Server v{0}</h1>
        <ul><li><a href="/docs">Documentation</a></li></ul>
    </body>
</html>
""".format(
        __version__
    )


@app.get("/test", response_class=HTMLResponse)
async def test():
    return """
<body>
<!--<form action="/files/" enctype="multipart/form-data" method="post">
<input name="files" type="file" multiple>
<input type="submit">
</form>-->
<form action="/train" enctype="multipart/form-data" method="post">
<input name="files" type="file" multiple>
<input type="submit">
</form>
</body>
    """


TMP_DIR = "tmp"
MAX_FILESIZE = 500 * 1024  # 500 KB
PMDL_MIMETYPE = "application/pmdl"
PMDL_FILENAME = "model.pmdl"
NUM_WAV_REQ = 3


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
    """ Delete all files created during model training. """
    for fn in filepaths:
        path = Path(fn)
        if path.exists():
            os.remove(path)


def is_valid_wav(data: bytes) -> bool:
    """ Check that data is WAV file w. correct audio format. """
    fh = BytesIO(data)
    riff, size, fformat = struct.unpack("<4sI4s", fh.read(12))
    # print("Riff: %s, Chunk Size: %i, format: %s" % (riff, size, fformat))

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

    # print(
    #     "Format: %i, Channels %i, Sample Rate: %i"
    #     % (aformat, channels, samplerate)
    # )

    return True


@app.post("/train", response_class=Response)  # type: ignore
async def train(files: List[UploadFile] = File(...)) -> Response:
    """Receives uploaded WAV training files as multipart/form-data, runs
    the training process on them and returns the resulting pmdl file."""

    # Check for API key
    # TODO: Implement this

    # Make sure we have the correct number of files
    numfiles = len(files)
    if numfiles != NUM_WAV_REQ:
        return err(f"Incorrect number of files: {numfiles} ({NUM_WAV_REQ} required)")

    # Read all uploaded files into memory and verify
    file_contents: List[bytes] = []
    for f in files:
        contents = cast(bytes, await f.read())
        # Check if file size is excessive
        if len(contents) > MAX_FILESIZE:
            return err(f"File too large: {f.filename}")

        # Make sure this is 16-bit mono WAV audio at 16Khz
        if not is_valid_wav(contents):
            return err(f"Wrong file format: {f.filename}")

        file_contents.append(contents)

    # Make sure current working directory is repo root
    basepath, _ = os.path.split(os.path.realpath(__file__))
    os.chdir(basepath)

    # Write files to tmp/ directory on filesystem
    try:
        filepaths = gen_outpaths()
        # print(filepaths)
        for ix, fdata in enumerate(file_contents):
            with open(filepaths[ix], "wb") as fh:
                fh.write(fdata)
    except Exception as e:
        cleanup(filepaths)
        return err(f"Error writing to filesystem: {e}")

    # Run model training script
    try:
        cmd = ["./gen_model.sh"]
        cmd.extend(filepaths)
        # print(cmd)
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

    # Return it as a file w. correct headers
    headers = {"Content-Disposition": f"attachment; filename={PMDL_FILENAME}"}
    return Response(
        content=model_bytes,
        status_code=200,
        media_type=PMDL_MIMETYPE,
        headers=headers,
    )
