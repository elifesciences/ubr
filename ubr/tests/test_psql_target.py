import os, types
import pg8000 as pg8k
from os.path import join
from .base import BaseCase
from ubr import psql_target as psql, conf


class One(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_backup_name(self):
        cases = [(123, "123-psql.gz"), ("foo", "foo-psql.gz")]
        for given, expected in cases:
            actual = psql.backup_name(given)
            self.assertEqual(
                actual,
                expected,
                "given %r I got %r but was expecting %r" % (given, actual, expected),
            )

    def test_bad_backup_names(self):
        "bad backup names fail noisily"
        cases = ["", None, [], {}]
        for given in cases:
            self.assertRaises(ValueError, psql.backup_name, given)


class Two(BaseCase):
    def setUp(self):
        self.db1, self.db2 = "_ubr_testdb", "_pants-party"
        psql.create_if_not_exists(self.db1)
        psql.drop_if_exists(self.db2)

        fixture = join(self.fixture_dir, "psql_ubr_testdb.psql.gz")
        psql.load(self.db1, fixture)

    def tearDown(self):
        list(map(psql.drop_if_exists, [self.db1, self.db2]))

    def test_dbexists(self):
        self.assertTrue(psql.dbexists(self.db1))

    def test_not_dbexists(self):
        self.assertFalse(psql.dbexists(self.db2))

    def test_create(self):
        db = self.db2
        self.assertFalse(psql.dbexists(db))
        self.assertTrue(psql.create(db))
        self.assertTrue(psql.dbexists(db))

    def test_drop(self):
        db = self.db2
        self.assertTrue(psql.create(db))
        self.assertTrue(psql.dbexists(db))
        self.assertTrue(psql.drop(db))
        self.assertFalse(psql.dbexists(db))

    def test_runsql(self):
        "running a query yields expected results"
        results = psql.runsql(self.db1, "select * from table1")
        self.assertTrue(
            isinstance(results, types.GeneratorType)
        )  # we get a lazy result back
        expected_fields = ["field1", "field2"]
        for row in results:
            self.assertTrue(isinstance(row, dict))  # each row in result is a dictionary
            self.assertCountEqual(list(row.keys()), expected_fields)

    def test_runsql_fails_on_missing_database(self):
        "running a query against a missing database raises a error"
        self.assertRaises(pg8k.DatabaseError, psql.runsql, self.db2, "asrf")


class Backup(BaseCase):
    def setUp(self):
        self.dbname = "_ubr_testdb"
        psql.create_if_not_exists(self.dbname)
        fixture = join(self.fixture_dir, "psql_ubr_testdb.psql.gz")
        psql.load(self.dbname, fixture)

        self.backup_dir = conf.WORKING_DIR  # TODO: change this temp.dir
        self.assertTrue(psql.dbexists(self.dbname))

    def tearDown(self):
        psql.drop_if_exists(self.dbname)

    def test_backup(self):
        "a simple dump of the database happens"
        psql.backup(self.dbname)
        expected_path = join(self.backup_dir, self.dbname + "-psql.gz")
        self.assertTrue(os.path.exists(expected_path))

    def test_backup_db_doesnt_exist(self):
        "a backup request for a database that doesn't exist, never happens"
        expected = []  # nothing backed up
        self.assertEqual(expected, psql.backup("foo")["output"])


class Restore(BaseCase):
    def setUp(self):
        self.db = "_ubr_testdb"
        psql.drop_if_exists(self.db)

    def tearDown(self):
        psql.drop_if_exists(self.db)

    def test_restore(self):
        "a database dump can be restored"
        # no database
        self.assertFalse(psql.dbexists(self.db))
        # will look for .../fixtures/_ubr_testdb.psql.gz
        expected = {"output": [(self.db, True)]}
        self.assertEqual(expected, psql.restore([self.db], self.fixture_dir))
        self.assertTrue(psql.dbexists(self.db))

    def test_restore_when_db_exists(self):
        "restoring a database drops any existing one"
        psql.create(self.db)
        fixture = join(self.fixture_dir, "psql_ubr_testdb.psql.gz")
        psql.load(self.db, fixture)

        psql.runsql(self.db, "delete from table1")
        self.assertEqual(0, len(list(psql.runsql(self.db, "select * from table1"))))

        psql.restore([self.db], self.fixture_dir)
        self.assertEqual(2, len(list(psql.runsql(self.db, "select * from table1"))))

    def test_load_can_drop_the_existing_db(self):
        "restoring a database drops any existing one"
        psql.create(self.db)
        fixture = join(self.fixture_dir, "psql_ubr_testdb.psql.gz")
        psql.load(self.db, fixture)

        psql.runsql(self.db, "delete from table1")
        self.assertEqual(0, len(list(psql.runsql(self.db, "select * from table1"))))

        psql.load(self.db, fixture, dropdb=True)
        self.assertEqual(2, len(list(psql.runsql(self.db, "select * from table1"))))
