import argparse
import unittest
import sys

from mpf.commands import MpfCommandLineParser
from mpf.tests.MpfDocTestCase import MpfDocTestCase

subcommand = True


class Command(MpfCommandLineParser):

    """Run a text unit test from cli."""

    def __init__(self, args, path):
        """Parse args."""
        super().__init__(args, path)
        test_file = self.argv.pop(1)

        parser = argparse.ArgumentParser(description='MPF Command')

        parser.add_argument("-v", help="verbose",
                            default=False, action="store_true", dest="verbose")
        args = parser.parse_args(self.argv[1:])

        with open(test_file) as f:
            test_string = f.read()

        test = MpfDocTestCase(config_string=test_string)
        suite = unittest.TestSuite()
        suite.addTest(test)
        result = unittest.TextTestRunner(verbosity=1 if not args.verbose else 99).run(suite)

        sys.exit(not result.wasSuccessful())
