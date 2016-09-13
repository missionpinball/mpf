"""Contains the DataManager base class."""

import copy
import logging
import os
import errno
import _thread
import threading

from mpf.core.file_manager import FileManager


class DataManager(object):

    """Handles key value data loading and saving for the machine."""

    def __init__(self, machine, name):
        """Initialise data manger.

        The DataManager is responsible for reading and writing data to/from a
        file on disk.

        Args:
            machine: The main MachineController instance.
            name: A string name that represents what this DataManager instance
                is for. This name is used to lookup the configuration option
                in the machine config in the mpf:paths:<name> location. That's
                how you specify the file name this DataManager will use.
        """
        self.machine = machine
        self.name = name
        self.filename = os.path.join(self.machine.machine_path,
                                     self.machine.config['mpf']['paths'][name])

        self.log = logging.getLogger('DataInterface')

        self.data = dict()
        self._dirty = threading.Event()

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
        self.log.debug("Loading %s from %s", self.name, self.filename)
        if os.path.isfile(self.filename):
            self.data = FileManager.load(self.filename, halt_on_error=False)

        else:
            self.log.debug("Didn't find the %s file. No prob. We'll create "
                           "it when we save.", self.name)

    def get_data(self, section=None):
        """Return the value of this DataManager's data.

        Args:
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
        else:
            return dict()

    def save_all(self, data=None, delay_secs=0):
        """Write this DataManager's data to the disk.

        Args:
            data: An optional dict() of the data you want to write. If None
                then it will write the data as it exists in its own data
                attribute.
            delay_secs: Optional integer value of the amount of time you want
                to wait before the disk write occurs. Useful for writes that
                occur when MPF is busy, so you can delay them by a few seconds
                so they don't slow down MPF. Default is 0.
        """
        self.log.debug("Will write %s to disk in %s sec(s)", self.name,
                       delay_secs)

        if data:
            self.data = data

        if delay_secs:
            self.machine.delay.add(callback=self._delayed_save_callback,
                                   ms=delay_secs * 1000)
        else:
            self._dirty.set()

    def _delayed_save_callback(self):
        self._dirty.set()

    def save_key(self, key, value, delay_secs=0):
        """Update an individual key and then write the entire dictionary to disk.

        Args:
            key: String name of the key to add/update.
            value: Value of the key
            delay_secs: Optional number of seconds to wait before writing the
                data to disk. Default is 0.
        """
        try:
            self.data[key] = value
        except TypeError:
            self.log.warning('In-memory copy of %s is invalid. Re-creating', self.filename)
            # todo should we reload from disk here?
            self.data = dict()
            self.data[key] = value

        self.save_all(delay_secs=delay_secs)

    def remove_key(self, key):
        """Remove key by name."""
        try:
            del self.data[key]
            self.save_all()
        except KeyError:
            pass

    def _writing_thread(self):  # pragma: no cover
        while not self.machine.thread_stopper.is_set():
            if not self._dirty.wait(1):
                continue
            self._dirty.clear()

            data = copy.deepcopy(self.data)
            self.log.debug("Writing %s to: %s", self.name, self.filename)
            # save data
            FileManager.save(self.filename, data)
