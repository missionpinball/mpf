"""Run regression tests."""

if __name__ == '__main__':
    import os
    import sys
    import unittest

    from mpf.tests.MpfDocTestCase import MpfDocTestCase

    tests = []
    for subdir, dirs, files in os.walk(os.path.join(os.path.dirname(__file__), "mpf", "tests", "regression_tests")):
        for file in files:
            full_path = os.path.join(subdir, file)
            with open(full_path) as f:
                config_string = f.read()
            testcase = MpfDocTestCase(config_string)
            testcase._testMethodDoc = full_path
            tests.append(testcase)

    suite = unittest.TestSuite()
    suite.addTests(tests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if result.wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)
