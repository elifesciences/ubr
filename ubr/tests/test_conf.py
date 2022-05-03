import os
from unittest import mock
from ubr import conf
from .base import BaseCase


class One(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_conf__var_default(self):
        expected = "bup"
        actual = conf._var("UBR_FOO", "foo.bar", "bup")
        self.assertEqual(expected, actual)

    def test_conf__var__cfg(self):
        expected = "baz"
        with mock.patch("ubr.conf._cfg", return_value=expected) as mockobj:
            actual = conf._var("UBR_FOO", "foo.bar", "bup")
            self.assertEqual(expected, actual)
            self.assertEqual(mockobj.call_count, 1)

    def test_conf__var__envvar(self):
        try:
            expected = "baz"
            os.environ["UBR_FOO"] = expected
            actual = conf._var("UBR_FOO", "foo.bar", "bup")
            self.assertEqual(expected, actual)
        finally:
            os.environ["UBR_FOO"] = ""
