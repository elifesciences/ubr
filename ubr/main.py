import os, sys, shutil
import yaml
from itertools import takewhile
from datetime import datetime
import logging
import threading

logging.basicConfig()

logger = logging.getLogger(__name__)
logger.level = logging.INFO

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
    
    return {'dir_prefix': dir_prefix, 'output_dir': destination, 'output': results}

def tgz_backup(path_list, destination):
    """does a regular file_backup and then tars and gzips the results.
    the name of the resulting file is 'archive.tar.gz'"""
    # obfuscate the given destination so it doesn't overwrite anything
    original_destination = destination
    destination = os.path.join(destination, ".tgz-tmp") # /tmp/foo/.tgz-tmp
    
    output = file_backup(path_list, destination)

    cd = destination
    target = '*' #os.path.basename(output['output_dir'])
    filename = os.path.basename(original_destination) # this needs to change...!
    filename = 'archive'
    output_path = '%s/%s.tar.gz' % (original_destination, filename)

    cmd = 'cd %s && tar cvzf %s %s --remove-files > /dev/null' % (cd, output_path, target)
    os.system(cmd)

    # amend the results slightly
    #output['results'] = {'files': output['results'],
    #                     'archive': output_path}

    output['output'] = output_path
    
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
        output_dir = ymdhms()
    foo = {}
    for target, args in descriptor.items():
        foo[target] = _backup(target, args, output_dir)
    return foo

#
# s3 wrangling
#

def s3_conn():
    import boto3
    return boto3.client("s3")

# TODO: cachable
def s3_buckets():
    return [m['Name'] for m in s3_conn().list_buckets()]

def s3_bucket_exists(bname):
    return bname in s3_buckets()

def s3_file(bucket, path):
    "returns the object in the bucket at the given path"
    return s3_conn().list_objects(Bucket=bucket, Prefix=path)

def hostname():
    import platform
    return platform.node()

def s3_key(project, hostname, filename):
    now = datetime.now()
    ym = now.strftime("%Y%m")
    ymdhms = now.strftime("%Y%m%d_%H%M%S")
    # path, ext = os.path.splitext(filename) # doesn't work for .tar.gz
    fname, ext = os.path.basename(filename), None
    try:
        dotidx = fname.index('.')
        ext = fname[dotidx + 1:]
        fname = fname[:dotidx]
    except ValueError:
        # couldn't find a dot
        pass
    if ext:
        return "%(project)s/%(ym)s/%(ymdhms)s_%(hostname)s-%(fname)s.%(ext)s" % locals()
    raise ValueError("given file has no extension.")

class ProgressPercentage(object):
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        # To simplify we'll assume this is hooked up
        # to a single filename.
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%)" % (self._filename, self._seen_so_far,
                                             self._size, percentage))
            sys.stdout.flush()

def upload_to_s3(bucket, src, dest):
    logger.info("attempting to upload %r to s3://%s/%s", src, bucket, dest)
    s3_conn().upload_file(src, bucket, dest, Callback=ProgressPercentage(src))

def upload_backup_to_s3(bucket, backup_results, project, hostname):
    """uploads the results of processing a backup.
    `backup_results` should be a dictionary of targets with their results as values.
    each value will have a 'output' key with the outputs for that target.
    these outputs are what is uploaded to s3"""
    for target, target_results in backup_results.items():
        logger.info("processing %s", target)
        # 'target' looks like 'tar-gzipped' or 'mysql' or 'postgresql' etc
        # 'target_results' looks like {..., 'output': '/tmp/foo.tar.gz', ...}
        src = target_results['output']
        if isinstance(src, list):
            logger.warning("uploads of many files is not supported, skipping")
            continue
        if not os.path.exists(src):
            logger.error("the given output does not exist. cannot upload to s3: %s", src)
            continue
        dest = s3_key(project, hostname, src)
        upload_to_s3(bucket, src, dest)

#
# bootstrap
#

def env(nom):
    return os.environ.get(nom, None)

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
        upload_backup_to_s3(bucket, backup(descriptor), project, hostname())

if __name__ == '__main__':
    main(sys.argv[1:])
