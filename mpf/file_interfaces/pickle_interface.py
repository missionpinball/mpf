"""File interface for pickled binary files."""
from typing import List

import pickle

from mpf.core.file_interface import FileInterface


class PickleInterface(FileInterface):

    """Loads and saves pickled binary files."""

    __slots__ = []  # type: List[str]

    file_types = ['.bin']

    def load(self, filename, expected_version_str=None, halt_on_error=True):
        """Load data from binary file."""
        del expected_version_str
        self.log.info("Loading %s", filename)
        try:
            with open(filename, "rb") as f:
                return pickle.load(f)
        except Exception:   # pylint: disable-msg=broad-except
            if halt_on_error:
                raise
            return None

    def save(self, filename, data):
        """Save data to binary file."""
        with open(filename, "wb") as f:
            pickle.dump(data, f)
