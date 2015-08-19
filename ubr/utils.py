import os
import logging
from datetime import datetime
from compiler.ast import flatten # deprecated, removed in Python3
import errno
from itertools import takewhile
import hashlib

logger = logging.getLogger(__name__)

def env(nom):
    return os.environ.get(nom, None)

def system(cmd):
    logger.info(cmd)
    retval = os.system(cmd)
    logger.info("return status %s", retval)
    return retval

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            logger.error("problem attempting to create path %s", path)
            raise

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
    "returns a list of full paths in the given directory"
    return map(lambda f: os.path.join(d, f), os.listdir(d))

def list_paths_recur(d):
    from os.path import join
    file_list = []
    for root, dirs, files in os.walk(d):
        file_list.extend(map(lambda f: join(root, f), files))
    return file_list

# http://rosettacode.org/wiki/Find_common_directory_path#Python

def allnamesequal(name):
    return all(n == name[0] for n in name[1:])

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
    return datetime.utcnow().strftime("%Y-%m-%d--%H-%M-%S")

def hostname():
    import platform
    return platform.node()

def generate_file_md5(filename, blocksize=2**20):
    "http://stackoverflow.com/questions/1131220/get-md5-hash-of-big-files-in-python"
    m = hashlib.md5()
    with open(filename, "rb") as f:
        while True:
            buf = f.read(blocksize)
            if not buf:
                break
            m.update(buf)
    return m.hexdigest()

def rename_keys(data, keypairs):
    "renames keys in a dictionary. if the replacement is 'None', the key is deleted"
    kp = keypairs[0:1]
    if not kp:
        return data
    old, new = kp[0]
    if new:
        data[new] = data[old]
    del data[old]
    return rename_keys(data, keypairs[1:])


"""
# works but not being used
def group(item_list, grouper):
    "the best my tired brain can do on a friday evening. sorry."
    def _group(item, grouper, store):
        "grouped func should return a pair of match and rest"
        bits = grouper(item)
        first = bits[0]
        if not store.has_key(first):
            store[first] = OrderedDict({})
        rest = bits[1:]
        if rest:
            store[first] =  _group(rest[0], grouper, store[first])
        return store
    _store = OrderedDict({})
    map(lambda i: _group(i, grouper, _store), item_list)
    return _store
"""
