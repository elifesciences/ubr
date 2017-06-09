import os, configparser
from os.path import join
import logging
from pythonjsonlogger import jsonlogger
# from ubr import utils # DONT!

#
# logging
#

ROOTLOG = logging.getLogger("")
_supported_keys = [
    #'asctime',
    #'created',
    'filename',
    'funcName',
    'levelname',
    #'levelno',
    'lineno',
    'module',
    'msecs',
    'message',
    'name',
    'pathname',
    #'process',
    #'processName',
    #'relativeCreated',
    #'thread',
    #'threadName'
]
# optional json logging if you need it
_log_format = ['%({0:s})'.format(i) for i in _supported_keys]
_log_format = ' '.join(_log_format)
_formatter = jsonlogger.JsonFormatter(_log_format)

# output to stderr
_handler = logging.StreamHandler()
_handler.setLevel(logging.DEBUG)
_handler.setFormatter(logging.Formatter('%(levelname)s - %(asctime)s - %(message)s'))

ROOTLOG.addHandler(_handler)
ROOTLOG.setLevel(logging.DEBUG)

# tell boto to pipe down
loggers = ['boto3', 'botocore', 's3transfer']
[logging.getLogger(nom).setLevel(logging.CRITICAL) for nom in loggers]

#
# utils
#

# duplicated from utils
def mkdir_p(path):
    import os, errno
    try:
        os.makedirs(path)
    except OSError as err:
        if err.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            ROOTLOG.error("problem attempting to create path %s: %s", path, err)
            raise

#
# config parsing
#


PROJECT_DIR = os.getcwdu() # ll: /path/to/ubr/

CFG_NAME = 'app.cfg'
DYNCONFIG = configparser.SafeConfigParser(**{
    'allow_no_value': True,
    # these can be used like template variables
    # https://docs.python.org/2/library/configparser.html
    'defaults': {'dir': PROJECT_DIR}})
DYNCONFIG.read(join(PROJECT_DIR, CFG_NAME)) # ll: /path/to/ubr/app.cfg

def cfg(path, default=0xDEADBEEF):
    lu = {'True': True, 'true': True, 'False': False, 'false': False} # cast any obvious booleans
    try:
        val = DYNCONFIG.get(*path.split('.'))
        return lu.get(val, val)
    except (configparser.NoOptionError, configparser.NoSectionError): # given key in section hasn't been defined
        if default == 0xDEADBEEF:
            raise ValueError("no value/section set for setting at %r" % path)
        return default
    except Exception:
        raise

#
# config
#


# which S3 bucket should ubr upload backups to/restore backups from?
BUCKET = 'elife-app-backups'

# where should ubr look for backup descriptions?
DESCRIPTOR_DIR = '/etc/ubr/'

# where should ubr do it's work? /tmp/ubr/ by default
WORKING_DIR = join(cfg('general.working_dir', '/tmp'), 'ubr')

mkdir_p(WORKING_DIR)

# we used to pick these up from wherever boto could find them
# now a machine may have several sets of credentials for different tasks
# so we're explicit about which ones we're using.

AWS = {
    'aws_access_key_id': cfg('aws.access_key_id'),
    'aws_secret_access_key': cfg('aws.secret_access_key'),
}

MYSQL = {
    'user': cfg('mysql.user'),
    'pass': cfg('mysql.pass'),
    'host': cfg('mysql.host', 'localhost'),
    'port': int(cfg('mysql.port', 3306)), # pymysql absolutely cannot handle a stringified port
}

POSTGRESQL = {
    'user': cfg('postgresql.user'),
    # you can't use passwords in cli connections to postgresql. it's also not good practice.
    # ubr relies on a ~/.pgpass file existing:
    # https://www.postgresql.org/docs/9.2/static/libpq-pgpass.html
    #'pass':
    'host': cfg('postgresql.host', 'localhost'),
    'port': int(cfg('postgresql.port', 5432)),
}
