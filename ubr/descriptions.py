import os
from ubr import utils
from utils import ensure, unique
from functools import partial
import yaml
from schema import Schema, SchemaError
from conf import logging

LOG = logging.getLogger(__name__)

#
# 'descriptor' wrangling
# a descriptor is a yaml file in /etc/ubr/ that ends with '-backup.yaml'
#


#
# description pruning
#

def _subdesc(desc, path):
    """a path looks like: <type>.<target> 
    for example: `file./opt/thing/` or `mysql-database.mydb1"""
    bits = path.split('.', 1)
    ensure(len(bits) == 2, "expecting just two bits, got %s bits: %s" % (len(bits), path), ValueError)
    toplevel, target = bits
    ensure(toplevel in desc, "descriptor has no %r key" % toplevel, ValueError)
    ensure(target in desc[toplevel], "given descriptor has no path %r" % path, ValueError)
    return {toplevel: [target]}

def subdescriptor(desc, path_list):
    "same as `_subdesc` but supports many paths and the results are merged together"
    def merge(acc, x):
        for key, val in x.items():
            if key in acc:
                # conflict, merge children
                val = unique(acc[key] + val)
            acc[key] = val
        return acc
    return reduce(merge, map(partial(_subdesc, desc), path_list))

#
# utils
#

def pname(path):
    "returns the name of the project given a path to a file"
    try:
        filename = os.path.basename(path)
        return filename[:filename.index('-backup.yaml')]
    except ValueError:
        msg = "given descriptor file isn't suffixed with '-backup.yaml' - I can't determine the project name: %r" % path
        LOG.debug(msg)
        return None

def is_descriptor(path):
    "return True if the given path or filename looks like a descriptor file"
    return pname(path) != None

def find_descriptors(descriptor_dir):
    "returns a list of descriptors at the given path"
    expandtoabs = lambda path: utils.doall(path, os.path.expanduser, os.path.abspath)
    location_list = map(expandtoabs, utils.list_paths(descriptor_dir))
    return sorted(filter(is_descriptor, filter(os.path.exists, location_list)))

def validate_descriptor(descriptor):
    "return True if the given descriptor is correctly structured."
    try:
        descr_schema = Schema(
            {lambda v: v in ['files', 'tar-gzipped', 'mysql-database']: [str]})
        return descr_schema.validate(descriptor)
    except SchemaError as err:
        raise AssertionError(str(err))

def load_descriptor(descriptor_path, path_list=[]):
    descriptor = validate_descriptor(yaml.load(open(descriptor_path, "r")))
    if path_list:
        return subdescriptor(descriptor, path_list)
    return descriptor
