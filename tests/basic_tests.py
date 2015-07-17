import os, unittest
import main

"""These examples can be run with:
   python -m unittest discover -s tests/ -p *_test.py

"""

THIS_DIR = os.path.abspath(os.path.dirname(__name__))

class BasicUsage(unittest.TestCase):
    def setUp(self):
        self.fixture_dir = os.path.join(THIS_DIR, "tests")
        self.known_backup_fixtures = [
            self.fixture("ubr-backup.yaml"),
            self.fixture("ubr-2-backup.yaml"),
        ]

    def tearDown(self):
        pass

    def fixture(self, fname):
         return os.path.join(self.fixture_dir, fname)

    #
    #
    #

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
        fixture = self.known_backup_fixtures[0]
        expected = {
            'project-name': [
                {'mysql': [
                    'mydb1',
                    'mydb2.table1',
                ]},
                
                {'postgresql': [
                    'dbx',
                ]},
                
                {'files': [
                    '/opt/thing/logs/',
                    '/opt/thing/',
                    '/opt/otherthing/reports/*.csv'
                ]}
            ]
        }
        self.assertEqual(expected, main.load_descriptor(fixture))

if __name__ == '__main__':
    unittest.main()
