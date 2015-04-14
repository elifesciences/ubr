import os, unittest
import main

"""These examples can be run with:
   python -m unittest discover -s tests/unittests/ -p *_test.py


"""

class BasicUsage(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_find_descriptors(self):
        self.assertEqual(0, len(main.find_descriptors(".")))

if __name__ == '__main__':
    unittest.main()
