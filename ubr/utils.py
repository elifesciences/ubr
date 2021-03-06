import shutil
import tempfile
from contextlib import contextmanager
import sys
import os, subprocess
from datetime import datetime
import errno
from itertools import takewhile
import collections
import hashlib
from .conf import logging
from functools import reduce

LOG = logging.getLogger(__name__)


def visit(data, pred, fn):
    "visits every value in the given data and applies `fn` when `pred` is true "
    if pred(data):
        data = fn(data)
        # why don't we return here after matching?
        # the match may contain matches within child elements (lists, dicts)
        # we want to visit them, too
    if isinstance(data, dict):
        return {key: visit(val, pred, fn) for key, val in data.items()}
    elif isinstance(data, list):
        return [visit(row, pred, fn) for row in data]
    # unsupported type/no further matches
    return data


def group_by(lst, key):
    idx = {}
    for i in lst:
        ikey = i[key]
        grp = idx.get(ikey, [])
        grp.append(i)
        idx[ikey] = grp
    return idx


def group_by_many(lst, key_list):
    key = key_list[0]
    rest = key_list[1:]
    group = group_by(lst, key)
    if rest:
        return {
            grouper: group_by_many(sublist, rest) for grouper, sublist in group.items()
        }
    return group


def flatten(x):
    def iselement(e):
        return not (isinstance(e, collections.Iterable) and not isinstance(e, str))

    for el in x:
        if iselement(el):
            yield el
        else:
            yield from flatten(el)


def unique(lst):
    # http://stackoverflow.com/questions/13757835/make-python-list-unique-in-functional-way-map-reduce-filter
    return reduce(lambda x, y: x + [y] if not y in x else x, lst, [])


def ensure(assertion, msg, ExceptionClass=AssertionError):
    """intended as a convenient replacement for `assert` statements that
    get compiled away with -O flags"""
    if not assertion:
        raise ExceptionClass(msg)


def system1(cmd):
    LOG.info(cmd)
    retval = os.system(cmd)
    LOG.info("return status %s", retval)
    return retval


def system2(cmd):
    args = ["/bin/bash", "-c", cmd]
    # print args
    process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, stderr = process.communicate()
    # return process.returncode, stdout
    LOG.info(stdout)
    LOG.warning(stderr)
    return process.returncode


system = system2


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            LOG.error("problem attempting to create path %s", path)
            raise


def dir_exists(p):
    return os.path.exists(p) and os.path.isdir(p)


def first(lst):
    try:
        return lst[0]
    except IndexError:
        return None


def subdict(data, key_list):
    return {key: val for key, val in data.items() if key in key_list}


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
    return [os.path.join(d, f) for f in os.listdir(d)]


def list_paths_recur(d):
    from os.path import join

    file_list = []
    for root, dirs, files in os.walk(d):
        file_list.extend([join(root, f) for f in files])
    return file_list


# http://rosettacode.org/wiki/Find_common_directory_path#Python


def allnamesequal(name):
    return all(n == name[0] for n in name[1:])


def common_prefix(paths, sep="/"):
    """returns the common directory for a list of given paths.
    if only a single path is given, the parent directory is returned.
    if the only common directory is the root directory, then an empty string is returned."""
    bydirectorylevels = list(zip(*[p.split(sep) for p in paths]))
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


def generate_file_md5(filename, blocksize=2 ** 20):
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


def pairwise(lst):
    # very clever lazy pairwise traversal:
    # taken from: http://stackoverflow.com/questions/4628290/pairs-from-single-list
    iterator = iter(lst)
    return zip(iterator, iterator)


def enumerated(lst):
    return dict(list(zip(list(range(1, len(lst) + 1)), lst)))


def isint(x):
    try:
        int(x)
        return True
    except (TypeError, ValueError):
        return False


def choose(prompt, choices, label_fn=None):
    try:
        if label_fn:
            labels = list(
                zip(choices, list(map(label_fn, choices)))
            )  # ll: [(/foo/bar/baz, baz), (/foo/bar/bup, bup)]
        else:
            labels = list(zip(choices, choices))
        idx = enumerated(choices)  # ll: {1: /foo/bar/baz, 2: /foo/bar/bup}

        while True:
            # present menu
            for i, pair in enumerate(labels):
                print("%s: %s" % (i + 1, pair[1]))
            print()

            # prompt user
            uin = input(prompt)

            # hygeine
            if not uin or not uin.strip():
                print("a choice is required (ctrl-c to quit)")
                continue
            if not isint(uin):
                print("a -numeric- choice is required (ctrl-c to quit)")
                continue
            uin = int(uin)
            if uin not in idx:
                print(
                    "a choice between 1 and %s is required (ctrl-c to quit)"
                    % len(choices)
                )
                continue

            # all good,
            return idx[uin]

    except KeyboardInterrupt:
        print()
        sys.exit(1)


@contextmanager
def TemporaryDirectory():
    name = tempfile.mkdtemp()
    try:
        yield name
    finally:
        shutil.rmtree(name)


def tempdir():
    name = tempfile.mkdtemp()
    return (name, lambda: shutil.rmtree(name))
