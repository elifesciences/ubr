import os, shutil, unittest
from ubr import main, mysql_backup, s3, utils
from datetime import datetime
from unittest import skip

from basic_tests import BaseCase

class TestFileBackup(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        os.system('rm -rf %s' % self.expected_output_dir)


    def test_backup_single_file(self):
        "a simple descriptor of individual file backups can be run"
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        descriptor = {'files': [fixture]}
        
        expected_output = {
            'files': {'output_dir': self.expected_output_dir,
                      'dir_prefix': self.fixture_dir,
                      # common directory prefixes are stripped
                      'output': [os.path.join(self.expected_output_dir, 'img1.png')]}
        }

        output = main.backup(descriptor, output_dir=self.expected_output_dir)
        self.assertEqual(expected_output, output)
        self.assertTrue(utils.dir_exists(self.expected_output_dir))
        self.assertTrue(os.path.exists(os.path.join(self.expected_output_dir, 'img1.png')))

    def test_backup_multiple_file(self):
        "a simple descriptor of individual file backups can be run"
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        fixture2 = os.path.join(self.fixture_dir, 'img2.jpg')
        descriptor = {'files': [fixture, fixture2]}
        
        expected_output = {
            'files': {'output_dir': self.expected_output_dir,
                      'dir_prefix': self.fixture_dir,
                      # common directory prefixes are stripped
                      'output': [os.path.join(self.expected_output_dir, 'img1.png'),
                                  os.path.join(self.expected_output_dir, 'img2.jpg')]}
        }

        output = main.backup(descriptor, output_dir=self.expected_output_dir)
        self.assertEqual(expected_output, output)

    def test_backup_multiple_dispersed_files(self):
        "a simple descriptor of individual files in different directories can be run"
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        fixture2 = os.path.join(self.fixture_dir, 'img2.jpg')
        fixture3 = os.path.join(self.fixture_dir, "subdir", 'img3.jpg')
        
        descriptor = {'files': [fixture, fixture2, fixture3]}
        
        expected_output = {
            'files': {'output_dir': self.expected_output_dir,
                      'dir_prefix': self.fixture_dir,
                      # common directory prefixes are stripped
                      'output': [os.path.join(self.expected_output_dir, 'img1.png'),
                                  os.path.join(self.expected_output_dir, 'img2.jpg'),
                                  os.path.join(self.expected_output_dir, 'subdir', 'img3.jpg'),
                                  ]
                    }
        }
        output = main.backup(descriptor, output_dir=self.expected_output_dir)
        self.assertEqual(expected_output, output)
        self.assertTrue(os.path.exists(os.path.join(self.expected_output_dir, 'subdir', 'img3.jpg')))

    def test_backup_globbed_files(self):
        "a descriptor of individual files with glob syntax can be run"
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        fixture2 = os.path.join(self.fixture_dir, 'img2.jpg')
        fixture3 = os.path.join(self.fixture_dir, "subdir", 'img3.jpg')
        fixture4 = os.path.join(self.fixture_dir, "subdir", 'subdir2', 'img4.jpg')
        
        descriptor = {'files': [fixture,
                                fixture2,
                                os.path.join(self.fixture_dir, '*/**')]}

        expected_output = {
            'files': {'output_dir': self.expected_output_dir,
                      'dir_prefix': self.fixture_dir,
                      # common directory prefixes are stripped
                      'output': [os.path.join(self.expected_output_dir, 'img1.png'),
                                  os.path.join(self.expected_output_dir, 'img2.jpg'),
                                  os.path.join(self.expected_output_dir, 'subdir', 'img3.jpg'),
                                  os.path.join(self.expected_output_dir, 'subdir', 'subdir2', 'img4.jpg'),
                                  ]
                    }
        }
        output = main.backup(descriptor, output_dir=self.expected_output_dir)

        self.assertEqual(expected_output, output)
        self.assertTrue(os.path.exists(os.path.join(self.expected_output_dir, 'subdir', 'img3.jpg')))

    def test_unknown_backup(self):
        "an unknown target is reported"
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        # a /dev/null backup is valid, right? restore process sucks though ...
        descriptor = {'dev-null': [fixture]}

    def test_backup_to_dynamic_output_dir(self):
        "we're writing our output to a known output_dir for these tests. what happens when we try to output to a dir that doesn't exist?"
        pass

    def test_backup_of_bad_file(self):
        "what happens when the dir/file we specify in the descriptor doesn't exist"
        pass

    def test_backup_of_no_files(self):
        "what happens when the path we specify in the descriptor doesn't yield any files?"
        pass



class TestFileRestore(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_file_restore(self):
        
        pass
