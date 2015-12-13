#!/usr/bin/python

import unittest
import sys
sys.path.insert(0, 'machine_files/' + sys.argv[1] + "/")

if __name__ == "__main__":
    all_tests = unittest.TestLoader().discover('machine_files/' + sys.argv[1] + "/")
    unittest.TextTestRunner().run(all_tests)
