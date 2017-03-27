from ubr import conf, utils
from ubr.utils import ensure
import os, copy
from os.path import join

def defaults(db=None, **overrides):
    args = copy.deepcopy(conf.POSTGRESQL)
    args['dbname'] = db
    args.update(overrides)
    return args

def backup_name(dbname):
    "returns the expected name of the dump for the given database"
    if not dbname or type(dbname) not in [str, int]:
        raise ValueError("unhandled type %r" % type(dbname))
    return "%s-psql.gz" % dbname

def dbexists(dbname):
    cmd = """psql \
    --username %(user)s \
    --no-password \
    --host %(host)s \
    --port %(port)s \
    --list --quiet --tuples-only --no-align | grep -q '^%(dbname)s|'"""
    kwargs = defaults(dbname)
    return os.system(cmd % kwargs) == 0

def create(dbname):
    cmd = """createdb \
    --username %(user)s \
    --no-password \
    --host %(host)s \
    --port %(port)s \
    %(dbname)s"""
    kwargs = defaults(dbname)
    return os.system(cmd % kwargs) == 0

def drop(dbname):
    cmd = """dropdb \
    --username %(user)s \
    --no-password \
    --host %(host)s \
    --port %(port)s \
    %(dbname)s"""
    kwargs = defaults(dbname)
    return os.system(cmd % kwargs) == 0

def load(dbname, path_to_dump):
    # https://www.postgresql.org/docs/8.1/static/backup.html#BACKUP-DUMP-RESTORE
    ensure(os.path.exists(path_to_dump), "no such path: %r" % path_to_dump)
    cmd = """cat %(path_to_dump)s | gunzip | psql \
    --username %(user)s \
    --no-password \
    --host %(host)s \
    --port %(port)s \
    --dbname %(dbname)s"""
    kwargs = defaults(dbname)
    kwargs.update({
        'path_to_dump': path_to_dump
    })
    return utils.system(cmd % kwargs) == 0
    

#
#
#

def _backup(dbname, destination):
    output_path = join(destination, backup_name(dbname))
    kwargs = defaults(dbname)
    kwargs.update({
        'output_path': output_path
    })

    # '--clean' and '--if-exists' and '--create' deliberately excluded
    # these are good for dev environments where the loss of data can be
    # tolerated (or even expected), but shouldn't lead to data loss (except owners)
    # when automated

    cmd = """pg_dump \
    --username %(user)s \
    --no-password \
    --host %(host)s \
    --port %(port)s \
    --no-owner \
    --dbname %(dbname)s | gzip > %(output_path)s""" % kwargs
    return utils.system(cmd) == 0

def backup(path_list, destination=conf.WORKING_DIR):
    if not isinstance(path_list, list):
        path_list = [path_list]
    return [_backup(dbname, destination) for dbname in path_list]
