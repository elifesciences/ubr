import os, shutil, unittest
from ubr import main, mysql_backup, s3, utils
from datetime import datetime
from unittest import skip

from basic_tests import BaseCase

class TestTarredGzippedBackup(BaseCase):
    def setUp(self):
        self.expected_output_dir = '/tmp/foo'

    def tearDown(self):
        os.system('rm /tmp/foo/archive.tar.gz')

    def test_simple_tgz(self):
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        descriptor = {'tar-gzipped': [fixture, os.path.join(self.fixture_dir, '*/**')]}
        output = main.backup(descriptor, output_dir=self.expected_output_dir)

        expected_output = {
            'tar-gzipped': {'output_dir': self.expected_output_dir,
                            'dir_prefix': self.fixture_dir,
                            # common directory prefixes are stripped
                            'output': [os.path.join(self.expected_output_dir, 'img1.png'),
                                        os.path.join(self.expected_output_dir, 'img2.jpg'),
                                        os.path.join(self.expected_output_dir, 'subdir', 'img3.jpg'),
                                        os.path.join(self.expected_output_dir, 'subdir', 'subdir2', 'img4.jpg'),
                                        ]
                            }
        }
        
        self.assertTrue(os.path.isfile(os.path.join(self.expected_output_dir, 'archive.tar.gz')))

    def test_tgz_returns_a_list_of_outputs(self):
        "the tgz target returns a list for it's 'output' result. all targets must return a list"
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        descriptor = {'tar-gzipped': [fixture]}
        results = main.backup(descriptor, output_dir=self.expected_output_dir)
        self.assertEqual(1, len(results['tar-gzipped']['output']))

