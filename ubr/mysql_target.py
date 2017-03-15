import os, copy
from ubr import utils, conf
from ubr.utils import ensure
import pymysql.cursors
import logging

LOG = logging.getLogger(__name__)

def defaults(db=None, **overrides):
    "default mysql args"
    args = copy.deepcopy(conf.MYSQL)
    args['dbname'] = db
    args.update(overrides)
    ensure(args['user'], "a database username *must* be specified")
    return args

def _pymysql_conn(db=None):
    "returns a database connection to the given db"
    config = defaults(db, **{
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    })
    # pymysql-specific wrangling
    config = utils.rename_keys(config, [('dbname', 'db'), ('pass', 'password')])
    return pymysql.connect(**config)

def mysql_query(db, sql, args=()):
    conn = _pymysql_conn(db)
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
        conn.commit()
        return cursor
    finally:
        conn.close()

def fetchall(db, sql, args=()):
    cursor = mysql_query(db, sql, args)
    return cursor.fetchall()

def fetchone(db, sql, args=()):
    cursor = mysql_query(db, sql, args)
    return cursor.fetchone()

def dbexists(db):
    "returns True if the given database exists"
    sql = "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s"
    args = [db]
    cursor = mysql_query(None, sql, args)
    result = cursor.fetchone()
    return result != None and result.has_key('SCHEMA_NAME') and result['SCHEMA_NAME'] == db

def mysql_cli_cmd(mysqlcmd, **kwargs):
    "runs very simple commands from the command line against mysql. doesn't handle quoting at all. totally insecure."
    args = defaults(mysqlcmd=mysqlcmd, **kwargs)
    cmd ="mysql -u %(user)s -p%(pass)s -h %(host)s -P %(port)s -e '%(mysqlcmd)s'" % args
    return utils.system(cmd)

def drop(db, **kwargs):
    return 0 == mysql_cli_cmd('drop database if exists %s;' % db, **kwargs)

def create(db, **kwargs):
    return 0 == mysql_cli_cmd('create database if not exists %s;' % db, **kwargs)

def load(db, dump_path, dropdb=False, **kwargs):
    LOG.info("loading dump %r into db %r. dropdb=%s", dump_path, db, dropdb)
    args = defaults(db, path=dump_path, **kwargs)
    if dropdb:
        # reset the database before loading the fixture
        msg = "failed to drop+create the database prior to loading fixture."
        assert all([drop(db, **kwargs), \
                    not dbexists(db), \
                    create(db, **kwargs), \
                    dbexists(db)]), msg
        LOG.info("passed assertion check!")
    cmd = "mysql -u %(user)s -p%(pass)s -h %(host)s -P %(port)s %(dbname)s < %(path)s" % args
    if dump_path.endswith('.gz'):
        LOG.info("dealing with a gzipped file")
        cmd = "zcat %(path)s | mysql -u %(user)s -p%(pass)s -h %(host)s -P %(port)s --database %(dbname)s" % args
    return 0 == utils.system(cmd)

def dumpname(db):
    "generates a filename for the given db"
    return db + "-mysql.gz" # looks like: ELIFECIVICRM-mysql.gz  or  /foo/bar/db-mysql.gz

def dump(db, output_path, **kwargs):
    output_path = dumpname(output_path)
    args = defaults(db, path=output_path, **kwargs)
    # --skip-dump-date # suppresses the 'Dump completed on <YMD HMS>'
    # at the bottom of each dump file, defeating duplicate checking
    cmd ="mysqldump -u %(user)s -h %(host)s -P %(port)s -p%(pass)s --databases %(dbname)s --single-transaction --skip-dump-date | gzip > %(path)s" % args
    retval = utils.system(cmd)
    if not retval == 0:
        raise OSError("bad dump. got return value %s" % retval)
    return output_path

def _backup(path, destination):
    "'path' in this case is either 'db' or 'db.table'"
    # looks like: /tmp/foo/test.gzip or /tmp/foo/test.table1.gzip
    output_path = os.path.join(destination, path)
    return dump(path, output_path)

#
#
#

def backup(path_list, destination):
    "dumps a list of databases and database tables"
    retval = utils.system("mkdir -p %s" % destination)
    if not retval == 0:
        # check to see if our intention is there
        assert os.path.isdir(destination), "given destination %r is not a directory or doesn't exist!" % destination
    return {
        'output_dir': destination,
        'output': map(lambda p: _backup(p, destination), path_list)
    }

def _restore(db, backup_dir):
    try:
        dump_path = os.path.join(backup_dir, dumpname(db))
        assert os.path.isfile(dump_path), "expected path %r does not exist or is not a file." % dump_path
        return (db, load(db, dump_path, dropdb=True))
    except Exception:
        LOG.exception("unhandled unexception attempting to restore database %r", db)
        #raise # this is what we should be doing
        return (db, False)

def restore(db_list, backup_dir):
    return {
        'output': map(lambda db: _restore(db, backup_dir), db_list)
    }
