import os, configparser
from os.path import join
import logging
from pythonjsonlogger import jsonlogger

# from ubr import utils # DONT!


def envvar(nom, default):
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
loggers = ["boto3", "botocore", "s3transfer"]
[logging.getLogger(nom).setLevel(logging.ERROR) for nom in loggers]

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


PROJECT_DIR = os.getcwd()  # "/path/to/ubr/"

CFG_NAME = envvar("UBR_CFG_FILE", "app.cfg")
DYNCONFIG = configparser.ConfigParser(
    **{
        "allow_no_value": True,
        # these can be used like template variables
        # https://docs.python.org/2/library/configparser.html
        "defaults": {"dir": PROJECT_DIR},
    }
)
DYNCONFIG.read(join(PROJECT_DIR, CFG_NAME))  # "/path/to/ubr/app.cfg"


def cfg(path, default=0xDEADBEEF):
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


def var(envname, cfgpath, default):
    return envvar(envname, None) or cfg(cfgpath, None) or default


#
# config
#


# which S3 bucket should ubr upload backups to/restore backups from?
BUCKET = "elife-app-backups"

# where should ubr look for backup descriptions?
DESCRIPTOR_DIR = cfg("general.descriptor_dir", "/etc/ubr/")

# where should ubr do it's work? /tmp/ubr/ by default
WORKING_DIR = join(
    var("UBR_WORKING_DIR", "general.working_dir", "/tmp"), "ubr"
)  # "/tmp/ubr", "/ext/tmp/ubr"

mkdir_p(WORKING_DIR)

# we used to pick these up from wherever boto could find them
# now a machine may have several sets of credentials for different tasks
# so we're explicit about which ones we're using.

AWS = {
    "aws_access_key_id": cfg("aws.access_key_id"),
    "aws_secret_access_key": cfg("aws.secret_access_key"),
}

MYSQL = {
    "user": cfg("mysql.user"),
    "pass": cfg("mysql.pass"),
    "host": cfg("mysql.host", "localhost"),
    "port": int(
        cfg("mysql.port", 3306)
    ),  # pymysql absolutely cannot handle a stringified port
}

POSTGRESQL = {
    "user": cfg("postgresql.user"),
    # you can't use passwords in cli connections to postgresql. it's also not good practice.
    # ubr relies on a ~/.pgpass file existing:
    # https://www.postgresql.org/docs/9.2/static/libpq-pgpass.html
    # 'pass':
    "host": cfg("postgresql.host", "localhost"),
    "port": int(cfg("postgresql.port", 5432)),
}

# ignore these specific projects when reporting
# (projects with an "_" prefix are automatically ignored
REPORT_PROJECT_BLACKLIST = ["civicrm"]

# ignore these specific files when reporting
REPORT_FILE_BLACKLIST = [
    "archive-d162efcb.tar.gz",  # elife-metrics, old-style backup
    "archive-b40e0f85.tar.gz",  # journal-cms, old-style backup
    "elifedashboardprod-psql.gz",  # elife-dashboard, old-style backup
]

# number of days between now and the last backup before it's considered a problem
REPORT_PROBLEM_THRESHOLD = 2 # days
