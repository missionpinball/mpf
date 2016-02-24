"""Migrates YAML configuration files for MPF from one version to another."""

import os
import shutil
import time
import datetime
import logging
import importlib

from ruamel import yaml
from ruamel.yaml.comments import CommentedSeq, CommentedMap

from mpf._version import version, __config_version__
from mpf.core.file_manager import FileManager
from mpf.core.utility_functions import Util

EXTENSION = '.yaml'
CONFIG_VERSION_FILE = 'migrator/config_versions.yaml'
BACKUP_FOLDER_NAME = 'previous_config_files'


class Migrator(object):
    def __init__(self, mpf_path, machine_path):
        self.log = logging.getLogger('Migrator')
        self.log.info("MPF Migrator v{}".format(version))
        self.log.info("Migrating config and show files from: {}".format(
            machine_path))

        self.log = logging.getLogger()

        self.mpf_path = mpf_path
        self.machine_path = machine_path
        self.file_list = list()
        self.backup_folder = None
        self.base_folder = None
        self.target_config_version = int(__config_version__)
        self.reprocess_current_version_files = False

        self.config_dict = FileManager.load(os.path.join(mpf_path,
                                                         CONFIG_VERSION_FILE))
        for key in list(self.config_dict.keys()):

            try:
                key_int = int(key)
                self.config_dict[key_int] = self.config_dict[key]
                del self.config_dict[key]
            except ValueError:
                del self.config_dict[key]

        self.new_config_version = max(self.config_dict.keys())
        self.previous_config_version = self.new_config_version - 1

        self.build_file_list()
        self.backup_files()
        self.migrate_files()

    def build_file_list(self):
        for root, dir, files in os.walk(self.machine_path):
            for file in files:
                if (os.path.splitext(file)[1].lower() == EXTENSION and
                            BACKUP_FOLDER_NAME not in root):
                    self.log.debug("Found file: {}".format(
                        os.path.join(root, file)))
                    self.file_list.append(os.path.join(root, file))

        self.base_folder = (os.path.commonpath(self.file_list))
        self.log.debug("Detected base folder: {}".format(self.base_folder))

    def create_backup_folder(self):
        this_time = datetime.datetime.fromtimestamp(time.time()).strftime(
            '%Y-%m-%d-%H-%M-%S')
        self.backup_folder = os.path.join(self.machine_path,
                                          BACKUP_FOLDER_NAME, this_time)

        self.log.debug("Backup folder: {}".format(self.backup_folder))

    def backup_files(self):
        self.log.debug("Backing up files")
        self.create_backup_folder()
        shutil.copytree(self.base_folder, self.backup_folder,
                        ignore=self._ignore_files)
        self.log.debug("Backup done")

    def _ignore_files(self, root_folder, contents):
        # ignore previous backup folders
        if BACKUP_FOLDER_NAME in root_folder:
            return contents

        return_list = list()

        # ignore everything that doesn't have the target extension
        for item in contents:
            if (os.path.isfile(os.path.join(root_folder, item)) and
                        os.path.splitext(item)[1].lower() != EXTENSION):
                return_list.append(item)
        return return_list

    def migrate_files(self):
        for file in self.file_list:
            f = FileManager.load(file, round_trip=True)

            if type(f) == CommentedMap:
                self.migrate_config_file(file, f)
            elif type(f) == CommentedSeq:
                self.migrate_show_file(file, f)
            else:
                self.log.debug("Ignoring data file: {}. (Error is ok)".format(file))

    def migrate_config_file(self, file_name, file_contents):

        file_version_num = self._is_config_migration_needed(file_name,
                                                            file_contents)

        if not file_version_num:
            return

        elif file_version_num < self.target_config_version:
            target_version = file_version_num + 1
        else:
            target_version = self.target_config_version


        # update to next config version
        file_contents = self._update_config_version_string(file_contents,
                                                           target_version)

        # Grab the config for this version
        migrator = importlib.import_module(
            'mpf.migrator.config_version_{}'.format(target_version))

        file_contents = self.convert_to_lowercase(file_contents)
        file_contents = self._rename_keys(file_contents, migrator)
        file_contents = migrator.custom_migration(file_contents)
        file_contents = self._remove_deprecated_sections(file_contents,
                                                         migrator)
        file_contents = migrator.get_warnings(file_contents)

        # If the config file is not current, run this again
        while target_version < self.target_config_version:
            self.migrate_config_file(file_name, file_contents)

        self.save_file(file_name, file_contents)

    def _get_config_version(self, file_name, file_contents):
        try:
            # comment attribute, item index 1, first item is first line
            # which should be config_version=X
            version_str = file_contents.ca.comment[1][0].value
            self.log.debug("Analyzing config file: {}".format(file_name))
            version_num = int(version_str.split('config_version=')[1])
            self.log.debug("Current config version is {}".format(version_num))
            return version_num

        except TypeError:
            # Otherwise it's not a config file
            self.log.debug("Skipping non-config file: {}".format(file_name))
            return None

    def _is_config_migration_needed(self, file_name, file_contents):
        file_version_num = self._get_config_version(file_name, file_contents)

        if file_version_num == self.target_config_version:
            self.log.debug('File is already on config version {}'.format(
                file_version_num))

            if self.reprocess_current_version_files:
                self.log.debug('Will re-process config file')
                return file_version_num
            else:
                return False

        else:
            return file_version_num

    def _update_config_version_string(self, file_contents, version):
        file_contents.ca.comment[1][0].value = '#config_version={}'.format(
            version)

        self.log.debug('Setting {}'.format(file_contents.ca.comment[1][0].value))

        return file_contents

    def convert_to_lowercase(self, file_data):

        self.log.debug("Converting keys to lowercase")

        new_data = self.get_new_dict(file_data)

        for k in file_data.keys():
            new_data[k.lower()] = file_data[k]

        return new_data

    def get_new_dict(self, _dict):
        # make a copy of whatever class the existing file_data is
        new_dict = _dict.__class__()
        # Copy the pre and end comments which aren't tied to a key or value
        new_dict.ca.comment = _dict.ca.comment
        new_dict.ca.end = _dict.ca.end

        return new_dict

    def replace_key(self, old_key, new_key, _dict):
        # Since this is an OrderedDict, we have to rebuild instead of
        # popping and inserting
        new_dict = self.get_new_dict(_dict)

        for k in _dict.keys():
            if k == old_key:
                new_dict[new_key] = _dict[old_key]

                try:
                    new_dict.ca.items[new_key] = _dict.ca.items[old_key]
                except KeyError:
                    pass
            else:
                new_dict[k] = _dict[k]
                try:
                    new_dict.ca.items[k] = _dict.ca.items[k]
                except KeyError:
                    pass

        return new_dict

    def replace_key2(self, old_key, new_key, _dict):

        key_list = list(_dict.keys())

        for key in key_list:
            if key == old_key:
                _dict[new_key] = _dict[old_key]

                _dict.ca.items[new_key] = _dict.ca.items.pop(old_key)
                # print(_dict.ca.items)
                del _dict[old_key]
            else:
                _dict.move_to_end(key)

    def _remove_deprecated_sections(self, file_contents, migrator):

        section_dict = yaml.load(migrator.section_deprecations)

        # TODO need to make this recursive
        for section in section_dict:
            if section in file_contents:
                self.log.debug(
                    "Removing deprecated section: {}".format(section))
                del file_contents[section]

        return file_contents

    def _rename_keys(self, file_contents, migrator):
        print('renaming keys')
        return file_contents

    def migrate_show_file(self, file_name, file_contents):
        self.log.debug("Analyzing show file: {}".format(file_name))

        for i, x in enumerate(file_contents):
            file_contents[i] = self.replace_key2('tocks', 'time', x)

        self.save_file(file_name, file_contents)

    def save_file(self, file_name, file_contents):
        self.log.info("Writing file: {}".format(file_name))
        # FileManager.save(file_name, file_contents, include_comments=True)