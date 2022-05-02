import os
from ubr import utils
from .utils import ensure, unique
from functools import partial
import yaml
from schema import Schema, SchemaError
from . import conf
from functools import reduce

LOG = conf.logging.getLogger(__name__)

#
# 'descriptor' wrangling
# a descriptor is a YAML file in /etc/ubr/ that ends with '-backup.yaml'
# it looks like:
#
# target:
#   - name
#
# with 'target' being one of "files", "tar-gzipped", "mysql-database" or "postgresql-database"
# and 'name' just the name of the target.
#
# a target can have many names, each of which becomes a separate backup. For example:
#
# postgresql-database:
#   - db1
#   - db2
#   - foodb
#
# and a descriptor can have many targets. For example:
#
# mysql-database:
#   - db1
#
# postgresql-database:
#   - db2
#   - db3
#
# tar-gzipped:
#   - /var/log/myapp/*

#
# description pruning
#


def _subdesc(desc, path):
    """a path looks like: <type>.<target>
    for example: `file./opt/thing/` or `mysql-database.mydb1"""
    bits = path.split(".", 1)
    ensure(
        len(bits) == 2,
        "expecting just two bits (type and target), got %s bits: %s"
        % (len(bits), path),
        ValueError,
    )
    toplevel, target = bits
    # lsh@2022-04-25: changed from hard fail with ValueError to soft fail with empty map
    if not toplevel in desc:
        LOG.warning("no %r in descriptor: %s" % (toplevel, desc))
        return {}
    if not target in desc[toplevel]:
        LOG.warning("given descriptor has no path %r" % path)
        return {}
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


def project_name(path):
    "returns the name of the project given a path to a file"
    try:
        filename = os.path.basename(path)
        return filename[: filename.index("-backup.yaml")]
    except ValueError:
        msg = (
            "given descriptor file isn't suffixed with '-backup.yaml' - I can't determine the project name: %r"
            % path
        )
        LOG.debug(msg)
        return None


def is_descriptor(path):
    "return True if the given path or filename looks like a descriptor file"
    return project_name(path) is not None


def find_descriptors(descriptor_dir):
    "returns a list of descriptors at the given path"
    # '/descriptor/dir/' => ['/descriptor/dir/foo-backup.yaml', '/descriptor/dir/bar-backup.yaml']
    return sorted(
        [
            os.path.abspath(os.path.expanduser(path))
            for path in utils.list_paths(descriptor_dir)
            if os.path.exists(path) and is_descriptor(path)
        ]
    )


def validate_descriptor(descriptor):
    "returns `True` if the given `descriptor` is correctly structured."
    try:
        fn = lambda v: v in conf.KNOWN_TARGETS
        descr_schema = Schema({fn: [str]})
        return descr_schema.validate(descriptor)
    except SchemaError as err:
        raise AssertionError(str(err))


def load_descriptor(descriptor_path, path_list=[]):
    data = yaml.safe_load(open(descriptor_path, "r"))
    if not data:
        return {}
    descriptor = validate_descriptor(data)
    if path_list:
        return subdescriptor(descriptor, path_list)
    return descriptor
