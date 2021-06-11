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


from typing import List

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import Response, JSONResponse, HTMLResponse


__version__ = 0.1


app = FastAPI()


def _err(msg: str) -> JSONResponse:
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


@app.post("/train")  # type: ignore
async def train(files: List[UploadFile] = File(...)) -> Response:
    return {"filenames": [file.filename for file in files]}
