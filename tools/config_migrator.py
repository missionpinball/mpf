"""Migrates YAML configuration files for MPF from one version to another."""
# config_migrator.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

import logging
import optparse
import sys

import yaml

file_list = list()
section_replacements = dict()
section_warnings = dict()
section_deprecations = set()


parser = optparse.OptionParser()

options, args = parser.parse_args()

try:
    source_str = args[0]
except:
    print "Error: YAML file or search folder not specified."
    sys.exit()

def load_config():
    config_file = yaml.load(open('config_versions.yaml', 'r'))

    # find highest version number

    highest_version = 2

    section_replacements = config_file[highest_version]['section_replacements']
    section_warnings = config_file[highest_version]['section_warnings']
    section_deprecations = config_file[highest_version]['section_deprecations']

def create_file_list(source_str):
    return list()
    # todo
    # if file string ends in .yaml, then that's the file
    # if not, check to see if it's a folder
    # scan it for .yaml files
    # add them as found
    # continue scanning through subdirectories


def process_file(file_obj):
    pass

    # find and replace



    for k, v in section_replacements.iteritems():
        pass
        # search for k plus colon, replace with v

    for k, v in section_warnings.iteritems():
        pass
        # search for k plus colon
        # if found, insert warning text, URL
        # log file name

    for section in section_deprecations:
        pass
        # search for k plus colon
        # if found, insert deprecation text
        # log file name, line

def check_file_version():
    pass

    # if config version is already current, print

    # if it's not, make sure it's current minus 1

    # if not, then error since we can't do two at once

    # return true or false

def create_backup_file():
    pass

    # old_config_files\v1\
    # build folder structure to match what it finds

    # if v1 is already there, append timestamp


def main():
    load_config()

    file_list = create_file_list(source_str)

    for f in file_list:
        process_file(f)




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
