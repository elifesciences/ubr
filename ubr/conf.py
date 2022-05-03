import pathlib
import tempfile
import os, configparser
import logging
from pythonjsonlogger import jsonlogger

# from ubr import utils # DONT!


def _envvar(nom, default):
    return os.environ.get(nom) or default


#
# logging
#

ROOTLOG = logging.getLogger("")
_supported_keys = [
    # 'asctime',
    # 'created',
    "filename",
    "funcName",
    "levelname",
    # 'levelno',
    "lineno",
    "module",
    "msecs",
    "message",
    "name",
    "pathname",
    # 'process',
    # 'processName',
    # 'relativeCreated',
    # 'thread',
    # 'threadName'
]
# optional json logging if you need it
_log_format = ["%({0:s})".format(i) for i in _supported_keys]
_log_format = " ".join(_log_format)
_formatter = jsonlogger.JsonFormatter(_log_format)

# output to stderr
_handler = logging.StreamHandler()
_handler.setLevel(logging.INFO)
_handler.setFormatter(logging.Formatter("%(levelname)s - %(asctime)s - %(message)s"))

_filehandler = logging.FileHandler("ubr.log")
_filehandler.setFormatter(_formatter)
_filehandler.setLevel(logging.INFO)

ROOTLOG.addHandler(_handler)
ROOTLOG.addHandler(_filehandler)
ROOTLOG.setLevel(logging.DEBUG)

# tell boto to pipe down
_loggers = ["boto3", "botocore", "s3transfer"]
[logging.getLogger(nom).setLevel(logging.ERROR) for nom in _loggers]

#
# utils
#


def _mkdir_p(path):
    try:
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    except Exception as err:
        ROOTLOG.error("problem attempting to create path %s: %s", path, err)


#
# config parsing
#


PROJECT_DIR = os.getcwd()  # "/path/to/ubr/"

CFG_NAME = _envvar("UBR_CFG_FILE", "app.cfg")
DYNCONFIG = configparser.ConfigParser(
    **{
        "allow_no_value": True,
        # these can be used like template variables
        # https://docs.python.org/2/library/configparser.html
        "defaults": {"dir": PROJECT_DIR},
    }
)
DYNCONFIG.read(os.path.join(PROJECT_DIR, CFG_NAME))  # "/path/to/ubr/app.cfg"


def _cfg(path, default=0xDEADBEEF):
    lu = {
        "True": True,
        "true": True,
        "False": False,
        "false": False,
    }  # cast any obvious booleans
    try:
        val = DYNCONFIG.get(*path.split("."))
        return lu.get(val, val)
    except (
        configparser.NoOptionError,
        configparser.NoSectionError,
    ):  # given key in section hasn't been defined
        if default == 0xDEADBEEF:
            raise ValueError("no value/section set for setting at %r" % path)
        return default
    except Exception:
        raise


def _var(envname, cfgpath, default):
    return _envvar(envname, None) or _cfg(cfgpath, None) or default


#
# config
#

# CLI argument parsing uses the values in this map as defaults
# tests and other non-standard entry points should use the values in
# this map if parsed CLI arguments are not available
DEFAULT_CLI_OPTS = {}

# which S3 bucket should ubr upload backups to/restore backups from?
BUCKET = "elife-app-backups"

# where should ubr look for backup descriptions?
DESCRIPTOR_DIR = _var("UBR_DESCRIPTOR_DIR", "general.descriptor_dir", "/etc/ubr")

# where should ubr do it's work? /tmp/ubr/ by default
# "/tmp/ubr", "/ext/tmp/ubr"
WORKING_DIR = os.path.join(
    _var("UBR_WORKING_DIR", "general.working_dir", tempfile.gettempdir()), "ubr"
)
_mkdir_p(WORKING_DIR)

# always be explicit about which AWS credentials to use,
# otherwise boto will go looking for them on the fs, in envvars, etc,
# possibly finding an incorrect set during testing.

AWS = {
    "aws_access_key_id": _cfg("aws.access_key_id"),
    "aws_secret_access_key": _cfg("aws.secret_access_key"),
    "region_name": "us-east-1",
}

MYSQL = {
    "user": _cfg("mysql.user"),
    "pass": _cfg("mysql.pass"),
    "host": _cfg("mysql.host", "localhost"),
    # pymysql cannot handle a stringified port
    "port": int(_cfg("mysql.port", 3306)),
}

POSTGRESQL = {
    "user": _cfg("postgresql.user"),
    # you can't use passwords in cli connections to postgresql. it's also not good practice.
    # ubr relies on a ~/.pgpass file existing:
    # https://www.postgresql.org/docs/9.2/static/libpq-pgpass.html
    # 'pass':
    "host": _cfg("postgresql.host", "localhost"),
    "port": int(_cfg("postgresql.port", 5432)),
}

# ignore these specific projects when reporting
# (projects with an "_" prefix are automatically ignored
REPORT_PROJECT_BLACKLIST = ["civicrm"]

# ignore these specific files when reporting
REPORT_FILE_BLACKLIST = [
    "archive-d162efcb.tar.gz",  # elife-metrics, old-style backup
    "archive-b40e0f85.tar.gz",  # journal-cms, old-style backup
    "elifedashboardprod-psql.gz",  # elife-dashboard, old-style backup
    "articlescheduler-psql.gz",  # elife-dashboard/article-scheduler, once-off/ad-hoc article-scheduler backup
    "archive-59001402.tar.gz",  # peerscout, adhoc files backup
    "peerscoutprod-psql.gz",  # peerscout, adhoc database upload
]

# number of days between now and the last backup before it's considered a problem
REPORT_PROBLEM_THRESHOLD = 2  # days

KNOWN_TARGETS = [
    "files",
    "tar-gzipped",
    "mysql-database",
    "postgresql-database",
    "rds-snapshot",
]
