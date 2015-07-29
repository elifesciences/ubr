import os, sys, shutil
import yaml
from datetime import datetime
import logging
from ubr import utils, s3


logging.basicConfig()

logger = logging.getLogger(__name__)
logger.level = logging.INFO

#logger.addHandler(logging.StreamHandler())

# 
#
#

def valid_descriptor(descriptor):
    assert isinstance(descriptor, dict), "the descriptor must be a dictionary"
    known_targets = targets().keys()
    for target_name, target_items in descriptor.items():
        assert isinstance(target_items, list), "a target's list of things to back up must be a list"
        assert target_name in known_targets, "we don't recognize what a %r is. known targets: %r" % (target_name, ', '.join(known_targets))
    return True

def is_descriptor(path):
    "returns true if the given path or filename looks like a backup descriptor"
    fname = os.path.basename(path)
    suffix = '-backup.yaml' # descriptors look like: elife-api-backup.yaml or lagotto-backup.yaml
    return fname.endswith(suffix)

def find_descriptors(descriptor_dir):
    "returns a list of descriptors at the given path"
    location_list = map(lambda path: utils.doall(path, os.path.expanduser, os.path.abspath), utils.list_paths(descriptor_dir))
    return sorted(filter(is_descriptor, filter(os.path.exists, location_list)))

def load_descriptor(descriptor):
    return yaml.load(open(descriptor, "r"))

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
    import glob2
    return glob2.glob(src)

def file_backup(path_list, destination):
    "embarassingly simple 'copy each of the files specified to new destination, ignoring the common parents'"
    logger.debug('given paths %s with destination %s', path_list, destination)

    dir_prefix = utils.common_prefix(path_list)

    # expand any globs and then flatten the resulting nested structure
    new_path_list = utils.flatten(map(expand_path, path_list))
    new_path_list = filter(file_is_valid, new_path_list)

    # some adhoc error reporting
    try:
        assert len(path_list) == len(new_path_list), "invalid files have been removed from the backup!"
    except AssertionError, e:
        # find the difference and then strip out anything that looks like a glob expr
        missing = filter(lambda p: '*' not in p, set(path_list) - set(new_path_list))
        if missing:
            msg = "the following files failed validation and were removed from this backup: %s"
            logger.error(msg, ", ".join(missing))

    utils.mkdir_p(destination)

    # assumes all paths exist and are file and valid etc etc
    results = []
    for src in new_path_list:
        dest = os.path.join(destination, src[len(dir_prefix):].lstrip('/'))
        results.append(copy_file(src, dest))
    
    return {'dir_prefix': dir_prefix, 'output_dir': destination, 'output': results}

def tgz_backup(path_list, destination):
    """does a regular file_backup and then tars and gzips the results.
    the name of the resulting file is 'archive.tar.gz'"""
    destination = os.path.abspath(destination)
    
    # obfuscate the given destination so it doesn't overwrite anything
    original_destination = destination
    destination = os.path.join(destination, ".tgz-tmp") # /tmp/foo/.tgz-tmp
    
    output = file_backup(path_list, destination)

    cd = destination
    target = '*' #os.path.basename(output['output_dir'])
    filename = os.path.basename(original_destination) # this needs to change...!
    filename = 'archive'
    output_path = '%s/%s.tar.gz' % (original_destination, filename)

    # cd 2015-07-27--15-41-36/.tgz-tmp && tar cvzf 2015-07-27--15-41-36/archive.tar.gz *
    # cd /tmp/foo/.tgz-tmp && tar -cvzf /tmp/foo/archive.tar.gz *
    cmd = 'cd %s && tar cvzf %s %s --remove-files > /dev/null' % (cd, output_path, target)
    utils.system(cmd)

    output['output'] = [output_path]
    return output

#
#
#

def targets():
    import mysql_backup
    return {'files': file_backup,
            'tar-gzipped': tgz_backup,
            'mysql-database': mysql_backup.backup}

# looks like: backup('file', ['/tmp/foo', '/tmp/bar'], 'file:///tmp/foo.tar.gz')
def _backup(target, args, destination):
    "a descriptor is a set of targets and inputs to the target functions."
    try:
        return targets()[target](args, destination)
    except KeyError:
        pass

# looks like: backup({'file': ['/tmp/foo']}, 'file://')
def backup(descriptor, output_dir=None):
    if not output_dir:
        output_dir = utils.ymdhms()
    foo = {}
    for target, args in descriptor.items():
        foo[target] = _backup(target, args, output_dir)
    return foo

def restore(target, path):
    ""
    pass


#
# bootstrap
#

def main(args):

    def pname(filename):
        try:
            filename = os.path.basename(filename)
            return filename[:filename.index('-backup.yaml')]
        except ValueError:
            logger.warning("the given backup descriptor isn't suffixed with '-backup.yaml' - I don't know where the project name starts and ends!")
            return None
    
    given_dir = args[0]
    bucket = 'elife-app-backups'
    for descriptor in find_descriptors(given_dir):
        project = pname(descriptor)
        if not project:
            logger.warning("no project name, skipping given descriptor %r", descriptor)
            continue
        s3.upload_backup(bucket, backup(load_descriptor(descriptor)), project, utils.hostname())

if __name__ == '__main__':
    main(sys.argv[1:])
