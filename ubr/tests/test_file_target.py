import os, shutil
from ubr import main, utils
from base import BaseCase

class TestFileBackup(BaseCase):
    def setUp(self):
        self.expected_output_dir = '/tmp/foo'

    def tearDown(self):
        if os.path.exists(self.expected_output_dir):
            shutil.rmtree(self.expected_output_dir)

    def expected_fixture_path(self, fixture_path):
        return os.path.join(self.expected_output_dir,
                            os.path.dirname(fixture_path).lstrip('/'),
                            os.path.basename(fixture_path))

    def test_backup_single_file(self):
        "a simple descriptor of individual file backups can be run"
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        descriptor = {'files': [fixture]}

        expected_output = {
            'files': {'output_dir': self.expected_output_dir,
                      'output': [self.expected_fixture_path(fixture)]}
        }

        output = main.backup(descriptor, output_dir=self.expected_output_dir)
        self.assertEqual(expected_output, output)
        self.assertTrue(utils.dir_exists(self.expected_output_dir))
        # test all of the files exist
        for path in output['files']['output']:
            self.assertTrue(os.path.exists(path))

    def test_backup_multiple_file(self):
        "a simple descriptor of individual file backups can be run"
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        fixture2 = os.path.join(self.fixture_dir, 'img2.jpg')
        descriptor = {'files': [fixture, fixture2]}

        expected_output = {
            'files': {
                'output_dir': self.expected_output_dir,
                'output': [
                    self.expected_fixture_path(fixture),
                    self.expected_fixture_path(fixture2),
                ]
            }
        }

        output = main.backup(descriptor, output_dir=self.expected_output_dir)
        self.assertEqual(expected_output, output)
        # test all of the files exist
        for path in output['files']['output']:
            self.assertTrue(os.path.exists(path))

    def test_backup_multiple_dispersed_files(self):
        "a simple descriptor of individual files in different directories can be run"
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        fixture2 = os.path.join(self.fixture_dir, 'img2.jpg')
        fixture3 = os.path.join(self.fixture_dir, "subdir", 'img3.jpg')

        descriptor = {'files': [fixture, fixture2, fixture3]}

        expected_output = {
            'files': {
                'output_dir': self.expected_output_dir,
                'output': [
                    self.expected_fixture_path(fixture),
                    self.expected_fixture_path(fixture2),
                    self.expected_fixture_path(fixture3),
                ]
            }
        }
        output = main.backup(descriptor, output_dir=self.expected_output_dir)
        self.assertEqual(expected_output, output)
        # test all of the files exist
        for path in output['files']['output']:
            self.assertTrue(os.path.exists(path))

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
            'files': {
                'output_dir': self.expected_output_dir,
                'output': [
                    self.expected_fixture_path(fixture),
                    self.expected_fixture_path(fixture2),
                    self.expected_fixture_path(fixture3),
                    self.expected_fixture_path(fixture4),
                ]
            }
        }
        output = main.backup(descriptor, output_dir=self.expected_output_dir)
        self.assertEqual(expected_output, output)
        # test all of the files exist
        for path in output['files']['output']:
            self.assertTrue(os.path.exists(path))

    def test_unknown_backup(self):
        "an unknown target is reported"
        '''
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        # a /dev/null backup is valid, right? restore process sucks though ...
        descriptor = {'dev-null': [fixture]}
        '''
        pass

    def test_backup_to_dynamic_output_dir(self):
        "we're writing our output to a known output_dir for these tests. what happens when we try to output to a dir that doesn't exist?"
        pass

    def test_backup_of_file_to_same_output_dir(self):
        pass

    def test_backup_of_bad_file(self):
        "what happens when the dir/file we specify in the descriptor doesn't exist"
        pass

    def test_backup_of_no_files(self):
        "what happens when the path we specify in the descriptor doesn't yield any files?"
        pass


class TestFileRestore(BaseCase):
    def setUp(self):
        self.expected_output_dir = os.path.join('/tmp/', utils.ymdhms())

    def tearDown(self):
        pass

    def test_file_restore(self):
        "a file can be backed-up, modified, and then the backed up version restored"
        # copy fixture and ensure contents are what we expect ...
        fixture = os.path.join(self.fixture_dir, 'hello.txt')
        fixture_copy = '/tmp/foo.txt' # this is the file to be backed up
        shutil.copyfile(fixture, fixture_copy)
        self.assertEqual(open(fixture, 'r').read(), open(fixture_copy, 'r').read())
        md5 = utils.generate_file_md5(fixture_copy)

        # backup the fixture copy
        descriptor = {'files': [fixture_copy]}
        main.backup(descriptor, output_dir=self.expected_output_dir)

        # overwrite our fixture copy with some garbage
        open(fixture_copy, 'w').write("fooooooooooooooooooobar")
        bad_md5 = utils.generate_file_md5(fixture_copy)
        self.assertNotEqual(md5, bad_md5)

        # restore our fixture copy
        main.restore(descriptor, backup_dir=self.expected_output_dir)
        self.assertEqual(open(fixture, 'r').read(), open(fixture_copy, 'r').read())
        restored_md5 = utils.generate_file_md5(fixture_copy)
        self.assertEqual(md5, restored_md5)
