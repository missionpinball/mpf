import os
import ruamel.yaml as yaml
from ruamel.yaml.dumper import RoundTripDumper

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
        old_config_path = os.path.abspath(os.path.join(
            self.machine.machine_path, os.pardir, 'migrator/before'))

        TestMigratorCls(self.machine.mpf_path, old_config_path)

        for old_file_name, contents in TestMigratorCls.migrated_files.items():
            # print()
            # print(file)
            # print(yaml.dump(contents, Dumper=RoundTripDumper, indent=4))

            target_file_name = old_file_name.replace('before', 'after')
            target_file_name = target_file_name.replace('.yaml', '_after.yaml')

            with open(target_file_name, 'r') as f:
                target_string = f.read()

            migrated_string = yaml.dump(contents, Dumper=RoundTripDumper,
                                        indent=4)

            self.maxDiff = None
            self.assertEqual(migrated_string, target_string)