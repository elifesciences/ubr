import os, shutil, unittest
from ubr import main, mysql_backup
from datetime import datetime

"""These examples can be run with:
   python -m unittest discover -s tests/ -p *_test.py

"""

THIS_DIR = os.path.abspath(os.path.dirname(__file__))

class BaseCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(BaseCase, self).__init__(*args, **kwargs)
        self.maxDiff = 1024
        self.fixture_dir = THIS_DIR # I might have a dedicated fixtures dir in future. /shrug
        self.expected_output_dir = '/tmp/foo'

class BasicUsage(BaseCase):
    def setUp(self):
        self.known_backup_fixtures = [
            os.path.join(self.fixture_dir, "ubr-backup.yaml"),
            os.path.join(self.fixture_dir, "ubr-2-backup.yaml"),
        ]


    def tearDown(self):
        os.system('rm -rf %s' % self.expected_output_dir)

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
        self.assertTrue(main.dir_exists(self.expected_output_dir))
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

class TestTarredGzippedBackup(BaseCase):
    def setUp(self):
        pass

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

class TestUploadToS3(BaseCase):
    def setUp(self):
        self.s3_backup_bucket = 'elife-app-backups'
        self.project_name = '_test'
        self.hostname = 'testmachine'

    def tearDown(self):
        pass

    def test_s3_file_exists(self):
        "we can talk to s3 about the existence of files"
        s3obj = main.s3_file(self.s3_backup_bucket, self.project_name)
        self.assertTrue(isinstance(s3obj, dict))
        self.assertTrue(s3obj.has_key('Contents'))

    def test_backup_is_copied_to_s3(self):
        "the results of a backup are uploaded to s3"
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        descriptor = {'tar-gzipped': [fixture, os.path.join(self.fixture_dir, '*/**')]}
        results = main.backup(descriptor, output_dir=self.expected_output_dir)
        
        main.upload_backup_to_s3(self.s3_backup_bucket, results, self.project_name, self.hostname)

        s3obj = main.s3_file(self.s3_backup_bucket, self.project_name)
        self.assertTrue(s3obj.has_key('Contents'))


class TestDatabaseBackup(BaseCase):
    def setUp(self):
        self.expected_output_dir = '/tmp/bar'
        self.project_name = '_test'
        mysql_backup.load(self.project_name, os.path.join(self.fixture_dir, 'mysql_test_table.sql'))

    def tearDown(self):
        assert self.expected_output_dir.startswith('/tmp'), "cowardly refusing to recursively delete anything outside /tmp ..."
        shutil.rmtree(self.expected_output_dir)

    def test_dump_db(self):
        "a compressed dump of the test database is created at the expected destination"
        descriptor = {'mysql-database': ['_test']}        
        results = main.backup(descriptor, output_dir=self.expected_output_dir)
        self.assertEqual(1, len(results['mysql-database']['output']))

        expected_path = os.path.join(self.expected_output_dir, results['mysql-database']['output'][0])
        self.assertTrue(os.path.isfile(expected_path))

if __name__ == '__main__':
    unittest.main()
