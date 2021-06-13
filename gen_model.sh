#!/bin/bash

# Make sure we're getting correct number of arguments
if [ $# -ne 4 ]; then
    echo "Wrong number of arguments"
    exit 64 # EX_USAGE
fi

SNOWBOYDIR="snowboy"
VENV="venv"

MODEL_OUT_PATH=$4

# Activate Snowboy Python 2.7 virtual environment
# shellcheck disable=SC1091,SC1090
source "$SNOWBOYDIR/$VENV/bin/activate"

cd "$SNOWBOYDIR/examples/Python" || exit 1

python generate_pmdl.py \
-r1="$1" \
-r2="$2" \
-r3="$3" \
-lang="en" \
-n="$MODEL_OUT_PATH"
