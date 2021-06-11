#!/bin/bash

SNOWBOYDIR="snowboy"
VENV="venv"

F1=$1
F2=$2
F3=$3
MODEL_OUT_PATH=$4

# Activate Snowboy Python 2.7 virtual environment
source "$SNOWBOYDIR/$VENV/bin/activate"

cd "$SNOWBOYDIR/examples/Python"

python generate_pmdl.py -r1=$F1 -r2=$F2 -r3=$F3 -lang=en -n=$MODEL_OUT_PATH
