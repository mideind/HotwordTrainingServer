#!/bin/bash

SNOWBOYDIR="snowboy"
VENV="venv"

MODEL_OUT_PATH=$4

# Activate Snowboy Python 2.7 virtual environment
# shellcheck disable=SC1091
source "$SNOWBOYDIR/$VENV/bin/activate"

cd "$SNOWBOYDIR/examples/Python" || exit 1

python generate_pmdl.py -r1="$1" -r2="$2" -r3="$3" \
-lang="en" \
-n="$MODEL_OUT_PATH"
