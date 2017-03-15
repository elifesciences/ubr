#!/bin/bash
# calls the command line interface to the universal backup/restore script
# assumes script is being run from directory it lives in
set -e
. install.sh > /dev/null

# usage: ubr <config-dir> <backup|restore> <dir|s3> [target] [path]
python -m ubr.main "$@"
