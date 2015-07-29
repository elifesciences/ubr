import os
from main import env, system

def defaults(db=None, **overrides):
    "default mysql args"
    args = {
        'user': env('MYSQL_USER'),
        'dbname': db,
    }
    args.update(overrides)
    return args

def mysql_cmd(mysqlcmd, **kwargs):
    "runs very simple commands from the command line against mysql. doesn't handle quoting at all."
    args = defaults(mysqlcmd=mysqlcmd, **kwargs)
    cmd ="mysql -u %(user)s -e '%(mysqlcmd)s'" % args
    return system(cmd)

def drop(db, **kwargs):
    return mysql_cmd('drop database if exists %s;' % db, **kwargs)

def create(db, **kwargs):
    return mysql_cmd('create database if not exists %s;' % db, **kwargs)

def load(db, dump_path, dropdb=False, **kwargs):
    args = defaults(db, path=dump_path, **kwargs)
    if dropdb:
        # reset the database before loading the fixture
        assert all([drop(db, **kwargs), create(db, **kwargs)], "failed to drop+create the database prior to loading fixture.")
    #cmd ="MYSQL_PWD=%(passwd)s mysql -u %(user)s %(dbname)s < %(path)s" % args
    cmd ="mysql -u %(user)s %(dbname)s < %(path)s" % args
    return system(cmd)

def dump(db, output_path, **kwargs):
    output_path += "-mysql.gz"
    args = defaults(db, path=output_path, **kwargs)
    # --skip-dump-date # suppresses the 'Dump completed on <YMD HMS>'
    # at the bottom of each dump file, defeating duplicate checks
    cmd ="mysqldump -u %(user)s %(dbname)s --skip-dump-date | gzip > %(path)s" % args
    retval = system(cmd)
    if not retval == 0:
        raise OSError("bad dump. got return value %s" % retval)
    return output_path

def _backup(path, destination):
    "'path' in this case is either 'db' or 'db.table'"
    # looks like: /tmp/foo/_test.gzip or /tmp/foo/_test.table1.gzip
    output_path = os.path.join(destination, path)
    return dump(path, output_path)

def backup(path_list, destination):
    "dumps a list of databases and database tables"
    retval = system("mkdir -p %s" % destination)
    if not retval == 0:
        # check to see if our intention is there
        assert os.path.isdir(destination), "given destination %r is not a directory or doesn't exist!" % destination
    return {
        'output_dir': destination,
        'output': map(lambda p: _backup(p, destination), path_list)
    }
