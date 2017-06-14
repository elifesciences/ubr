from ubr import conf, utils
from ubr.utils import ensure
import os, copy
from os.path import join
from ubr.conf import logging
import pg8000

LOG = logging.getLogger(__name__)

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

def create_if_not_exists(dbname):
    if not dbexists(dbname):
        return create(dbname)
    return True

def drop_if_exists(dbname):
    if dbexists(dbname):
        return drop(dbname)
    return True

#
#
#

def pg8k_conn(dbname, **overrides):
    # http://pythonhosted.org/pg8000/dbapi.html#pg8000.paramstyle
    pg8000.paramstyle = 'pyformat' # Python format codes, eg. WHERE name=%(paramname)s
    pg8000.autocommit = True # not working ..?
    kwargs = defaults(dbname, **overrides)

    # argh! pg8k doesn't support the effing .pgpass file.
    # reason enough to swap it out when I have the time

    # https://github.com/gmr/pgpasslib/blob/master/pgpasslib.py#L46
    import pgpasslib
    password = pgpasslib.getpass(**kwargs)
    if not password:
        raise ValueError('Did not find a password in the .pgpass file')

    kwargs = utils.rename_keys(kwargs, [('dbname', 'database')])
    kwargs['password'] = password
    return pg8000.connect(**kwargs)

# kajuberdut, https://github.com/mfenniak/pg8000/issues/112
def _dictfetchall(cursor):
    "lazily returns query results as list of dictionaries."
    cols = [a[0].decode("utf-8") for a in cursor.description]
    for row in cursor.fetchall():
        yield {a: b for a, b in zip(cols, row)}

def runsql(dbname, sql, params=None):
    params = params or {}
    conn = pg8k_conn(dbname)
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit() # autocommit is on, I shouldn't need this
        return _dictfetchall(cursor)
    except pg8000.ProgrammingError as err:
        msg = err.args[3]
        if msg.startswith('database "') and msg.endswith('" does not exist'):
            # raise a better exception
            raise pg8000.DatabaseError("no such database %r" % dbname)

        raise

    finally:
        conn.close()

def dump(dbname, output_path):
    kwargs = defaults(dbname)
    kwargs.update({
        'output_path': output_path
    })

    # '--clean' and '--if-exists' and '--create' deliberately excluded
    # these are good for dev environments where the loss of data can be
    # tolerated (or even expected), but shouldn't lead to data loss (except owners)
    # when automated

    cmd = """
    set -o pipefail
    pg_dump \
    --username %(user)s \
    --no-password \
    --host %(host)s \
    --port %(port)s \
    --no-owner \
    --dbname %(dbname)s | gzip > %(output_path)s""" % kwargs
    return utils.system(cmd) == 0

#
#
#

def _backup(dbname, destination):
    "thin wrapper around `dump()` to raise hell if db failed to backup"
    output_path = join(destination, backup_name(dbname))
    ensure(dump(dbname, output_path), "postgresql database %r backup failed" % dbname)
    return output_path

def backup(path_list, destination=None):
    destination = destination or conf.WORKING_DIR
    destination = os.path.abspath(destination)
    utils.system("mkdir -p %s" % destination)
    if not isinstance(path_list, list):
        path_list = [path_list]
    return {
        'output_dir': destination,
        'output': [_backup(dbname, destination) for dbname in path_list if dbexists(dbname)]
    }

def backup_missing_prompt_user(dbname, dump_path):
    "in cases where we can't find the file to backup, there may be another file we can restore from that has been downloaded. prompt the user for the file"
    backup_dir = os.path.dirname(dump_path)
    other_files = os.listdir(backup_dir)
    if not other_files:
        # nothing else can be restored, return what we were given
        return dump_path
    # opportunity!
    other_files = map(lambda fname: join(backup_dir, fname), other_files) # full paths
    print "expected file missing: %s" % dump_path
    print "other files are available to restore over %s" % dbname
    return utils.choose('choose: ', other_files, os.path.basename)

def _restore(dbname, backup_dir, prompt=False):
    "look for a backup of $dbname in $backup_dir and restore it"
    try:
        backup_dir = backup_dir or conf.WORKING_DIR
        dump_path = join(backup_dir, backup_name(dbname))
        if prompt and not os.path.exists(dump_path):
            dump_path = backup_missing_prompt_user(dbname, dump_path)
        ensure(os.path.exists(dump_path), "expected path %r does not exist or is not a file." % dump_path)
        return (dbname, all([drop_if_exists(dbname), create(dbname), load(dbname, dump_path)]))
    except Exception:
        LOG.exception("unhandled unexception attempting to restore database %r", dbname)
        # raise # this is what we should be doing
        return (dbname, False)

def restore(path_list, backup_dir, prompt=False):
    return {
        'output': [_restore(db, backup_dir, prompt) for db in path_list]
    }
