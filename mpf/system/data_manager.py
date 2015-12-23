"""Contains the DataManager base class."""
# data_manager.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import copy
import logging
import os
import errno
import thread
import time

from mpf.system.file_manager import FileManager


class DataManager(object):

    def __init__(self, machine, name):
        """
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

        self._setup_file()

    def _setup_file(self):
        self._make_sure_path_exists(os.path.dirname(self.filename))

        self._load()

    def _make_sure_path_exists(self, path):
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
        """Returns the value of this DataManager's data.

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
        """Writes this DataManager's data to the disk.

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
                                   data=copy.deepcopy(self.data),
                                   ms=delay_secs*1000)
        else:
            thread.start_new_thread(self._writing_thread, (copy.deepcopy(self.data), ))

    def _delayed_save_callback(self, data):
        thread.start_new_thread(self._writing_thread, (data, ))

    def save_key(self, key, value, delay_secs=0):
        """Updates an individual key and then writes the entire dictionary to
        disk.

        Args:
            key: String name of the key to add/update.
            value: Value of the key
            delay_secs: Optional number of seconds to wait before writing the
                data to disk. Default is 0.

        """
        try:
            self.data[key] = value
        except TypeError:
            self.log.warning('In-memory copy of {} is invalid. Re-creating'.
                             format(self.filename))
            # todo should we reload from disk here?
            self.data = dict()
            self.data[key] = value

        self.save_all(delay_secs=delay_secs)

    def remove_key(self, key):
        try:
            del self.data[key]
            self.save_all()
        except KeyError:
            pass

    def _writing_thread(self, data):
        self.log.debug("Writing {} to: {}".format(self.name, self.filename))
        FileManager.save(self.filename, data)


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