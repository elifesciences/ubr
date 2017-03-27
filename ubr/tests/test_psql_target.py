import os
from os.path import join
from base import BaseCase
from ubr import psql_target as psql, conf

class One(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_backup_name(self):
        cases = [
            (123, '123-psql.gz'),
            ('foo', 'foo-psql.gz'),
        ]
        for given, expected in cases:
            actual = psql.backup_name(given)
            self.assertEqual(actual, expected, "given %r I got %r but was expecting %r" % (given, actual, expected))

    def test_bad_backup_names(self):
        cases = [
            "", None, [], {},
        ]
        for given in cases:
            self.assertRaises(ValueError, psql.backup_name, given)


class Two(BaseCase):
    def setUp(self):
        self.dbname = '_ubr_testdb'
        fixture = join(self.fixture_dir, 'psql_ubr_testdb.psql.gz')
        # fixture has drop+create statements
        psql.load(self.dbname, fixture)
        self.assertTrue(psql.dbexists(self.dbname))

    def test_backup(self):
        psql.backup(self.dbname)
        expected_path = join(conf.WORKING_DIR, self.dbname + "-psql.gz")
        self.assertTrue(os.path.exists(expected_path))
