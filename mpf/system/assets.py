"""Contains AssetManager, AssetLoader, and Asset parent classes"""
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
import sys
import traceback

from mpf.system.config import CaseInsensitiveDict


class AssetManager(object):
    """Base class for an Asset Manager.

    Args:
        machine: The main ``MachineController`` object.
        config_section: String of the name of the section in the config file
            for the asset settings that this Asset Manager will machine. e.g.
            'image'.
        path_string: The setting in the paths section of the config file that
            specifies what path these asset files are in. e.g. 'images'.
        asset_class: A class object of the base class for the assets that this
            Asset Manager will manage. e.g. Image.
        asset_attribute: The string name that you want to refer to this asset
            collection as. e.g. a value of 'images' means that assets will be
            accessible via ``self.machine.images``.
        file_extensions: A tuple of strings of valid file extensions that files
            for this asset will use. e.g. ``('png', 'jpg', 'jpeg', 'bmp')``

    There will be one Asset Manager for each different type of asset. (e.g. one
    for images, one for movies, one for sounds, etc.)
    """

    assets_to_load = 0
    total_assets = 0

    @classmethod
    def add_asset_to_load(cls):
        AssetManager.assets_to_load += 1
        AssetManager.total_assets += 1

    @classmethod
    def remove_asset_to_load(cls):
        AssetManager.assets_to_load -= 1

    def __init__(self, machine, config_section, path_string, asset_class,
                 asset_attribute, file_extensions):

        self.log = logging.getLogger(config_section + ' Asset Manager')
        self.log.debug("Initializing...")

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
            setattr(self.machine, asset_attribute, CaseInsensitiveDict())

        self.asset_list = getattr(self.machine, asset_attribute)

        self.create_loader_thread()

        self.machine.mode_controller.register_load_method(self.load_assets,
                                                self.config_section,
                                                load_key='preload')

        self.machine.mode_controller.register_start_method(self.load_assets,
                                                 self.config_section,
                                                 load_key='mode_start')

        # register & load systemwide assets
        self.machine.events.add_handler('init_phase_4',
                                        self.register_and_load_machine_assets)

        self.defaults = self.setup_defaults(self.machine.config)

    def process_assets_from_disk(self, config, path=None):
        """Looks at a path and finds all the assets in the folder.
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
                in's asset_defaults settings.)
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

        self.log.debug("Processing assets from base folder: %s", root_path)

        for path, _, files in os.walk(root_path, followlinks=True):

            valid_files = [f for f in files if f.endswith(self.file_extensions)]

            for file_name in valid_files:
                folder = os.path.basename(path)
                name = os.path.splitext(file_name)[0].lower()
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

                    if ('file' in v and v['file'] == file_name) or name == k:
                        if name != k:
                            name = k
                            #print "NEW NAME:", name
                        built_up_config.update(config[k])
                        break

                built_up_config['file'] = full_file_path

                config[name] = built_up_config

                self.log.debug("Registering Asset: %s, File: %s, Default Group:"
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

        self.log.debug("Registering machine-wide %s", self.config_section)

        if self.config_section in self.machine.config:
            config = self.machine.config[self.config_section]
        else:
            config = None

        self.machine.config[self.config_section] = self.register_assets(
            config=config)

        self.log.debug("Loading machine-wide 'preload' %s", self.config_section)

        # Load preload systemwide assets
        self.load_assets(self.machine.config[self.config_section],
                         load_key='preload')

    def setup_defaults(self, config):
        """Processed the ``asset_defaults`` section of the machine config
        files.

        """

        default_config_dict = dict()

        if 'asset_defaults' in config and config['asset_defaults']:

            if (self.config_section in config['asset_defaults'] and
                    config['asset_defaults'][self.config_section]):

                this_config = config['asset_defaults'][self.config_section]

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
                                         queue=self.loader_queue,
                                         machine=self.machine)
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

            self.register_asset(asset=asset.lower(),
                                config=config[asset])

        return config

    def load_assets(self, config, mode=None, load_key=None, callback=None,
                    **kwargs):
        """Loads the assets from a config dictionary.

        Args:
            config: Dictionary that holds the assets to load.
            mode: Not used. Included here since this method is registered as a
                mode start handler.
            load_key: String name of the load key which specifies which assets
                should be loaded.
            callback: Callback method which is called by each asset once it's
                loaded.
            **kwargs: Not used. Included to allow this method to be used as an
                event handler.

        The assets must already be registered in order for this method to work.

        """
        # actually loads assets from a config file. Assumes that they've
        # aleady been registered.

        asset_set = set()

        for asset in config:
            if self.asset_list[asset].config['load'] == load_key:
                self.asset_list[asset].load(callback=callback)
                asset_set.add(self.asset_list[asset])

        return self.unload_assets, asset_set

    def register_asset(self, asset, config):
        """Registers an asset with the Asset Manager.

        Args:
            asset: String name of the asset to register.
            config: Dictionary which contains settings for this asset.

        Registering an asset is what makes it available to be used in the game.
        Note that registering an asset is separate from loading an asset. All
        assets will be registered on MPF boot, but they can be loaded and
        unloaded as needed to save on memory.

        """

        #file_name = self.locate_asset_file(config['file'], path)
        #
        ## get the defaults based on the path name
        #this_config = copy.deepcopy(self.defaults[default_config_name])
        #this_config.update(config)

        self.asset_list[asset] = self.asset_class(self.machine, config,
                                                  config['file'], self)

    def unload_assets(self, asset_set):
        """Unloads assets from memory.

        Args:
            asset_set: A set (or any iterable) of Asset objects which will be
                unloaded.

        Unloading an asset does not de-register it. It's still available to be
        used, but it's just unloaded from memory to save on memory.

        """
        for asset in asset_set:
            self.log.debug("Unloading asset: %s", asset.file_name)
            asset.unload()

    def load_asset(self, asset, callback, priority=10):
        """Loads an asset into memory.

        Args:
            asset: The Asset object to load.
            callback: The callback that will be called once the asset has been
                loaded by the loader thread.
            priority: The relative loading priority of the asset. If there's a
                queue of assets waiting to be loaded, this load request will be
                inserted into the queue in a position based on its priority.

        """
        self.loader_queue.put((-priority, asset, callback))
        # priority above is negative so this becomes a LIFO queue
        self.log.debug("Adding %s to loader queue at priority %s. New queue "
                       "size: %s", asset, priority, self.loader_queue.qsize())
        AssetManager.add_asset_to_load()

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
    """Base class for the Asset Loader with runs as a separate thread and
    actually loads the assets from disk.

    Args:
        name: String name of what this loader will be called. (Only really used
            to give a friendly name to it in logs.)
        queue: A reference to the asset loader ``Queue`` which holds assets
            waiting to be loaded.
        machine: The main ``MachineController`` object.

    """

    def __init__(self, name, queue, machine):

        threading.Thread.__init__(self)
        self.log = logging.getLogger(name + ' Asset Loader')
        self.queue = queue
        self.machine = machine

    def run(self):
        """Run loop for the loader thread."""

        try:
            while True:
                asset = self.queue.get()

                if not asset[1].loaded:
                    self.log.debug("Loading Asset: %s. Callback: %s", asset[1],
                                   asset[2])
                    asset[1].do_load(asset[2])
                    self.log.debug("Asset Finished Loading: %s. Remaining: %s",
                                   asset[1], self.queue.qsize())

                # If the asset is already loaded and we don't need to load it
                # again, we still need to call the callback.
                elif asset[2]:
                    self.log.debug("Calling callback for asset %s since it's "
                                   "already loaded. Callback: %s", asset[1],
                                   asset[2])
                    asset[2]()

                AssetManager.remove_asset_to_load()

                # If the asset is already loaded, just ignore it and move on.
                # I thought about trying to make sure that an asset isn't
                # in the queue before it gets added. But since this is separate
                # threads that would require all sorts of work. It's actually
                # more efficient to add it to the queue anyway and then just
                # skip it if it's already loaded by the time the loader gets to
                # it.

        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            msg = ''.join(line for line in lines)
            self.machine.crash_queue.put(msg)


class Asset(object):

    def __init__(self, machine, config, file_name, asset_manager):
        self.machine = machine
        self.config = config
        self.file_name = file_name
        self.asset_manager = asset_manager
        self.loaded = False

        self._initialize_asset()

    # def __repr__(self):
    #
    #     if self.file_name:
    #         return self.file_name
    #     else:
    #         return self

    def load(self, callback=None):
        self.asset_manager.load_asset(self, callback)

    def do_load(self, callback):
        pass

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
