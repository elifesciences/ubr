from os.path import join
import os, unittest

THIS_DIR = os.path.abspath(os.path.dirname(__file__))


class BaseCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(BaseCase, self).__init__(*args, **kwargs)
        self.maxDiff = 1024
        self.fixture_dir = join(THIS_DIR, "fixtures")
