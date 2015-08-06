import os
from ubr import utils, file_target

import logging

logger = logging.getLogger(__name__)
logger.level = logging.DEBUG

def backup(path_list, destination):
    """does a regular file_backup and then tars and gzips the results.
    the name of the resulting file is 'archive.tar.gz'"""
    destination = os.path.abspath(destination)

    # obfuscate the given destination so it doesn't overwrite anything
    original_destination = destination
    destination = os.path.join(destination, ".tgz-tmp") # /tmp/foo/.tgz-tmp

    output = file_target.backup(path_list, destination)

    ctd = destination
    target = '*'
    filename = os.path.basename(original_destination) # this needs to change...!
    filename = 'archive'
    output_path = '%s/%s.tar.gz' % (original_destination, filename)

    # cd 2015-07-27--15-41-36/.tgz-tmp && tar cvzf 2015-07-27--15-41-36/archive.tar.gz *
    # cd /tmp/foo/.tgz-tmp && tar -cvzf /tmp/foo/archive.tar.gz *
    cmd = 'cd %s && tar cvzf %s %s --remove-files > /dev/null' % (ctd, output_path, target)
    utils.system(cmd)

    output['output'] = [output_path]
    return output

def restore(path_list, backup_dir):
    "just like the file restore, however we unpack the files first before calling `file_restore`"
    pass
