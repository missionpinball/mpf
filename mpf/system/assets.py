"""Contains AssetManager and Asset parent classes"""
# assets.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import os
import threading
import copy
from Queue import PriorityQueue


class AssetManager(object):

    def __init__(self, machine, config_section, path_string, asset_class,
                 asset_attribute, file_extensions):

        self.log = logging.getLogger(config_section + ' Asset Manager')
        self.log.info("Initializing...")

        self.machine = machine
        self.max_memory = None
        self.registered_assets = set()
        self.path_string = path_string
        self.config_section = config_section
        self.asset_class = asset_class
        self.file_extensions = file_extensions
        self.loader_queue = PriorityQueue()
        self.loader_thread = None

        self.machine.asset_managers[config_section] = self

        if not hasattr(self.machine, asset_attribute):
            setattr(self.machine, asset_attribute, dict())

        self.asset_list = getattr(self.machine, asset_attribute)

        self.create_loader_thread()

        self.machine.modes.register_load_method(self.load_assets,
                                                self.config_section,
                                                load_key='preload')

        self.machine.modes.register_start_method(self.load_assets,
                                                 self.config_section,
                                                 load_key='mode_start')

        # register & load systemwide assets
        self.machine.events.add_handler('machine_init_phase_4',
            self.register_and_load_machine_assets)

        self.defaults = self.setup_defaults(self.machine.config)

    def process_assets_from_disk(self, config, path=None):
        """ Looks at a path and finds all the assets in the folder.
        Looks in a subfolder based on the asset's path string.
        Crawls subfolders too. The first subfolder it finds is used for the
        asset's default config section.
        If an asset has a related entry in the config file, it will create
        the asset with that config. Otherwise it uses the default

        Args:
            config: A dictionary which contains a list of asset names with
                settings that will be used for the specific asset. (Note this
                is not needed for all assets, as any asset file found not in the
                config dictionary will be set up with the folder it was found
                in's AssetDefaults settings.)
            path: A full system path to the root folder that will be searched
                for assetsk. This should *not* include the asset-specific path
                string. If omitted, only the machine's root folder will be
                searched.
        """

        if not path:
            path = self.machine.machine_path

        if not config:
            config = dict()

        root_path = os.path.join(path, self.path_string)

        self.log.info("Processing assets from base folder: %s", root_path)

        for path, _, files in os.walk(root_path, followlinks=True):

            valid_files = [f for f in files if f.endswith(self.file_extensions)]

            for file_name in valid_files:
                folder = os.path.basename(path)
                name = os.path.splitext(file_name)[0]
                full_file_path = os.path.join(path, file_name)

                if folder == self.path_string or folder not in self.defaults:
                    default_string = 'default'
                else:
                    default_string = folder

                #print "------"
                #print "path:", path
                #print "full_path", full_file_path
                #print "file:", file_name
                #print "name:", name
                #print "folder:", folder
                #print "default settings name:", default_string
                #print "default settings:", self.defaults[default_string]

                built_up_config = copy.deepcopy(self.defaults[default_string])

                for k, v in config.iteritems():
                    if v['file'] == file_name:
                        if name != k:
                            name = k
                            #print "NEW NAME:", name
                        built_up_config.update(config[k])
                        break

                built_up_config['file'] = full_file_path

                config[name] = built_up_config

                self.log.info("Registering Asset: %s, File: %s, Default Group:"
                              " %s, Final Config: %s", name, file_name,
                              default_string, built_up_config)

        return config

    def register_and_load_machine_assets(self):
        """Called on MPF boot to register any assets found in the machine-wide
        configuration files. (i.e. any assets not specified in mode config
        files.)

        If an asset is set with the load type of 'preload', this method will
        also load the asset file into memory.
        """

        self.log.info("Registering machine-wide %s", self.config_section)

        if self.config_section in self.machine.config:
            config = self.machine.config[self.config_section]
        else:
            config = None

        self.machine.config[self.config_section] = self.register_assets(
            config=config)

        self.log.info("Loading machine-wide 'preload' %s", self.config_section)

        # Load preload systemwide assets
        self.load_assets(self.machine.config[self.config_section],
                         load_key='preload')

    def setup_defaults(self, config):
        """Processed the `AssetDefaults` section of the machine config files."""

        default_config_dict = dict()

        if 'AssetDefaults' in config and config['AssetDefaults']:

            if (self.config_section in config['AssetDefaults'] and
                config['AssetDefaults'][self.config_section]):

                this_config = config['AssetDefaults'][self.config_section]

                # set the default
                default_config_dict['default'] = this_config.pop('default')

                for default_section_name in this_config:

                    # first get a copy of the default for this section
                    default_config_dict[default_section_name] = (
                        copy.deepcopy(default_config_dict['default']))

                    # then merge in this section's specific settings
                    default_config_dict[default_section_name].update(
                        this_config[default_section_name])

        return default_config_dict

    def create_loader_thread(self):
        """Creates a loader thread which will handle the actual reading from
        disk and loading into memory for assets of this class. Note that one
        loader thread is created for each class of assets used in your game.

        Note that this asset loader as a separate *thread*, not a separate
        *process*. It will run on the same core as your main MPF Python
        instance.

        Note that it's possible to call this method multiple times to create
        multiple loader threads, but that will not make things load any faster
        since this process is limited by CPU and disk I/O. In fact if it's a
        magnetic disk, think multiple threads would make it slower.
        """

        self.loader_thread = AssetLoader(name=self.config_section,
                                         queue=self.loader_queue)
        self.loader_thread.daemon = True
        self.loader_thread.start()

    def register_assets(self, config, mode_path=None):
        """Scans a config dictionary and registers any asset entries it finds.

            Args:
                config: A dictionary of asset entries. This dictionary needs to
                    be "localized" to just the section for this particular
                    asset type. e.g. if you're loading "Images" the keys of this
                    dictionary should be image_1, image_2, etc., not "Images".
                mode_path: The full path to the base folder that will be
                    seaerched for the asset file on disk. This folder should
                    *not* include the asset-specific folder. If omitted, the
                    base machine folder will be searched.

        Note that this method merely registers the assets so they can be
        referenced in MPF. It does not actually load the asset files into
        memory.
        """

        # config here is already localized

        config = self.process_assets_from_disk(config=config, path=mode_path)

        for asset in config:

            if not os.path.isfile(config[asset]['file']):
                config[asset]['file'] = self.locate_asset_file(
                    file_name=config[asset]['file'],
                    path=mode_path)

            self.register_asset(asset=asset,
                                config=config[asset])

        return config

    def load_assets(self, config, load_key=None, **kwargs):
        # actually loads assets from a config file. Assumes that they've
        # aleady been registered.

        asset_set = set()

        for asset in config:
            if self.asset_list[asset].config['load'] == load_key:
                self.asset_list[asset].load()
                asset_set.add(self.asset_list[asset])

        return self.unload_assets, asset_set

    def register_asset(self, asset, config):

        #file_name = self.locate_asset_file(config['file'], path)
        #
        ## get the defaults based on the path name
        #this_config = copy.deepcopy(self.defaults[default_config_name])
        #this_config.update(config)

        self.asset_list[asset] = self.asset_class(self.machine, config,
                                                  config['file'], self)

    def unload_assets(self, asset_set):
        for asset in asset_set:
            self.log.info("Unloading asset: %s", asset.file_name)
            asset.unload()

    def load_asset(self, asset, callback, priority=10):
        self.loader_queue.put((-priority, asset, callback))
        # priority above is negative so this becomes a LIFO queue
        self.log.debug("Adding asset to loader queue at priority %s. New queue "
                       "size: %s", priority, self.loader_queue.qsize())

    def locate_asset_file(self, file_name, path=None):
        """Takes a file name and a root path and returns a link to the absolute
        path of the file

        Args:
            file_name: String of the file name
            path: root of the path to check (without the specific asset path
                string)

        Returns: String of the full path (path + file name) of the asset.

        Note this method will add the path string between the path you pass and
        the file. Also if it can't find the file in the path you pass, it will
        look for the file in the machine root plus the path string location.

        """

        if path:
            path_list = [path]
        else:
            path_list = list()

        path_list.append(self.machine.machine_path)

        for path in path_list:

            full_path = os.path.join(path, self.path_string, file_name)
            if os.path.isfile(full_path):
                return full_path

        self.log.critical("Could not locate asset file '%s'. Quitting...",
                          file_name)
        raise Exception()


class AssetLoader(threading.Thread):

    def __init__(self, name, queue):

        threading.Thread.__init__(self)
        self.log = logging.getLogger(name + ' Asset Loader')
        self.queue = queue

    def run(self):

        while 1:
            asset = self.queue.get()
            self.log.info("Loading Asset: '%s'. Callback: %s", asset[1],
                          asset[2])

            if not asset[1].loaded:
                asset[1]._load(asset[2])
                self.log.info("Asset Finished Loading: %s", asset[1])
            else:
                self.log.error("Received request to load %s, but it's already"
                               " loaded", asset[1])


class Asset(object):

    def __init__(self, machine, config, file_name, asset_manager):
        self.machine = machine
        self.config = config
        self.file_name = file_name
        self.asset_manager = asset_manager
        self.loaded = False

        self._initialize_asset()

    def __str__(self):
        return self.file_name

    def load(self, callback=None):
        self.asset_manager.load_asset(self, callback)

    def unload(self):
        self._unload()
        self.loaded = False

        # todo also check the loader queue to remove this asset from there



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
