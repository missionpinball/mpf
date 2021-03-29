import os

import argparse
import re
import unittest
import sys

# some hacks to unbreak logging afte loading the kivy logger
import logging
root = logging.root
os.environ['KIVY_NO_FILELOG'] = '1'
os.environ['KIVY_NO_CONSOLELOG'] = '1'
os.environ["KIVY_NO_ARGS"] = "1"

from kivy.logger import Logger
for handler in Logger.handlers:
    Logger.removeHandler(handler)
sys.stdout = sys.__stdout__
logging.root = root
# end of anti kivy hacks

from mpf.commands import MpfCommandLineParser
from mpf.tests.MpfDocTestCase import MpfDocTestCase, MpfDocTestCaseNoFakeGame
from mpf.tests.MpfIntegrationDocTestCase import MpfIntegrationDocTestCase

SUBCOMMAND = True


class Command(MpfCommandLineParser):

    """Run a text unit test from cli."""

    def __init__(self, args, path):
        """Parse args."""
        super().__init__(args, path)
        test_file = self.argv.pop(1)

        parser = argparse.ArgumentParser(description='MPF Command')

        parser.add_argument("-v", help="verbose",
                            default=False, action="store_true", dest="verbose")
        parser.add_argument("-m", help="Start MC on non sphinx test (auto-detected in sphinx)",
                            default=False, action="store_true", dest="start_mc")

        args = parser.parse_args(self.argv[1:])

        with open(test_file) as f:
            test_string = f.read()

        base_dir = os.path.dirname(os.path.abspath(test_file))
        suite = unittest.TestSuite()
        simulation = "##! no_simulation" not in test_string

        if ".. code-block:: mpf-config" in test_string or ".. code-block:: mpf-mc-config" in test_string:
            print("Parsing documentation page")
            blocks = re.finditer(".. code-block:: (?P<type>mpf-config|mpf-mc-config)\n\n(?P<code>( {2,4}[^\n]+|\n)+)",
                                 test_string)
            if not blocks:
                raise AssertionError("Could not parse tests.")

            for num, block in enumerate(blocks):
                text = block.group("code")
                indent_len = None
                test_case = ''
                for line in text.split("\n"):
                    if indent_len is None:
                        indent = re.search("^( )+", line)
                        if not indent:
                            raise AssertionError("Block {} (starting at 0) is incorrectly indented.".format(num))
                        indent_len = len(indent.group(0))
                    test_case += line[indent_len:] + "\n"
                if block.group("type") == "mpf-config":
                    if "##! no_fake_game" in test_case:
                        test = MpfDocTestCaseNoFakeGame(config_string=test_case, base_dir=base_dir,
                                                        simulation=simulation)
                    else:
                        test = MpfDocTestCase(config_string=test_case, base_dir=base_dir, simulation=simulation)
                else:
                    test = MpfIntegrationDocTestCase(config_string=test_case, base_dir=base_dir, simulation=simulation)
                test._testMethodDoc = "Block {} (starting at 0)".format(num)
                suite.addTest(test)
        else:
            print("Parsing single test")

            if args.start_mc:
                test = MpfIntegrationDocTestCase(config_string=test_string, base_dir=base_dir, simulation=simulation)
            else:
                if "##! no_fake_game" in test_string:
                    test = MpfDocTestCaseNoFakeGame(config_string=test_string, base_dir=base_dir, simulation=simulation)
                else:
                    test = MpfDocTestCase(config_string=test_string, base_dir=base_dir, simulation=simulation)
            suite.addTest(test)

        result = unittest.TextTestRunner(verbosity=1 if not args.verbose else 99).run(suite)

        sys.exit(not result.wasSuccessful())
