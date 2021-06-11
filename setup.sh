#!/bin/bash

git clone https://github.com/seasalt-ai/snowboy
cd snowboy
virtualenv -p python2.7 venv
source venv/bin/activate
cd examples/Python
pip install -r requirements.txt