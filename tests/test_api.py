#!/usr/bin/env python3
"""

    HotwordTrainingServer

    Copyright (C) 2021 Miðeind ehf.

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


    Tests for web application.

"""

import os
import sys

# from fastapi.testclient import TestClient

# Hack to make this Python program executable from the tests subdirectory
basepath, _ = os.path.split(os.path.realpath(__file__))
if basepath.endswith("/tests") or basepath.endswith("\\tests"):
    basepath = basepath[0:-6]
    sys.path.append(basepath)

from app import *  # noqa


def test_all():
    pass
