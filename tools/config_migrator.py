"""Migrates YAML configuration files for MPF from one version to another."""

import optparse
import os
import shutil
import sys
import time
import datetime
import re

from mpf.system.config import Config
from mpf.system.file_manager import FileManager

EXTENSION = '.yaml'
CONFIG_VERSION_FILE = 'config_versions.yaml'
BACKUP_FOLDER_NAME = 'previous_config_files'

file_list = list()
section_replacements = dict()
string_replacements = dict()
section_warnings = dict()
section_deprecations = set()
root_folder = ''
backup_root_folder = ''
previous_config_version = 0
new_config_version = 0
skipped_files = list()
migrated_files = list()
warnings_files = list()
target_file_versions = set()

parser = optparse.OptionParser()

parser.add_option("-f", "--force",
                  action="store_true", dest="force", default=False,
                  help="Force reprocessing of files thare are already the "
                  "latest config version")

options, args = parser.parse_args()
options = vars(options)

try:
    source_str = args[0]
except:
    print("Error: YAML file or search folder not specified.")
    sys.exit()


def load_config():

    global previous_config_version
    global new_config_version
    global section_deprecations
    global section_replacements
    global section_warnings
    global string_replacements

    config_dict = FileManager.load(CONFIG_VERSION_FILE)

    for key in list(config_dict.keys()):
        if type(key) is not int:
            del config_dict[key]

    # todo could add support for command line param to specify version
    new_config_version = max(config_dict)
    previous_config_version = new_config_version-1

    print()
    print(("Migrating MPF config files from v" + str(previous_config_version) +
           " to v" + str(new_config_version)))

    target_file_versions.add(previous_config_version)

    if options['force']:
        print(("Will also re-check v" + str(new_config_version) + " files"))
        target_file_versions.add(new_config_version)

    section_replacements = config_dict[new_config_version].get('section_replacements', dict())
    section_warnings = config_dict[new_config_version].get('section_warnings', dict())
    section_deprecations = config_dict[new_config_version].get('section_deprecations', dict())
    string_replacements = config_dict[new_config_version].get('string_replacements', dict())

def create_file_list(source_str):

    global root_folder

    if os.path.isfile(source_str):
        root_folder = os.path.dirname(source_str)
        file_list.append(source_str)
    elif os.path.isdir(source_str):
        root_folder = source_str
        os.path.walk(source_str, add_files, EXTENSION)

    else:
        print("not a valid file or folder")

    return file_list


def add_files(arg, dirname, names):

    global BACKUP_FOLDER_NAME

    if BACKUP_FOLDER_NAME in dirname:
        return

    for file_name in names:
        if file_name.lower().endswith(arg):
            file_list.append(os.path.join(dirname, file_name))


def process_file(file_name):

    global section_replacements
    global section_warnings
    global section_deprecations
    global string_replacements
    global previous_config_version
    global new_config_version
    global skipped_files
    global migrated_files
    global warnings_files
    global target_file_versions

    found_warning = False

    with open(file_name) as f:

        file_version = f.readline().split('config_version=')[-1:][0]

        try:
            file_version = int(file_version)
        except ValueError:
            file_version = 0

        if file_version not in target_file_versions:
            skipped_files.append(file_name)
            print("Skipping File:", file_name)
            return

    print("Processing File:", file_name)

    create_backup_file(file_name)

    with open(file_name, 'r') as f:
        file_data = f.read()

    file_data = file_data.replace('config_version=' + str(previous_config_version),
                                  'config_version=' + str(new_config_version))

    for warning in section_warnings:

        pattern = re.compile(re.escape(warning['path'] + ':'), re.IGNORECASE)

        if re.search(pattern, file_data):
            file_data = ('# ---------------------------------------------------'
                '\n# MIGRATION WARNING:\n'
                '# This file contains a "' + warning['path'] + '" section which'
                ' underwent major changes in config_version=' +
                str(new_config_version) + '.\n# You will have to read the docs '
                'and re-do this section.\n# New documentation for this section '
                'is here:\n# ' + warning['url']+ '\n\n' +
                "# When you're done, delete this message so #config_version=" +
                str(new_config_version) + ' is the first line in this file.\n'
                '# ---------------------------------------------------\n\n'
                + file_data)

            found_warning = True

    for section in section_deprecations:

        new_string = ('########################################################'
                      '############\n# NOTE: The section "' + section + '" has '
                      'been deprecated. You can remove it\n####################'
                      '################################################\n')

        pattern = re.compile(re.escape(section + ':'), re.IGNORECASE)
        file_data = pattern.sub(new_string + section + ':', file_data)

    for k, v in section_replacements.items():
        pattern = re.compile('\\b(' + k + ')\\b:', re.IGNORECASE)
        file_data = pattern.sub(v + ':', file_data)

    for k, v in string_replacements.items():
        pattern = re.compile(k, re.IGNORECASE)
        file_data = pattern.sub(v, file_data)

    with open(file_name, 'w') as f:
        f.write(file_data)

    if found_warning:
        warnings_files.append(file_name)
    else:
        migrated_files.append(file_name)


def create_backup_folder():

    global BACKUP_FOLDER_NAME
    global root_folder
    global backup_root_folder

    try:
        os.makedirs(os.path.join(root_folder, BACKUP_FOLDER_NAME))
    except OSError:
        if not os.path.isdir(os.path.join(root_folder, BACKUP_FOLDER_NAME)):
            raise

    this_time = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d-%H-%M-%S')
    backup_root_folder = os.path.join(root_folder, BACKUP_FOLDER_NAME, this_time)

    try:
        os.makedirs(backup_root_folder)
    except OSError:
        if not os.path.isdir(backup_root_folder):
            raise


def create_backup_file(file_name):
    global backup_root_folder

    shutil.copy2(file_name, backup_root_folder)


def display_results():
    global skipped_files
    global migrated_files
    global warnings_files

    print()
    print("Migration Results")
    print("=================")
    print("Backup location for existing files:", backup_root_folder)
    print("Files migrated successfully:", len(migrated_files))
    print("Files skipped:", len(skipped_files))
    print("Files that require manual intervention:", len(warnings_files))

    if warnings_files:
        print()
        print ("Open up each of these files to see the details of the sections "
               "you need to manually update:")

    for file_name in warnings_files:
        print(file_name)

    print()


def main():

    load_config()

    file_list = create_file_list(source_str)
    create_backup_folder()

    for f in file_list:
        process_file(f)

    display_results()

if __name__ == '__main__':
    main()
