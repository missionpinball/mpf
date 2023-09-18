"""Contains the FileManager base classes."""

import logging
import os

from mpf.file_interfaces.pickle_interface import PickleInterface
from mpf.file_interfaces.yaml_interface import YamlInterface

MYPY = False
if MYPY:    # pragma: no cover
    from typing import Dict, List  # pylint: disable-msg=cyclic-import,unused-import


class FileManager:

    """Manages file interfaces."""

    __slots__ = []  # type: List[str]

    log = logging.getLogger('FileManager')
    file_interfaces = dict()    # type: Dict[str, YamlInterface]
    initialized = False

    @classmethod
    def init(cls):
        """initialize file interfaces."""
        cls.file_interfaces[".yaml"] = YamlInterface()
        cls.file_interfaces[".bin"] = PickleInterface()

        FileManager.initialized = True

    @staticmethod
    def locate_file(filename) -> str:
        """Find a file location.

        Args:
        ----
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
                    if isinstance(questionable_file, str):
                        return questionable_file

            raise FileNotFoundError("File not found: {}".format(filename))

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
                raise OSError("Could not find file {}".format(filename))

            return dict()

        if not file and halt_on_error:
            raise OSError(
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
        if not FileManager.initialized:
            FileManager.init()

        ext = os.path.splitext(filename)[1]

        # save to temp file and move afterwards. prevents broken files
        temp_file = os.path.dirname(filename) + os.sep + "_" + os.path.basename(filename)

        try:
            FileManager.file_interfaces[ext].save(temp_file, data)
        except KeyError:
            raise AssertionError("No config file processor available for file type {}".format(ext))

        # move temp file
        os.replace(temp_file, filename)
