import os
from ubr import main
from base import BaseCase

class TestTarredGzippedBackup(BaseCase):
    def setUp(self):
        self.expected_output_dir = '/tmp/foo'

    def tearDown(self):
        os.system('rm /tmp/foo/archive.tar.gz')

    def test_simple_tgz(self):
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        descriptor = {'tar-gzipped': [fixture, os.path.join(self.fixture_dir, '*/**')]}
        output = main.backup(descriptor, output_dir=self.expected_output_dir)

        expected_output = {
            'tar-gzipped': {
                'output': [os.path.join(self.expected_output_dir, 'archive.tar.gz')]}}
        self.assertEqual(output, expected_output)
        # test all of the files exist
        for path in output['tar-gzipped']['output']:
            self.assertTrue(os.path.exists(path))

    def test_tgz_returns_a_list_of_outputs(self):
        "the tgz target returns a list for it's 'output' result. all targets must return a list"
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        descriptor = {'tar-gzipped': [fixture]}
        results = main.backup(descriptor, output_dir=self.expected_output_dir)
        self.assertEqual(1, len(results['tar-gzipped']['output']))

class TestTarredGzippedRestore(BaseCase):
    def setUp(self):
        self.expected_output_dir = '/tmp/baz'

    def tearDown(self):
        os.system('rm %s' % os.path.join(self.expected_output_dir, 'archive.tar.gz'))

    def test_tgz_restore(self):
        "tar-gzipped target unpacks the backup and restores the files"
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        descriptor = {'tar-gzipped': [fixture]}
        main.backup(descriptor, output_dir=self.expected_output_dir)
        # ensure an archive was created
        self.assertTrue(os.path.isfile(os.path.join(self.expected_output_dir, 'archive.tar.gz')))

        expected_results = {
            'tar-gzipped': {'output': [(os.path.abspath(fixture), True)]}}
        results = main.restore(descriptor, backup_dir=self.expected_output_dir)
        self.assertEqual(results, expected_results)

