import os
from base import BaseCase
from ubr import descriptions as descr

class Descriptor(BaseCase):
    def setUp(self):
        self.known_backup_fixtures = [
            os.path.join(self.fixture_dir, "ubr-backup.yaml"),
            os.path.join(self.fixture_dir, "ubr-2-backup.yaml"),
        ]

    def tearDown(self):
        pass

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
