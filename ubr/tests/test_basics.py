import os, shutil
from ubr import main
from base import BaseCase

"""These examples can be run with:
      ./run-tests.sh
   or:
      python -m unittest discover -s tests/ -p *_test.py
"""

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
            'mysql-database': [
                'mydb1',
                'mydb2.table1',
            ],

            'files': [
                '/opt/thing/logs/',
                '/opt/thing/',
                '/opt/otherthing/reports/*.csv',
            ],

        }
        self.assertEqual(expected, main.load_descriptor(fixture))
