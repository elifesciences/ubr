#!/bin/bash

# everything must pass
set -e

# reload the virtualenv
rm -rf venv/
source install.sh

# upgrade all deps to latest version
pip install pip-review
pip-review --pre # preview the upgrades
echo "[any key to continue ...]"
read -p "$*"
pip-review --auto --pre # update everything

# run the tests
source .unittest.sh
