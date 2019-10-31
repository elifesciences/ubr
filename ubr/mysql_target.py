import os, copy
from ubr import utils, conf
from ubr.utils import ensure
import pymysql.cursors
import logging

LOG = logging.getLogger(__name__)


def defaults(db=None, **overrides):
    "default mysql args"
    args = copy.deepcopy(conf.MYSQL)
    args["dbname"] = db
    args.update(overrides)
    ensure(args["user"], "a database username *must* be specified")
    return args


def _pymysql_conn(db=None):
    "returns a database connection to the given db"
    config = defaults(
        db, **{"charset": "utf8mb4", "cursorclass": pymysql.cursors.DictCursor}
    )
    # pymysql-specific wrangling
    config = utils.rename_keys(config, [("dbname", "db"), ("pass", "password")])
    # while you can connect to mysqld via mysql fine with the above config, you can't via pymysql.
    # both mysql and pymysql are doing stupid magic tricks behind the scenes when 'localhost' or
    # '127.0.0.1' are encountered.
    if config["host"] in ["localhost", "127.0.0.1"]:
        config["unix_socket"] = "/var/run/mysqld/mysqld.sock"
    LOG.debug("connecting with: %r", config)
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
    return (
        result is not None and "SCHEMA_NAME" in result and result["SCHEMA_NAME"] == db
    )


def mysql_cli_cmd(mysqlcmd, **kwargs):
    "runs very simple commands from the command line against mysql. doesn't handle quoting at all. totally insecure."
    args = defaults(mysqlcmd=mysqlcmd, **kwargs)
    cmd = (
        """mysql \
    -u %(user)s \
    -p%(pass)s \
    -h %(host)s \
    -P %(port)s \
    -e '%(mysqlcmd)s'"""
        % args
    )
    return utils.system(cmd)


def drop(db, **kwargs):
    return 0 == mysql_cli_cmd("drop database if exists %s;" % db, **kwargs)


def create(db, **kwargs):
    return 0 == mysql_cli_cmd("create database if not exists %s;" % db, **kwargs)


def load(db, dump_path, dropdb=False, **kwargs):
    LOG.debug("loading dump %r into db %r (dropdb=%s)", dump_path, db, dropdb)
    args = defaults(db, path=dump_path, **kwargs)
    # TODO: consider dropping this convenience function
    if dropdb:
        # reset the database before loading the fixture
        msg = "failed to drop+create the database prior to loading fixture."
        ensure(
            all(
                [
                    drop(db, **kwargs),
                    not dbexists(db),
                    create(db, **kwargs),
                    dbexists(db),
                ]
            ),
            msg,
        )
        LOG.debug("passed assertion check!")

    cmd = (
        """mysql \
    -u %(user)s \
    -p%(pass)s \
    -h %(host)s \
    -P %(port)s \
    %(dbname)s < %(path)s"""
        % args
    )

    if dump_path.endswith(".gz"):
        LOG.debug("dealing with a gzipped file")
        cmd = (
            """zcat %(path)s | mysql \
        -u %(user)s \
        -p%(pass)s \
        -h %(host)s \
        -P %(port)s \
        %(dbname)s"""
            % args
        )

    return utils.system(cmd) == 0


def backup_name(db):
    "generates a filename for the given db"
    return (
        db + "-mysql.gz"
    )  # looks like: ELIFECIVICRM-mysql.gz  or  /foo/bar/db-mysql.gz


def dump(db, output_path, **kwargs):
    output_path = backup_name(output_path)
    args = defaults(db, path=output_path, **kwargs)
    # --skip-dump-date # suppresses the 'Dump completed on <YMD HMS>'
    # at the bottom of each dump file, defeating duplicate checking
    
    # THEORY
    #
    # The MySQL server binary log) contains all events that describe database changes.
    # https://dev.mysql.com/doc/refman/5.7/en/binary-log.html
    # The binary log can be used for:
    # - replication of data to MySQL slaves. We do this in `prod` environments.
    # - for point-in-time backup restores where some events from the log are applied to an old backup to make it reach time X. We don't do this at the moment.
    #
    # Global Transaction IDs are identifiers that can be assigned to write transactions on a MySQL master node:
    # https://dev.mysql.com/doc/refman/5.7/en/replication-gtids.html
    # MySQL slaves nodes can keep a record of the GTIDs that have been applied to their copy of the data.
    #
    # VARIABLES
    #
    # `gtid_purged` is a system variable that contains GTIDs that have been committed, but do not exist in the binary log (anymore, for example because the binary log has been _purged_ aka rotated).
    # A dump doesn't contain only data then, but may also contain information about the GTIDs.
    #
    # DUMP GENERATION
    # `--set-gtid-purged=OFF` does not write GTID-related information to the dump:
    # https://dev.mysql.com/doc/refman/5.7/en/mysqldump.html#option_mysqldump_set-gtid-purged
    # This means:
    # - No `SET @@GLOBAL.gtid_purged` statement in the dump
    # - No `@@SESSION.SQL_LOG_BIN=0` statement to disable the binary log while the dump is being reloaded
    #
    # AWS RDS CONTEXT
    #
    # These properties are problematic because (at least the latter) require `SUPER` privileges, which we don't have on RDS, being a managed server where we don't have access to a root user.
    # RDS is configured with replication in `prod` environments:
    # https://aws.amazon.com/rds/details/multi-az/
    # However, GTIDs are disabled in the `default.mysql57` parameter group that we are consistently using:
    # https://console.aws.amazon.com/rds/home?region=us-east-1#parameter-groups-detail:ids=default.mysql5.7;type=DbParameterGroup;editing=false
    # Moreover, when we are restoring we are not even interested in GTIDs as we are dropping the database first.
    # If GTIDs were enables, and we were to restore a slave node to bring it on par with master, we could use them. Unlikely use case as replication is always managed by RDS.
    cmd = (
        """set -o pipefail
    mysqldump \
    -u %(user)s \
    -h %(host)s \
    -P %(port)s \
    -p%(pass)s \
    --single-transaction \
    --skip-dump-date \
    --set-gtid-purged=OFF \
    %(dbname)s | gzip > %(path)s"""
        % args
    )
    retval = utils.system(cmd)
    if not retval == 0:
        # not the best error to be throwing. perhaps a CommandError ?
        raise OSError("bad dump. got return value %s" % retval)
    return output_path


#
#
#


def _backup(path, destination):
    """'path' in MySQL's case is either 'dbname' or 'dbname.table'
    'destination' is the directory to store the output"""
    # looks like: /tmp/foo/test.gzip or /tmp/foo/test.table1.gzip
    output_path = os.path.join(destination, path)
    LOG.info("backing up MySQL database %r" % path)
    return dump(path, output_path)


def backup(path_list, destination, prompt=False):
    "dumps a list of databases and database tables"
    retval = utils.system("mkdir -p %s" % destination)
    if not retval == 0:
        # check to see if our intention is there
        ensure(
            os.path.isdir(destination),
            "given destination %r is not a directory or doesn't exist!" % destination,
        )
    return {
        "output_dir": destination,
        "output": [_backup(p, destination) for p in path_list],
    }


def _restore(db, backup_dir):
    try:
        dump_path = os.path.join(backup_dir, backup_name(db))
        ensure(
            os.path.isfile(dump_path),
            "expected path %r does not exist or is not a file." % dump_path,
        )
        LOG.info("restoring MySQL database %r" % db)
        return (db, load(db, dump_path, dropdb=True))
    except Exception:
        LOG.exception("unhandled unexception attempting to restore database %r", db)
        # raise # this is what we should be doing
        return (db, False)


def restore(db_list, backup_dir, prompt=False):
    return {"output": [_restore(db, backup_dir) for db in db_list]}
