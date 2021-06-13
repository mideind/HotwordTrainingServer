#!/bin/bash

git clone https://github.com/seasalt-ai/snowboy
cd snowboy || exit 1
virtualenv -p python2.7 venv
# shellcheck disable=SC1091
source venv/bin/activate
cd examples/Python || exit 1
pip install -r requirements.txt
deactivate