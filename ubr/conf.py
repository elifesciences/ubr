import logging
from pythonjsonlogger import jsonlogger
#from ubr import utils # DONT!
        
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
import boto3
boto3.set_stream_logger('', logging.CRITICAL)

BUCKET = 'elife-app-backups'
CONFIG_DIR = '/etc/ubr/'

RESTORE_DIR = '/tmp/ubr/' # which dir to download files to and restore from

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

mkdir_p(RESTORE_DIR)
