#!/bin/bash
# automatic code formatting

if [ -e venv/bin/python3.6 ]; then
    black ubr/ --target-version py34
else
    # seeing this on new 16.04 lax instances
    echo "black requires Python 3.6+"
fi
