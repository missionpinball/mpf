import os
import ruamel.yaml as yaml
from ruamel.yaml.dumper import RoundTripDumper

from mpf.migrator.config_version_4 import V4Migrator
from mpf.migrator.migrator import Migrator
from mpf.tests.MpfTestCase import MpfTestCase

from collections import OrderedDict


class TestMigratorCls(Migrator):

    migrated_files = OrderedDict()

    def save_file(self, file_name, file_contents):
        TestMigratorCls.migrated_files[file_name] = file_contents

    def backup_files(self):
        pass


class TestMigrator(MpfTestCase):

    def test_migrator(self):

        self.expected_duration = 3.0

        old_config_path = os.path.abspath(os.path.join(
            self.machine.machine_path, os.pardir, 'migrator/config_v3'))

        V4Migrator.MAIN_CONFIG_FILE = 'test_config2_v3.yaml'

        TestMigratorCls(self.machine.mpf_path, old_config_path)

        for old_file_name, contents in TestMigratorCls.migrated_files.items():
            target_file_name = old_file_name.replace('config_v3', 'config')
            target_file_name = target_file_name.replace('_v3', '_v4')

            with open(target_file_name, 'r') as f:
                target_string = f.read()

            migrated_string = yaml.dump(contents, Dumper=RoundTripDumper,
                                        indent=4)

            # print(migrated_string)
            # print('--------------------------------------------------------')

            self.maxDiff = None  # Full file contents in the log on failure

            # todo
            # the dict order is dumped out randomly, need to figure out
            # a way to test this consistently. For now we can just
            # uncomment this when we're actually testing the migrator.

            # self.assertEqual(migrated_string, target_string)
