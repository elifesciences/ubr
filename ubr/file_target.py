import os, shutil, glob2
from ubr import utils

import logging
logger = logging.getLogger(__name__)

def copy_file(src, dest):
    "a wrapper around shutil.copyfile that will create the dest dirs if necessary"
    dirs = os.path.dirname(dest)
    if not os.path.exists(dirs):
        os.makedirs(dirs)
    shutil.copyfile(src, dest)
    return dest

def file_is_valid(src):
    return all([
        os.path.exists(src), # exists?
        os.path.isfile(src), # is a file?
        os.access(src, os.R_OK)]) # is a *readable* file?

def expand_path(src):
    "files can be described using an extended glob syntax with support for recursive dirs"
    return glob2.glob(src)

def wrangle_files(path_list):
    # expand any globs and then flatten the resulting nested structure
    new_path_list = utils.flatten(map(expand_path, path_list))
    new_path_list = filter(file_is_valid, new_path_list)

    # some adhoc error reporting
    try:
        msg = "invalid files have been removed from the backup!"
        assert len(path_list) == len(new_path_list), msg
    except AssertionError:
        # find the difference and then strip out anything that looks like a glob expr
        missing = filter(lambda p: '*' not in p, set(path_list) - set(new_path_list))
        if missing:
            msg = "the following files failed validation and were removed from this backup: %s"
            logger.error(msg, ", ".join(missing))
    return new_path_list

def backup(path_list, destination):
    """embarassingly simple 'copy each of the files specified
    to new destination, ignoring the common parents'"""
    logger.debug('given paths %s with destination %s', path_list, destination)

    new_path_list = wrangle_files(path_list)
    utils.mkdir_p(destination)

    # assumes all paths exist and are file and valid etc etc
    results = []
    for src in new_path_list:
        dest = os.path.join(destination, src.lstrip('/'))
        results.append(copy_file(src, dest))
    return {'output_dir': destination,
            'output': results}



def _restore(path, backup_dir):
    logger.debug("received path %s and input dir %s", path, backup_dir)
    data = {
        'backup_src': os.path.join(backup_dir, path.lstrip('/')),
        'broken_dest': path}
    cmd = "rsync %(backup_src)s %(broken_dest)s" % data
    retcode = utils.system(cmd)
    return (path, retcode == 0)

def restore(path_list, backup_dir):
    """how do we restore files? we rsync the target from the input dir.

    the 'backup_dir' is the dir we read backups from with the given path_list providing further path information

    if the path is "/opt/program/uploaded-files/" and the backup_dir is "/tmp/foo/" than the command looks like:
    rsync <src> <target>
    rsync /tmp/foo/opt/program/uploaded-files/ /opt/program/uploaded-files/
    """
    return {
        'output': map(lambda p: _restore(p, backup_dir), path_list)
    }
    
