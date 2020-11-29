"""Command to format yaml files."""
import sys

import argparse
import re

from mpf.file_interfaces.yaml_roundtrip import YamlRoundtrip

from mpf.commands import MpfCommandLineParser
from mpf.tests.MpfDocTestCase import MpfDocTestCaseBase

SUBCOMMAND = True


class Command(MpfCommandLineParser):

    """Run a text unit test from cli."""

    def __init__(self, args, path):
        """Parse args."""
        super().__init__(args, path)
        test_file = self.argv.pop(1)

        parser = argparse.ArgumentParser(description='MPF Command')

        parser.add_argument("--yes", help="perform the action",
                            default=False, action="store_true", dest="do_it")

        args = parser.parse_args(self.argv[1:])

        with open(test_file) as f:
            test_string = f.read()

        if ".. code-block:: mpf-config" in test_string or ".. code-block:: mpf-mc-config" in test_string:
            print("Parsing documentation page {}.".format(test_file))
            new_config = re.sub(".. code-block:: (?P<type>mpf-config|mpf-mc-config)\n\n(?P<code>( {2,4}[^\n]+|\n)+)",
                                self._replace_config, test_string)
        elif test_file.endswith(".rst"):
            print("Rst file {} without test. Skipping.".format(test_file))
            sys.exit(3)
        else:
            print("Parsing single test {}.".format(test_file))
            new_config = self._reformat_test_case(test_string)

        if new_config != test_string:
            print("Config is not linted.")
            print(MpfDocTestCaseBase.unidiff_output(test_string, new_config))
            if args.do_it:
                print("Writing back changes")
                with open(test_file, "w") as f:
                    f.write(new_config)
                sys.exit(1)
            else:
                print("Not writing back changes. Use --yes to do this.")
                sys.exit(2)
        else:
            print("Config is ok.")
            sys.exit(0)

    def _replace_config(self, test_case):
        text = test_case.group("code")
        indent_len = None
        unindented_text = ''
        for line in text.split("\n"):
            if indent_len is None:
                indent = re.search("^( )+", line)
                if not indent:
                    raise AssertionError("Block is incorrectly indented: {}.".format(text))
                indent_len = len(indent.group(0))
            unindented_text += line[indent_len:] + "\n"

        undented_result = self._reformat_test_case(unindented_text)

        indented_result = ".. code-block:: " + test_case.group("type") + "\n\n"
        for line in undented_result.split("\n"):
            if line:
                indented_result += " " * indent_len + line + "\n"
            else:
                indented_result += "\n"
        return indented_result

    # pylint: disable-msg=too-many-locals
    def _reformat_test_case(self, test_case):
        test_case = test_case.replace("\t", "  ")
        test_case = re.sub(r" +\n", "\n", test_case)
        machine_config, extra_configs, mode_configs, show_configs, assets, code, tests = \
            MpfDocTestCaseBase.prepare_config(test_case, fixup_config=False)
        formatted_yaml = ""
        if machine_config:
            new_config = self._reformat(machine_config, show_file=False)
            if new_config == "null\n...\n":
                formatted_yaml += machine_config
            else:
                formatted_yaml += new_config
        for config_name, extra_config in extra_configs.items():
            formatted_yaml += "##! config: " + config_name + "\n"
            formatted_yaml += self._reformat(extra_config, show_file=False)
        for mode_name, mode_config in mode_configs.items():
            formatted_yaml += "##! mode: " + mode_name + "\n"
            formatted_yaml += self._reformat(mode_config, show_file=False)
        if show_configs:
            for show_name, show_config in show_configs.items():
                formatted_yaml += "##! show: " + show_name + "\n"
                formatted_yaml += self._reformat(show_config, show_file=True)

        if code:
            for file_path, file_content in code:
                formatted_yaml += "##! code: " + "/".join(file_path) + "\n"
                formatted_yaml += file_content

        if assets:
            for asset_path, asset_source in assets.items():
                formatted_yaml += "##! asset: {}={}\n".format(asset_path, asset_source)

        if tests:
            formatted_yaml += "##! test\n"
            for test in tests:
                formatted_yaml += test + "\n"

        return formatted_yaml.strip() + "\n"

    @staticmethod
    def _reformat(yaml_string, show_file):
        new_config = YamlRoundtrip.reformat_yaml(yaml_string, show_file)
        if new_config == "null\n...\n":
            return yaml_string

        return new_config
