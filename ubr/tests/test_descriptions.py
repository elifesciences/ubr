import os, shutil
from ubr import descriptions
from . import base

class FindDescriptors(base.BaseCase):
    def setUp(self):
        self.expected_output_dir = "/tmp/foo"
        self.known_backup_fixtures = [
            os.path.join(self.fixture_dir, "ubr-backup.yaml"),
            os.path.join(self.fixture_dir, "ubr-2-backup.yaml"),
            os.path.join(self.fixture_dir, "ubr-empty-backup.yaml"),
        ]

    def tearDown(self):
        if os.path.exists(self.expected_output_dir):
            shutil.rmtree(self.expected_output_dir)

    def test_find_no_descriptor(self):
        "a directory with no descriptors in it returns an empty list"
        self.assertEqual([], descriptions.find_descriptors("/tmp/"))

    def test_find_actual_description(self):
        "a directory with descriptors in it returns each one ordered alphabetically"
        found_descriptors = descriptions.find_descriptors(self.fixture_dir)
        for f in self.known_backup_fixtures:
            # all known fixtures should be found
            self.assertTrue(f in found_descriptors)
        # just to be sure, assert both lists are the same size
        self.assertEqual(len(set(found_descriptors)), len(self.known_backup_fixtures))


class LoadDescriptor(base.BaseCase):
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
            "mysql-database": ["mydb1", "mydb2.table1"],
            "files": [
                "/opt/thing/logs/",
                "/opt/thing/",
                "/opt/otherthing/reports/*.csv",
            ],
        }
        self.assertEqual(expected, descriptions.load_descriptor(fixture))

    def test_descriptor_correctness(self):
        descriptor = descriptions.load_descriptor(self.known_backup_fixtures[0])
        self.assertEqual(descriptor, descriptions.validate_descriptor(descriptor))

    def test_descriptor_invalid(self):
        bad_descriptors = [
            {"foo": "bar"},  # target items must be a list
            {"foo": ["baz", "bar"]},  # unknown target 'foo'
        ]
        for bad_descriptor in bad_descriptors:
            self.assertRaises(
                AssertionError, descriptions.validate_descriptor, bad_descriptor
            )

def test_descriptior__empty():
    expected = {}
    assert descriptions.load_descriptor(base.fixture("ubr-empty-backup.yaml")) == expected
            

def test_many_subdesc():
    "passing multiple paths gives us the appropriately pruned description"
    desc = {
        "mysql-databases": ["mdb1", "mdb2", "mdb3"],
        "files": ["/etc/foo/", "/var/bar/", "/bin/baz/"],
    }
    given = ["mysql-databases.mdb3", "mysql-databases.mdb2", "files./var/bar/"]
    expected = {"mysql-databases": ["mdb3", "mdb2"], "files": ["/var/bar/"]}
    assert descriptions.subdescriptor(desc, given) == expected


def test_subdesc():
    desc = {"mysql-databases": ["mdb1", "mdb2", "mdb3"]}
    given = "mysql-databases.mdb2"
    expected = {"mysql-databases": ["mdb2"]}
    assert descriptions._subdesc(desc, given) == expected


def test_subdesc__no_match():
    desc = {"mysql-databases": ["mdb1", "mdb2", "mdb3"]}
    given = "foo.bar"
    expected = {}
    assert descriptions._subdesc(desc, given) == expected


def test_subdesc__no_desc():
    desc = {}
    given = "foo.bar"
    expected = {}
    assert descriptions._subdesc(desc, given) == expected
