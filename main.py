import os, sys, shutil
import yaml
from itertools import takewhile

import logging
logger = logging.getLogger(__name__)

logging.basicConfig()

#logger.addHandler(logging.StreamHandler())

#
# utils
#

def dir_exists(p):
    return os.path.exists(p) and os.path.isdir(p)

def first(lst):
    try:
        return lst[0]
    except IndexError:
        return None

def rest(lst):
    return lst[1:]

def doall(val, *args):
    "applies all of the functions given in args to the first val"
    func = first(args)
    if func:
        return doall(func(val), *rest(args))
    return val

def list_paths(d):
    return map(lambda f: os.path.join(d, f), os.listdir(d))

# http://rosettacode.org/wiki/Find_common_directory_path#Python

def allnamesequal(name):
    return all(n==name[0] for n in name[1:])

def common_prefix(paths, sep='/'):
    """returns the common directory for a list of given paths.
    if only a single path is given, the parent directory is returned.
    if the only common directory is the root directory, then an empty string is returned."""
    bydirectorylevels = zip(*[p.split(sep) for p in paths])
    common = sep.join(x[0] for x in takewhile(allnamesequal, bydirectorylevels))
    if len(paths) == 1:
        return os.path.dirname(common)
    return common

def ymdhms():
    "returns a UTC datetime stamp as y-m-d--hr-min-sec"
    from datetime import datetime
    return datetime.utcnow().strftime("%Y-%m-%d--%H-%M-%S")

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
    location_list = map(lambda path: doall(path, os.path.expanduser, os.path.abspath), list_paths(descriptor_dir))
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

def flatten(shallow_nested_iterable):
    import itertools
    return itertools.chain.from_iterable(shallow_nested_iterable)

def file_backup(path_list, destination):
    "embarassingly simple 'copy each of the files specified to new destination, ignoring the common parents'"
    logger.debug('given paths %s with destination %s', path_list, destination)

    dir_prefix = common_prefix(path_list)

    # expand any globs and then flatten the resulting nested structure
    new_path_list = flatten(map(expand_path, path_list))
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

    # assumes all paths exist and are file and valid etc etc
    results = []
    for src in new_path_list:
        dest = os.path.join(destination, src[len(dir_prefix):].lstrip('/'))
        results.append(copy_file(src, dest))
    
    return {'dir_prefix': dir_prefix, 'output_dir': destination, 'results': results}

def tgz_backup(path_list, destination):
    "does a regular file_backup and then tars and gzips the results"
    output = file_backup(path_list, destination)
    cmd = 'tar cvzf %s.tar.gz %s' % (output['output_dir'], output['output_dir'])
    print cmd
    #os.system(cmd)
    

def targets():
    return {'files': file_backup,
            'tar-gzipped': tgz_backup}

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
        output_dir = ymdhms()
    return {target: _backup(target, args, output_dir) for target, args in descriptor.items()}

#
#
#

def main(args):
    return map(lambda d: backup(load_descriptor(d)), find_descriptors(args[0]))

if __name__ == '__main__':
    main(sys.argv[1:])
