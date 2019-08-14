import os, shutil
from .base import BaseCase
from ubr import descriptions as descr

class FindDescriptors(BaseCase):
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
        self.assertEqual([], descr.find_descriptors("/tmp/"))

    def test_find_actual_description(self):
        "a directory with descriptors in it returns each one ordered alphabetically"
        found_descriptors = descr.find_descriptors(self.fixture_dir)
        for f in self.known_backup_fixtures:
            # all known fixtures should be found
            self.assertTrue(f in found_descriptors)
        # just to be sure, assert both lists are the same size
        self.assertEqual(len(set(found_descriptors)), len(self.known_backup_fixtures))

class LoadDescriptor(BaseCase):
    def setUp(self):
        self.known_backup_fixtures = [
            os.path.join(self.fixture_dir, "ubr-backup.yaml"),
            os.path.join(self.fixture_dir, "ubr-2-backup.yaml"),
        ]

    def tearDown(self):
        pass

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
        self.assertEqual(expected, descr.load_descriptor(fixture))

    def test_descriptor_correctness(self):
        descriptor = descr.load_descriptor(self.known_backup_fixtures[0])
        self.assertEqual(descriptor, descr.validate_descriptor(descriptor))

    def test_descriptor_invalid(self):
        bad_descriptors = [
            {'foo': 'bar'}, # target items must be a list
            {'foo': ['baz', 'bar']}, # unknown target 'foo'
        ]
        for bad_descriptor in bad_descriptors:
            self.assertRaises(AssertionError, descr.validate_descriptor, bad_descriptor)

    def test_subdesc(self):
        desc = {
            'mysql-databases': [
                'mdb1',
                'mdb2',
                'mdb3'
            ]
        }
        given = 'mysql-databases.mdb2'
        expected = {
            'mysql-databases': [
                'mdb2'
            ]
        }
        self.assertEqual(expected, descr._subdesc(desc, given))

    def test_many_subdesc(self):
        "passing multiple paths gives us the appropriately pruned description"
        desc = {
            'mysql-databases': [
                'mdb1',
                'mdb2',
                'mdb3'
            ],
            'files': [
                '/etc/foo/',
                '/var/bar/',
                '/bin/baz/'
            ]
        }
        given = ['mysql-databases.mdb3', 'mysql-databases.mdb2', 'files./var/bar/']
        expected = {
            'mysql-databases': [
                'mdb3',
                'mdb2',
            ],
            'files': [
                '/var/bar/'
            ]
        }
        self.assertEqual(expected, descr.subdescriptor(desc, given))
