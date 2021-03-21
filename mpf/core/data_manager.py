"""Contains the DataManager base class."""

import copy
import os
import errno
import threading
import time
import _thread

from mpf.core.file_manager import FileManager
from mpf.core.mpf_controller import MpfController


class DataManager(MpfController):

    """Handles key value data loading and saving for the machine."""

    config_name = "data_manager"

    __slots_ = ["name", "min_wait_secs", "filename", "data", "_dirty"]

    def __init__(self, machine, name, min_wait_secs=1):
        """Initialise data manger.

        The DataManager is responsible for reading and writing data to/from a
        file on disk.

        Args:
        ----
            machine: The main MachineController instance.
            name: A string name that represents what this DataManager instance
                is for. This name is used to lookup the configuration option
                in the machine config in the mpf:paths:<name> location. That's
                how you specify the file name this DataManager will use.
            min_wait_secs: Minimal seconds to wait between two writes.
        """
        super().__init__(machine)
        self.name = name
        self.min_wait_secs = min_wait_secs
        config_path = self.machine.config['mpf']['paths'][name]
        if config_path is False:
            self.filename = False
        elif isinstance(config_path, str) and config_path.startswith("/"):
            self.filename = config_path
        elif isinstance(config_path, str):
            self.filename = os.path.join(self.machine.machine_path,
                                         self.machine.config['mpf']['paths'][name])
        else:
            raise AssertionError("Invalid path {} for {}".format(config_path, name))

        self.data = dict()
        self._dirty = threading.Event()

        if self.filename:
            self._setup_file()

            _thread.start_new_thread(self._writing_thread, ())

    def _setup_file(self):
        self._make_sure_path_exists(os.path.dirname(self.filename))

        self._load()

    @classmethod
    def _make_sure_path_exists(cls, path):
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

    def _load(self):
        self.debug_log("Loading %s from %s", self.name, self.filename)
        if os.path.isfile(self.filename):
            self.data = FileManager.load(self.filename, halt_on_error=False)

        else:
            self.debug_log("Didn't find the %s file. No prob. We'll create "
                           "it when we save.", self.name)

        if not self.data:
            self.data = {}

    def get_data(self, section=None):
        """Return the value of this DataManager's data.

        Args:
        ----
            section: Optional string name of a section (dictionary key) for the
                data you want returned. Default is None which returns the
                entire dictionary.
        """
        if not section:
            data = copy.copy(self.data)
        else:

            try:
                data = copy.copy(self.data[section])
            except (KeyError, TypeError):
                data = dict()

        if isinstance(data, dict):
            return data

        return dict()

    def _trigger_save(self):
        """Trigger a write of this DataManager's data to the disk."""
        self.debug_log("Will write %s to disk", self.name)
        self._dirty.set()

    def save_all(self, data):
        """Update all data."""
        self.data = data
        self._trigger_save()

    def _writing_thread(self):  # pragma: no cover
        # prevent early writes at start-up
        time.sleep(self.min_wait_secs)
        while not self.machine.thread_stopper.is_set():
            if not self._dirty.wait(1):
                continue
            self._dirty.clear()

            data = copy.deepcopy(self.data)
            self.debug_log("Writing %s to: %s", self.name, self.filename)
            # save data
            FileManager.save(self.filename, data)
            # prevent too many writes
            time.sleep(self.min_wait_secs)

        # if dirty write data one last time during shutdown
        if self._dirty.is_set():
            FileManager.save(self.filename, data)
