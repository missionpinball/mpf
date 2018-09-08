"""Migrates YAML configuration files for MPF from one version to another."""

import os
import shutil
import time
import datetime
import logging
import importlib
from copy import deepcopy

from ruamel import yaml
from ruamel.yaml.comments import CommentedSeq, CommentedMap

from mpf.file_interfaces.yaml_roundtrip import YamlRoundtrip
from mpf._version import version
from mpf.core.file_manager import FileManager
from mpf.core.utility_functions import Util

EXTENSION = '.yaml'
BACKUP_FOLDER_NAME = 'previous_config_files'
TARGET_CONFIG_VERSION = 4  # todo change to dynamic param
REPROCESS_CURRENT_VERSION = False
INDENTATION_SPACES = 4


class Migrator:

    """Migrates a config."""

    def __init__(self, mpf_path, machine_path):
        """Initialise migrator."""
        self.log = logging.getLogger('Migrator')
        self.start_time = time.time()
        self.num_config_files = 0
        self.num_show_files = 0
        self.log.info("MPF Migrator: %s", version)
        self.log.info("Migrating config and show files from: %s",
                      machine_path)

        self.mpf_path = mpf_path
        self.machine_path = machine_path
        self.file_list = list()
        self.backup_folder = None
        self.base_folder = None
        # self.target_config_version = int(__config_version__)
        self.target_config_version = TARGET_CONFIG_VERSION
        self.log.info("New config version will be v%s",
                      self.target_config_version)

        self.migrator = importlib.import_module(
            'mpf.migrator.config_version_{}'.format(TARGET_CONFIG_VERSION))

        self.log.debug("Found Migrator for config files v%s",
                       TARGET_CONFIG_VERSION)

        self.build_file_list()
        self.backup_files()
        self.migrate_files()

    def build_file_list(self):
        """Build file list for machine."""
        for root, _, files in os.walk(self.machine_path):
            for file in files:
                if (os.path.splitext(file)[1].lower() == EXTENSION and
                        BACKUP_FOLDER_NAME not in root):
                    self.log.debug("Found file: %s", os.path.join(root, file))
                    self.file_list.append(os.path.join(root, file))

        self.base_folder = (os.path.commonprefix(self.file_list))
        self.log.debug("Detected base folder: %s", self.base_folder)

    def create_backup_folder(self):
        """Create backup folder."""
        this_time = datetime.datetime.fromtimestamp(time.time()).strftime(
            '%Y-%m-%d-%H-%M-%S')
        self.backup_folder = os.path.join(self.machine_path,
                                          BACKUP_FOLDER_NAME, this_time)

    def backup_files(self):
        """Create folder and backup config."""
        self.create_backup_folder()
        self.log.info("Backing up files to %s", self.backup_folder)
        shutil.copytree(self.base_folder, self.backup_folder,
                        ignore=self._ignore_files)
        self.log.debug("Backup done")

    @classmethod
    def _ignore_files(cls, root_folder, contents):
        # ignore previous backup folders
        if BACKUP_FOLDER_NAME in root_folder:
            return contents

        # ignore the data folder since those files can't be opened
        # with the round trip loaded
        if root_folder.split(os.sep)[-1] == 'data':
            return contents

        return_list = list()

        # ignore everything that doesn't have the target extension
        for item in contents:
            if (os.path.isfile(os.path.join(root_folder, item)) and
                    os.path.splitext(item)[1].lower() != EXTENSION):
                return_list.append(item)

        return return_list

    def migrate_files(self):
        """Migrate files in machine."""
        # We need to migrate show files after config files since we need
        # to pull some things out of the configs for the shows.
        round2_files = list()

        for file in self.file_list:
            file_content = FileManager.load(file)

            if isinstance(file_content, CommentedMap):
                migrated_content = self.migrator.migrate_file(file,
                                                              file_content)
                if migrated_content:
                    self.num_config_files += 1
                    self.save_file(file, migrated_content)
            else:
                round2_files.append(file)

        for file in round2_files:
            file_content = FileManager.load(file)
            migrated_content = self.migrator.migrate_file(file, file_content)
            if migrated_content:
                self.num_show_files += 1
                self.save_file(file, migrated_content)

        self.log.info("DONE! Migrated %s config file(s) and %s show file(s) in"
                      " %ss", self.num_config_files, self.num_show_files,
                      round(time.time() - self.start_time, 2))
        self.log.info("Detailed log file is in %s.", os.path.join(
            self.machine_path, 'logs'))
        self.log.info("Original YAML files are in %s", self.backup_folder)

    def save_file(self, file_name, file_contents):
        """Save file."""
        self.log.info("Writing file: %s", file_name)
        FileManager.save(file_name, file_contents)


class VersionMigrator:

    """Parent class for a version-specific migrator.

    One instance of this base class exists for each different config file version.
    """

    initialized = False
    deprecations = ''
    renames = ''
    moves = ''
    additions = ''
    migration_logger = None     # type: logging.Logger
    config_version = None       # type: int
    log = logging.getLogger('Migrator')

    def __init__(self, file_name, file_contents):
        """Initialize a specific instance of this file migrator.

        A new instance is created for each file to be migrated.

        Args:
            file_name: Full path and file name of the file being migrated.
            file_contents: ruamel.load(ed) contents of the file which includes
                the comments.

        Returns:
            Modified file_contents instance with the migrations applied.
        """
        self.log = logging.getLogger(os.path.basename(file_name))
        self.file_name = file_name
        self.base_name = os.path.basename(file_name).lower()
        self.fc = file_contents
        self.current_config_version = 0

        if not self.initialized:
            self._initialize()

        self.log.debug('')
        self.log.debug("------------------ %s ------------------",
                       os.path.basename(file_name))

    @classmethod
    def _initialize(cls):
        # Initializes the class
        cls.migration_logger = logging.getLogger('v%s Migrator' %
                                                 cls.config_version)

        # Deprecations
        cls.deprecations = yaml.load(cls.deprecations)
        try:
            for i, key in enumerate(cls.deprecations):
                cls.deprecations[i] = list(key.split('|'))  # pylint: disable-msg=unsupported-assignment-operation
        except TypeError:
            cls.deprecations = list()

        # Adds
        cls.additions = yaml.load(cls.additions)

        if not cls.additions:
            cls.additions = dict()

        # Renames
        cls.renames = yaml.load(cls.renames)
        try:
            for rename in cls.renames:
                rename['old'] = list(rename['old'].split('|'))
        except TypeError:
            cls.renames = list()

        # Moves
        if cls.moves:
            cls.moves = yaml.load(cls.moves)
            for i, move in enumerate(cls.moves):
                move['old'] = move['old'].split('|')
                move['new'] = move['new'].split('|')
                cls.moves[i] = move     # pylint: disable-msg=unsupported-assignment-operation
        else:
            cls.moves = dict()

        cls.initialized = True

    def migrate(self):
        """Migrate configs and shows."""
        if isinstance(self.fc, CommentedMap):
            if not self._migrate_config_file():
                return False
            self.log.debug("----------------------------------------")
            return self.fc
        elif isinstance(self.fc, CommentedSeq):
            if self.is_show_file():
                self._migrate_show_file()
                self.log.debug("----------------------------------------")
                return self.fc

        self.log.debug("Ignoring data file: %s. (Error is ok)", self.file_name)
        return False

    # pylint: disable-msg=no-self-use
    def is_show_file(self):
        """Return true if show file."""
        return False

    def _migrate_show_file(self):
        print(self.file_name, self._get_config_version())

    def _migrate_config_file(self):
        self.log.debug("Analyzing config file: %s", self.file_name)
        if not self._migration_needed():
            return False
        self._update_config_version()
        self.log.debug("Converting keys to lowercase")
        self._do_lowercase()
        self._do_rename()
        self._do_moves()
        self._do_custom()
        self._do_deprecations()
        self._do_adds()
        return True

    def _migration_needed(self):
        self.current_config_version = self._get_config_version()

        if not self.current_config_version:
            self.log.debug("Skipping non-config file: %s", self.file_name)
            return False
        else:
            if self.current_config_version == self.config_version:
                if REPROCESS_CURRENT_VERSION:
                    self.log.info('Reprocessing file which is already '
                                  'config_version=%s', self.config_version)
                    return True
                else:
                    self.log.info('File is already config_version=%s. '
                                  'Skipping...', self.config_version)
                    return False
            else:  # config_version is less than current:
                if self.config_version - self.current_config_version > 1:
                    # use a different loader
                    return True
                elif self.config_version - self.current_config_version == 1:
                    return True
                else:
                    self.log.warning('MPF version mismatch. File is '
                                     'config_version=%s, but this version of'
                                     'MPF is for config_version=%s. '
                                     'Skipping...',
                                     self.current_config_version,
                                     self.config_version)
                    return False

    def _update_config_version(self):
        # Do a str.replace to preserve any spaces or comments in the header
        self.fc.ca.comment[1][0].value = (
            self.fc.ca.comment[1][0].value.replace(
                'config_version={}'.format(self.current_config_version),
                'config_version={}'.format(self.config_version)))

        self.log.debug('Setting config_version=%s', self.config_version)

    def _get_config_version(self):
        try:
            version_num = int(self.fc.ca.comment[1][0].value.split(
                'config_version=')[1])
            self.log.debug("Current config version is %s", version_num)
            return version_num

        except (TypeError, IndexError):  # No version
            pass

    def _do_deprecations(self):
        # deprecations is a list of lists
        for key in deepcopy(self.deprecations):
            # Everything this does needs the dict, so we pull off the first
            # key so we can get the top level dict
            first_key = key.pop(0)

            if '__list__' in key:
                # If there's a "__list__" string in our list, it means one of
                # the items is a list instead of a dict which we'll have to
                # loop through. In that case, we loop through 20 times, each
                # time checking a different element. That's what the
                # _increment_key_with_list() does.

                key = self._increment_key_with_list(key)

                if first_key not in self.fc:
                    # If the first key isn't even here, we can skip all this
                    continue

                else:  # key found, key is nested
                    for dummy_iterator in range(20):

                        if self._remove_key(first_key, key):
                            continue

                        # Not found, but we have a list, so increment & repeat
                        key = self._increment_key_with_list(key)

            else:  # dict only, no list
                self._remove_key(first_key, key)

    def _remove_key(self, first_key, key):
        # actually removes the key from the dict, with nested dicts only
        # (no lists in there)

        if not key:  # single item
            if first_key in self.fc:

                YamlRoundtrip.del_key_with_comments(self.fc, first_key,
                                                    self.log)
                return True

        try:
            if self.fc[first_key].mlget(key, list_ok=True) is not None:
                # mlget just verifies with a nested dict / list
                # index that the key is found.
                final_key = key.pop(-1)
                dic = self.fc[first_key]

                while key:
                    # Loop to get the parent container of the
                    # lowest level key
                    dic = dic[key.pop(0)]

                YamlRoundtrip.del_key_with_comments(dic, final_key, self.log)
                return True
        except (KeyError, IndexError):
            pass

        return False

    @classmethod
    def _increment_key_with_list(cls, key):
        for i, val in enumerate(key):
            if val == '__list__':
                key[i] = 0
            elif isinstance(val, int):
                key[i] += 1

        return key

    def _do_adds(self):
        for section, keys in self.additions.items():
            if section in self.fc:
                for k, v in keys.items():
                    self.log.debug('Adding new key: %s:%s:%s', section, k, v)

                self.fc[section].update(keys)

    def _do_rename(self):
        for rename in self.renames:

            if len(rename['old']) > 1:  # searching for nested key

                found_section = Util.get_from_dict(self.fc, rename['old'][:-1])

                if not found_section:
                    continue

                self.log.debug('Renaming key: %s: -> %s:',
                               ':'.join(rename['old']), rename['new'])
                YamlRoundtrip.rename_key(rename['old'][-1], rename['new'],
                                         found_section)

            else:  # searching for a single key anywhere
                self._recursive_rename(rename['old'][0], rename['new'],
                                       self.fc)

    def _recursive_rename(self, old, new, target):
        if isinstance(target, list):
            for item in target:
                self._recursive_rename(old, new, item)
        elif isinstance(target, dict):

            if old in target:
                YamlRoundtrip.rename_key(old, new, target, self.log)

            for item in target.values():
                self._recursive_rename(old, new, item)

    def _do_moves(self):
        # first move, then rename
        for move in deepcopy(self.moves):
            orig_list = deepcopy(move['old'])
            old_parent = orig_list.pop(0)

            if old_parent not in self.fc:
                continue

            if orig_list:
                old_dict = self.fc[old_parent].mlget(orig_list)
            else:
                old_dict = self.fc[old_parent]

            if not old_dict:
                continue

            new_location = self.fc

            self.log.debug("Moving key: %s -> %s", ':'.join(orig_list),
                           ':'.join(move['new']))

            for key in move['new'][:-1]:
                try:
                    new_location = new_location[key]
                except KeyError:
                    new_location[key] = CommentedMap()
                    new_location = new_location[key]

            new_location[move['new'][-1]] = old_dict
            self._remove_key(old_parent, orig_list)

    def _do_lowercase(self, dic=None):
        # recurcisely converts all keys in dicts and nested dicts
        if not dic:
            dic = self.fc

        key_list = list(dic.keys())

        for key in key_list:
            try:
                YamlRoundtrip.rename_key(key, key.lower(), dic, self.log)
            except AttributeError:
                pass

            try:
                if isinstance(dic[key.lower()], dict):
                    self._do_lowercase(dic[key.lower()])
            except AttributeError:
                if isinstance(dic[key], dict):
                    self._do_lowercase(dic[key])

    def _do_custom(self):
        pass
