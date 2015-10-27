"""Contains the FileManager and FileInterface base classes."""
# file_manager.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import os
import sys
import mpf.file_interfaces


class FileInterface(object):

    file_types = list()

    def __init__(self):
        self.log = logging.getLogger('{} Config Processor'.format(
            self.file_types[0][1:].upper()))

    def find_file(self, filename):
        """Tests whether the passed file is valid. If the file does not have an
        externsion, this method will test for files with that base name with
        all the extensions it can read.

        Args:
            filename: Full absolute path of a file to check, with or without
                an extension.

        Returns:
            False if a file is not found.
            Tuple of (full file with path, extension) if a file is found

        """
        if not os.path.splitext(filename)[1]:
            # file has no extension

            for extension in self.file_types:
                if os.path.isfile(filename + extension):
                    return os.path.abspath(filename + extension), extension
            else:
                return False, None
        else:
            return filename, os.path.splitext(filename)[1]

    @staticmethod
    def get_config_file_version(self, filename):
        """Gets the config version number from a file. Since this technique
        varies depending on the file type, it needs to be implemented in the
        chile class

        Args:
            filename: The file with path to check.

        Returns:
            An int of the config file version

        """
        raise NotImplementedError

    def load(self, filename, verify_version=True):
        raise NotImplementedError

    def save(self, filename, data):
        raise NotImplementedError


class FileManager(object):

    log = logging.getLogger('FileManager')
    file_interfaces = dict()

    @classmethod
    def init(cls):
        # Needs to be a separate method to prevent circular import
        for module in mpf.file_interfaces.__all__:

                __import__('mpf.file_interfaces.{}'.format(module))

                interface_class = eval(
                    'mpf.file_interfaces.{}.file_interface_class'.format(module))

                this_instance = interface_class()

                for file_type in interface_class.file_types:
                    cls.file_interfaces[file_type] = this_instance

    @staticmethod
    def locate_file(filename):
        ext = os.path.splitext(filename)[1]

        if not os.path.isfile(filename):
            # If the file doesn't have an extension, let's see if we can find
            # one
            if not ext:
                for config_processor in set(FileManager.file_interfaces.values()):
                    questionable_file, ext = config_processor.find_file(filename)
                    if questionable_file:
                        return questionable_file

                return False

        else:
            return filename

    @staticmethod
    def get_file_interface(filename):
        file = FileManager.locate_file(filename)
        ext = os.path.splitext(filename)[1]

        if file:
            try:
                return FileManager.file_interfaces[ext]
            except KeyError:
                return None

    @staticmethod
    def load(filename, verify_version=False):

        file = FileManager.locate_file(filename)

        if file:
            ext = os.path.splitext(file)[1]

            try:
                config = FileManager.file_interfaces[ext].load(file, verify_version)
            except KeyError:
                # todo convert to exception
                FileManager.log.error("No config file processor available for file type {}"
                          .format(ext))
                sys.exit()

            return config

        else:
            print "Could not locate file:", filename

    @staticmethod
    def save(filename, data):
        ext = os.path.splitext(filename)[1]

        try:
            FileManager.file_interfaces[ext].save(filename, data)
        except KeyError:
            # todo convert to exception
            FileManager.log.error("No config file processor available for file type {}"
                      .format(ext))
            sys.exit()