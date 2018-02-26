"""Contains the FileManager and FileInterface base classes."""

import logging
import os
import importlib

from typing import Dict
from typing import List

import mpf.file_interfaces


class FileInterface(object):

    """Interface for config files."""

    file_types = list()     # type: List[str]

    def __init__(self):
        """Initialise file manager."""
        self.log = logging.getLogger('{} File Interface'.format(
            self.file_types[0][1:].upper()))

    def find_file(self, filename):
        """Test whether the passed file is valid.

        If the file does not have an externsion, this method will test for files with that base name with
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
            return False, None
        else:
            return filename, os.path.splitext(filename)[1]

    def load(self, filename, expected_version_str=None, halt_on_error=True):
        """Load file."""
        raise NotImplementedError

    def save(self, filename, data):
        """Save file."""
        raise NotImplementedError


class FileManager(object):

    """Manages file interfaces."""

    log = logging.getLogger('FileManager')
    file_interfaces = dict()    # type: Dict[str, FileInterface]
    initialized = False

    @classmethod
    def init(cls):
        """Initialise file manager."""
        # Needs to be a separate method to prevent circular import
        for module_name in mpf.file_interfaces.__all__:
            importlib.import_module('mpf.file_interfaces.{}'.format(module_name))
            module_obj = getattr(mpf.file_interfaces, module_name)
            interface_class = getattr(module_obj, "file_interface_class")

            this_instance = interface_class()

            for file_type in interface_class.file_types:
                cls.file_interfaces[file_type] = this_instance

        FileManager.initialized = True

    @staticmethod
    def locate_file(filename) -> str:
        """Find a file location.

        Args:
            filename: Filename to locate

        Returns: Location of file
        """
        if not filename:
            raise FileNotFoundError("No filename provided")

        if not FileManager.initialized:
            FileManager.init()

        ext = os.path.splitext(filename)[1]

        if not os.path.isfile(filename):
            # If the file doesn't have an extension, let's see if we can find
            # one
            if not ext:
                for config_processor in set(FileManager.file_interfaces.values()):
                    questionable_file, ext = config_processor.find_file(filename)
                    if questionable_file:
                        return questionable_file

            raise FileNotFoundError("File not found: {}".format(filename))

        else:
            return filename

    @staticmethod
    def get_file_interface(filename):
        """Return a file interface."""
        try:
            FileManager.locate_file(filename)
        except FileNotFoundError:
            return None

        ext = os.path.splitext(filename)[1]

        try:
            return FileManager.file_interfaces[ext]
        except KeyError:
            return None

    @staticmethod
    def load(filename, verify_version=False, halt_on_error=True):
        """Load a file by name."""
        if not FileManager.initialized:
            FileManager.init()

        try:
            file = FileManager.locate_file(filename)
        except FileNotFoundError:
            if halt_on_error:
                raise IOError("Could not find file {}".format(filename))
            else:
                return dict()

        if not file and halt_on_error:
            raise IOError(
                "Could not find file '{}'. Resolved abs path to {}".format(
                    filename, os.path.abspath(filename)))

        ext = os.path.splitext(file)[1]

        try:
            interface = FileManager.file_interfaces[ext]
        except KeyError:
            raise AssertionError("No config file processor available for file type {}".format(ext))

        return interface.load(file, verify_version, halt_on_error)

    @staticmethod
    def save(filename, data):
        """Save data to file."""
        ext = os.path.splitext(filename)[1]

        # save to temp file and move afterwards. prevents broken files
        temp_file = os.path.dirname(filename) + os.sep + "_" + os.path.basename(filename)

        try:
            FileManager.file_interfaces[ext].save(temp_file, data)
        except KeyError:
            raise AssertionError("No config file processor available for file type {}".format(ext))

        # move temp file
        os.replace(temp_file, filename)
