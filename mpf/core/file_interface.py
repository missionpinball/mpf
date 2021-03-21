"""Interface for config file loaders."""
import logging
import os
from typing import Union, Tuple, Optional

MYPY = False
if MYPY:    # pragma: no cover
    from typing import List     # pylint: disable-msg=cyclic-import,unused-import


class FileInterface:

    """Interface for config files."""

    __slots__ = ["log"]

    file_types = list()     # type: List[str]

    def __init__(self):
        """Initialise file manager."""
        self.log = logging.getLogger('{} File Interface'.format(
            self.file_types[0][1:].upper()))

    def find_file(self, filename) -> Tuple[Optional[str], Optional[str]]:
        """Test whether the passed file is valid.

        If the file does not have an externsion, this method will test for files with that base name with
        all the extensions it can read.

        Args:
        ----
            filename: Full absolute path of a file to check, with or without
                an extension.

        Returns false if a file is not found. Tuple of (full file with path, extension) if a file is found.
        """
        if not os.path.splitext(filename)[1]:
            # file has no extension

            for extension in self.file_types:
                if os.path.isfile(filename + extension):
                    return os.path.abspath(filename + extension), extension
            return None, None

        return filename, os.path.splitext(filename)[1]

    def load(self, filename, expected_version_str=None, halt_on_error=True):
        """Load file."""
        raise NotImplementedError

    def save(self, filename, data):
        """Save file."""
        raise NotImplementedError
