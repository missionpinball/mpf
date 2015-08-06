"""Migrates YAML configuration files for MPF from one version to another."""
# config_migrator.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

import optparse
import os
import shutil
import sys
import time
import datetime
import re

import yaml

EXTENSION = '.yaml'
CONFIG_VERSION_FILE = 'config_versions.yaml'
BACKUP_FOLDER_NAME = 'previous_config_files'

file_list = list()
section_replacements = dict()
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
                  help="Force reprocessing of files thare are already the latest"
                   "config version")

options, args = parser.parse_args()
options = vars(options)

try:
    source_str = args[0]
except:
    print "Error: YAML file or search folder not specified."
    sys.exit()


def load_config():

    global previous_config_version
    global new_config_version
    global section_deprecations
    global section_replacements
    global section_warnings

    config_dict = yaml.load(open(CONFIG_VERSION_FILE, 'r'))

    # todo could add support for command line param to specify version
    new_config_version = max(config_dict)
    previous_config_version = new_config_version-1

    print
    print ("Migrating MPF config files from v" + str(previous_config_version) +
           " to v" + str(new_config_version))

    target_file_versions.add(previous_config_version)

    if options['force']:
        print ("Will also re-check v" + str(new_config_version) + " files")
        target_file_versions.add(new_config_version)

    section_replacements = config_dict[new_config_version]['section_replacements']
    section_warnings = config_dict[new_config_version]['section_warnings']
    section_deprecations = config_dict[new_config_version]['section_deprecations']


def create_file_list(source_str):

    global root_folder

    if os.path.isfile(source_str):
        root_folder = os.path.dirname(source_str)
        file_list.append(source_str)
    elif os.path.isdir(source_str):
        root_folder = source_str
        os.path.walk(source_str, add_files, EXTENSION)

    else:
        print "not a valid file or folder"

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
            return

    create_backup_file(file_name)

    with open(file_name, 'r') as f:
        file_data = f.read()

    file_data = file_data.replace('config_version=' + str(previous_config_version),
                                  'config_version=' + str(new_config_version))

    for k, v in section_replacements.iteritems():
        pattern = re.compile(re.escape(k + ':'), re.IGNORECASE)
        file_data = pattern.sub(v + ':', file_data)

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

    print
    print "Migration Results"
    print "================="
    print "Backup location for existing files:", backup_root_folder
    print "Files migrated successfully:", len(migrated_files)
    print "Files skipped:", len(skipped_files)
    print "Files that require manual intervention:", len(warnings_files)
    print
    print ("Open up each of these files to see the details of the sections you "
           "need to manually update:")

    for file_name in warnings_files:
        print file_name

    print


def main():

    load_config()

    file_list = create_file_list(source_str)
    create_backup_folder()

    for f in file_list:
        process_file(f)

    display_results()

if __name__ == '__main__':
    main()


# The MIT License (MIT)

# Copyright (c) 2013-2015 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
