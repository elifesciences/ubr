#!/bin/bash
# automatic code formatting

if [ -e venv/bin/python3.6 ]; then
    pip install "black~=19.3b0"
    black ubr/ --target-version py34
else
    # seeing this on new 16.04 lax instances
    echo "black requires Python 3.6+"
fi
