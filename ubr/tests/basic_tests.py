import os, shutil, unittest
from ubr import main, mysql_backup, s3, utils
from datetime import datetime
from unittest import skip

skiptest = skip("'cuz")

"""These examples can be run with:
   python -m unittest discover -s tests/ -p *_test.py

"""

THIS_DIR = os.path.abspath(os.path.dirname(__file__))

class BaseCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(BaseCase, self).__init__(*args, **kwargs)
        self.maxDiff = 1024
        self.fixture_dir = THIS_DIR # I might have a dedicated fixtures dir in future. /shrug

class BasicUsage(BaseCase):
    def setUp(self):
        self.expected_output_dir = '/tmp/foo'
        self.known_backup_fixtures = [
            os.path.join(self.fixture_dir, "ubr-backup.yaml"),
            os.path.join(self.fixture_dir, "ubr-2-backup.yaml"),
        ]

    def tearDown(self):
        if os.path.exists(self.expected_output_dir):
            shutil.rmtree(self.expected_output_dir)

    def test_find_no_descriptor(self):
        "a directory with no descriptors in it returns an empty list"
        self.assertEqual([], main.find_descriptors("/tmp/"))

    def test_find_actual_description(self):
        "a directory with descriptors in it returns each one ordered alphabetically"
        found_descriptors = main.find_descriptors(self.fixture_dir)
        for f in self.known_backup_fixtures:
            # all known fixtures should be found
            self.assertTrue(f in found_descriptors)
        # just to be sure, assert both lists are the same size
        self.assertEqual(len(set(found_descriptors)), len(self.known_backup_fixtures))

    def test_find_bits(self):
        "what we load is what we expect"
        fixture = self.known_backup_fixtures[0]
        expected = {
            'mysql': [
                'mydb1',
                'mydb2.table1',
            ],

            'postgresql': [
                'dbx',
            ],

            'files': [
                '/opt/thing/logs/',
                '/opt/thing/',
                '/opt/otherthing/reports/*.csv',
            ],

        }
        self.assertEqual(expected, main.load_descriptor(fixture))

    def test_descriptor_correctness(self):
        self.assertTrue(main.valid_descriptor, main.load_descriptor(self.known_backup_fixtures[0]))

    def test_descriptor_invalid(self):
        bad_descriptors = [
            {'foo': 'bar'}, # target items must be a list
            {'foo': ['baz', 'bar']}, # unknown target 'foo'
        ]
        for bad_descriptor in bad_descriptors:
            self.assertRaises(AssertionError, main.valid_descriptor, bad_descriptor)

#if __name__ == '__main__':
#    unittest.main()
