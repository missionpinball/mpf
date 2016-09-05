"""Contains AssetManager, AssetLoader, and Asset parent classes."""
import copy
import logging
import os
import random
import threading
from collections import deque

import asyncio

from mpf.core.case_insensitive_dict import CaseInsensitiveDict
from mpf.core.mpf_controller import MpfController
from mpf.core.utility_functions import Util


class BaseAssetManager(MpfController):

    """Base class for the Asset Manager.

    Args:
        machine: The machine controller
    """

    def __init__(self, machine):
        """Initialise asset manager."""
        super().__init__(machine)
        self.log = logging.getLogger('AssetManager')
        self.log.debug("Initializing...")

        self.machine.register_boot_hold('assets')

        self._asset_classes = list()
        # List of dicts, with each dict being an asset class. See
        # register_asset_class() method for details.

        self.num_assets_to_load = 0
        # Total number of assets that are/will be loaded. Used for
        # calculating progress. Reset to 0 when num_assets_loaded matches it.

        self.num_assets_loaded = 0
        # Number of assets loaded so far. Reset to 0 when it hits
        # num_assets_to_load.

        self.num_bcp_assets_to_load = 0
        self.num_bcp_assets_loaded = 0

        self._next_id = 0
        # id of next asset

        self.machine.mode_controller.register_start_method(
            start_method=self._load_mode_assets)

        # Modes load in init_phase_1, so by 2 we have everything to create
        # the assets.
        self.machine.events.add_handler('init_phase_3', self._create_assets)

        # Picks up asset load information from connected BCP client(s)
        self.machine.events.add_handler('assets_to_load',
                                        self._bcp_client_asset_load)

    def get_next_id(self):
        """Return the next free id."""
        self._next_id += 1
        return self._next_id

    @property
    def loading_percent(self):
        """Return the percent of assets that are in the process of loading that have been loaded.

        This value is an integer between 0 and 100. It's reset
        when all the assets have been loaded, so it will go from 0 to 100 when
        MPF is starting up, and then go from 0 to 100 again when a mode starts,
        etc.

        Note that this percentage also includes asset loading status updates
        from a connected BCP client.
        """
        try:
            return round((self.num_assets_loaded +
                          self.num_bcp_assets_loaded) /
                         (self.num_assets_to_load +
                          self.num_bcp_assets_to_load) * 100)

        except ZeroDivisionError:
            return 100

    # pylint: disable-msg=too-many-arguments
    def register_asset_class(self, asset_class, attribute, config_section,
                             disk_asset_section,
                             path_string, extensions, priority,
                             pool_config_section):
        """Register a a type of assets to be controlled by the AssetManager.

        Args:
            asset_class: Reference to the class you want to register, based on
                mc.core.assets.Asset. e.g. mc.assets.images.ImageClass
            attribute: String of the name of the attribute dict that will be
                added to the main MpfMc instance. e.g. 'images' means that
                the dict of image names to image asset class instances will be
                at self.machine.images.
            config_section: String name of this assets section in the config
                files. e.g. 'images'
            disk_asset_section: String name of the section which holds settings
                for assets that are loaded from disk.
            path_string: String name of the setting from mpf-mc:paths: which
                controls the name of the folder that will hold this type of
                assets in the machine folder. e.g. 'images
            extensions: Tuple of strings, with no dots, of the types of file
                extensions that are valid for this type of asset. e.g. ('jpg',
                'gif', 'png')
            priority: Integer of the relative priority of this asset class as
                compared to other asset classes. This affects the order that
                asset objects are created and loaded (when there's a tie)
                because some asset classes depend on others to exist first.
                e.g. 'slide_shows' assets need 'images', 'videos', and 'sounds'
                to exist. Higher number is first.
            pool_config_section: String which specifies the config file
                section for associated asset groups.
        """
        if not hasattr(self.machine, attribute):
            # some assets of different classes use the same mc attribute, like
            # images and animated_images
            setattr(self.machine, attribute, CaseInsensitiveDict())

        ac = dict(attribute=attribute,
                  cls=asset_class,
                  path_string=path_string,
                  config_section=config_section,
                  disk_asset_section=disk_asset_section,
                  extensions=extensions,
                  priority=priority,
                  pool_config_section=pool_config_section,
                  defaults=dict())

        self._asset_classes.append(ac)
        self._asset_classes.sort(key=lambda x: x['priority'], reverse=True)
        self._set_asset_class_defaults(ac, self.machine.machine_config)

    @classmethod
    def _set_asset_class_defaults(cls, asset_class, config):
        # Creates the folder-based default configs for the asset class
        # starting with the default section and then created folder-specific
        # entries based on that. Just runs once on startup for each asset
        # class.
        default_config_dict = dict()

        if 'assets' in config and config['assets']:

            if (asset_class['disk_asset_section'] in config['assets'] and
                    config['assets'][asset_class['disk_asset_section']]):

                this_config = config['assets'][asset_class['disk_asset_section']]

                # set the default
                default_config_dict['default'] = this_config['default']

                for default_section_name in this_config:
                    # first get a copy of the default for this section
                    default_config_dict[default_section_name] = (
                        copy.deepcopy(default_config_dict['default']))

                    # then merge in this section's specific settings
                    default_config_dict[default_section_name].update(
                        this_config[default_section_name])

        asset_class['defaults'] = default_config_dict

    def _create_assets(self):
        # Called once on boot to create all the asset objects
        # Create the machine-wide assets

        self._create_assets_from_disk(config=self.machine.machine_config)
        self._create_asset_groups(config=self.machine.machine_config)

        # Create the mode assets
        for mode in self.machine.modes.values():
            self._create_assets_from_disk(config=mode.config, mode=mode)
            self._create_asset_groups(config=mode.config, mode=mode)

        # load the assets marked for preload:
        preload_assets = list()

        for ac in self._asset_classes:
            preload_assets.extend(
                [x for x in getattr(self.machine, ac['attribute']).values() if
                 x.config['load'] == 'preload'])

        for asset in preload_assets:
            asset.load()

        if not preload_assets:
            self.machine.clear_boot_hold('assets')

    def _create_assets_from_disk(self, config, mode=None):
        """Walk a folder (and subfolders) and finds all the assets.

        Check to see if those assets have config entries in the passed config file, and
        then builds a config for each asset based on its config entry, and/or
        defaults based on the subfolder it was in or the general defaults.
        Then it creates the asset objects based on the built-up config.

            Args:
                config: A config dictionary.
                mode: Optional reference to the mode object which is used when
                    assets are being created from mode folders.

            Returns: An updated config dictionary. (See the "How it works"
                section below for details.

        Note that this method merely creates the asset object so they can be
        referenced in MPF. It does not actually load the asset files into
        memory.

        It's called on startup register machine-wide assets, and it's called
        as modes initialize (also during the startup process) to find assets
        in mode folders.

        How it works
        ============

        Every asset class that's registered with the Asset Manager has a folder
        associated it. (e.g. Images assets as associated wit the "images"
        folder.)

        This method will build a master config dict of all the assets of each
        type. It does this by walking the folder, looking for files of each
        asset type.

        When it finds a file, it checks the config to see if either (1) any
        entries exist with a name that matches the root of that file name, or
        (2) to see if there's a config for an asset with a different name
        but with a file: setting that matches this file name.

        If it finds a match, that entry's file: setting is updated with the
        default settings for assets in that folder as well as the full path to
        the file. If it does not find a match, it creates a new entry for
        that asset in the config.

        To build up the config, it will base the config on any settings
        specified in the "default" section of the "assets:" section for that
        asset class. (e.g. images will get whatever key/value pairs are in the
        assets:images:default section of the config.)

        Then it will look to see what subfolder the asset it in and if there
        are any custom default settings for that subfolder. For example, an
        image found in the /custom1 subfolder will get any settings in the
        assets:images:custom1 section of the config. These settings are merged
        into the settings from the default section.

        Finally it will merge in any settings that existed for this asset
        specifically.

        When this method is done, the config dict has been updated to include
        every asset it found in that folder and subfolders (along with its
        full path), and a config dict appropriately merged from default,
        folder-specific, and asset specific settings
        """
        if not config:
            config = dict()

        try:
            mode_name = mode.name
            path = mode.path
        except AttributeError:
            mode_name = None
            path = self.machine.machine_path

        for ac in self._asset_classes:
            if ac['disk_asset_section'] not in config:
                config[ac['disk_asset_section']] = dict()

            # Populate the config section for this asset class with all the
            # assets found on disk
            config[ac['disk_asset_section']] = self._create_asset_config_entries(
                asset_class=ac,
                config=config[ac['disk_asset_section']],
                mode_name=mode_name,
                path=path)

            # create the actual instance of the Asset object and add it
            # to the self.machine asset attribute dict for that asset class
            for asset in config[ac['disk_asset_section']]:
                getattr(self.machine, ac['attribute'])[asset] = ac['cls'](
                    self.machine, name=asset,
                    file=config[ac['disk_asset_section']][asset]['file'],
                    config=config[ac['disk_asset_section']][asset])

        return config

    # pylint: disable-msg=too-many-locals
    def _create_asset_config_entries(self, asset_class, config, mode_name=None,
                                     path=None):
        """Scan a folder (and subfolders).

        Automatically creates or updates entries in the config dict for any asset files it finds.

        Args:
            asset_class: An asset class entry from the self._asset_classes
            dict.
            config: A dictionary which contains a list of asset names with
                settings that will be used for the specific asset. (Note this
                is not needed for all assets, as any asset file found not in
                the config dictionary will be set up with the folder it was
                found in's asset_defaults settings.)
            path: A full core path to the root folder that will be searched
                for assets. This should *not* include the asset-specific path
                string. If None, machine's root folder will be searched.

        Returns: Updated config dict that has all the new assets (and their
            built-up configs) that were found on disk.

        Note that for each file found, this method will scan through the
        entire config dict to see if any entry exists for that file based on an
        entry's 'file:' setting. If it's not found, an entry is created based
        on the file name. (This auto-created entry uses the lower-case stem of
        the file, e.g. a file called Image1.png will result in an asset entry
        called 'image1'.)

        Examples (based on images):

            asset_class defaults: section:
                default:
                    some_key: some_value
                foo:
                    some_key: some_value

            Based on the above asset_class defaults: section, the following
            files would get their 'defaults:' setting set to 'foo':
                /images/foo/image1.png
                /images/foo/bar/image2.png
                /images/foo/bar/bar2/image3.png

            And based on the above, the following files would get their
            'defaults:' setting set to 'default:
                /images/image4.png
                /images/foo/image5.png
                /images/other/images6.png
                /images/other/big/image7.png
        """
        if not path:
            path = self.machine.machine_path

        if not config:
            config = dict()

        root_path = os.path.join(path, asset_class['path_string'])
        self.log.debug("Processing assets from base folder: %s", root_path)

        for path, _, files in os.walk(root_path, followlinks=True):
            valid_files = [f for f in files if f.endswith(
                           asset_class['extensions'])]
            for file_name in valid_files:
                folder = os.path.basename(path)
                name = os.path.splitext(file_name)[0].lower()
                full_file_path = os.path.join(path, file_name)

                if folder == asset_class['path_string'] or folder not in asset_class['defaults']:
                    default_string = 'default'
                else:
                    default_string = folder

                # built_up_config is the built-up config dict for that will be
                # used for the entry for this asset.

                # first deepcopy the default config for this asset based
                # on its default_string (folder) since we use it as the base
                # for everything in case one of the custom folder configs
                # doesn't include all settings
                built_up_config = copy.deepcopy(
                    asset_class['defaults'][default_string])

                # scan through the existing config to see if this file is used
                # as the file setting for any entry.
                for k, v in config.items():
                    if ('file' in v and v['file'] == file_name) or name == k:
                        # if it's found, set the asset entry's name to whatever
                        # the name of this entry is
                        name = k
                        # merge in the config settings for this asset, updating
                        #  the defaults
                        built_up_config.update(config[k])
                        break

                # need to send the full file path to the Asset that will
                # be created so it will be able to load it later.
                built_up_config['file'] = full_file_path

                # If this asset is set to load on mode start, replace the load
                # value with one based on mode name
                if built_up_config['load'] == 'mode_start':
                    built_up_config['load'] = '{}_start'.format(mode_name)

                # Update the config for that asset
                config[name] = built_up_config

                self.log.debug("Registering Asset: %s, File: %s, Default "
                               "Group: %s, Final Config: %s", name, file_name,
                               default_string, built_up_config)
        return config

    def _create_asset_groups(self, config, mode=None):
        # creates named groups of assets and adds them to to the mc's asset
        # dicts
        del mode
        for ac in [x for x in self._asset_classes
                   if x['pool_config_section']]:

            if ac['pool_config_section'] in config:
                for name, settings in config[ac['pool_config_section']].items():
                    getattr(self.machine, ac['attribute'])[name] = (
                        ac['cls'].asset_group_class(self.machine, name, settings,
                                                    ac['cls']))

    def _load_mode_assets(self, config, priority, mode):
        # Called on mode start to load the assets that are set to automatically
        # load based on that mode starting
        del config
        return (self.unload_assets,
                self.load_assets_by_load_key(
                    key_name='{}_start'.format(mode.name),
                    priority=priority))

    def load_assets_by_load_key(self, key_name, priority=0):
        """Load all the assets with a given load key.

        Args:
            key_name: String of the load: key name.
        """
        del priority
        assets = set()
        # loop through all the registered assets of each class and look for
        # this key name
        for ac in self._asset_classes:
            asset_objects = getattr(self.machine, ac['attribute']).values()
            for asset in [x for x in asset_objects if
                          x.config['load'] == key_name]:
                asset.load()
                assets.add(asset)

        return assets

    @classmethod
    def unload_assets(cls, assets):
        """Unload multiple assets.

        Args:
            assets: An iterable of asset objects. You can safely mix
                    different classes of assets.
        """
        for asset in assets:
            asset.unload()

    def load_asset(self, asset):
        """Load an asset."""
        raise NotImplementedError("implement")

    def _bcp_client_asset_load(self, total, remaining):
        # Callback for the BCP assets_to_load command which tracks asset
        # loading from a connected BCP client.
        self.num_bcp_assets_loaded = int(total) - int(remaining)
        self.num_bcp_assets_to_load = int(total)
        self._post_loading_event()

    def _post_loading_event(self):
        # Called each time an asset is loaded.
        total = self.num_assets_to_load + self.num_bcp_assets_to_load
        remaining = total - self.num_assets_loaded - self.num_bcp_assets_loaded

        self.machine.events.post(
            'loading_assets', total=total,
            loaded=self.num_assets_loaded + self.num_bcp_assets_loaded,
            remaining=remaining,
            percent=self.loading_percent)
        '''event: loading_assets

        desc: Posted when the number of assets waiting to be loaded changes.

        Note that once all the assets are loaded, all the values below are
        reset to zero.

        args:

        total: The total number of assets that need to be loaded. This is
        equal to the sum of the *loaded* and *remaining* values below. It
        also includes assets that MPF is loading itself as well as any
        assets that have been reported from remotely connected BCP hosts
        (e.g. the media controller).

        loaded: The number of assets that have been loaded so far.

        remaining: The number of assets that are remaining to be loaded.

        percent: The numerical percent completion of the assets loaded, express
            in the range of 0 to 100.

        '''

        if not remaining:
            self.machine.events.post('asset_loading_complete')
            '''event: asset_loading_complete
            desc: Posted when the asset manager has loaded all the assets in
            its queue.

            Note that this event does *NOT* necessarily mean that all asset
            loading is complete. Rather is just means that the asset manager
            has loaded everything in its queue.

            For example, when the MPF-MC boots, it will load the assets it is
            configured to load on start. However, if the MPF MC is started but
            MPF is not, then the MPF MC will load its assets and then post this
            *asset_loading_complete* event when it's done. Then when MPF is
            started and connects, MPF will need to load its own assets, which
            means the MPF MC will post more *loading_assets* and then
            a final *asset_loading_complete* event a second time for the
            MPF-based assets.
            '''

        self.log.debug('Loading assets: %s/%s (%s%%)',
                       self.num_assets_loaded + self.num_bcp_assets_loaded,
                       total, self.loading_percent)

        if not remaining and not self.machine.is_init_done:
            self.machine.clear_boot_hold('assets')


class AsyncioAssetManager(BaseAssetManager):

    """AssetManager which uses asyncio to load assets."""

    @staticmethod
    def _load_sync(asset):
        with asset.lock:
            if not asset.loaded:
                asset.do_load()
                return True
            else:
                return False

    @asyncio.coroutine
    def wait_for_asset_load(self, asset):
        """Wait for an asset to load."""
        result = yield from self.machine.clock.loop.run_in_executor(None, self._load_sync, asset)
        if result:
            asset.is_loaded()
        self.num_assets_loaded += 1
        self._post_loading_event()

    def load_asset(self, asset):
        """Load an asset."""
        self.num_assets_to_load += 1
        self.machine.clock.loop.create_task(self.wait_for_asset_load(asset))


class AsyncioSyncAssetManager(BaseAssetManager):

    """AssetManager which uses asyncio to load assets."""

    @staticmethod
    def _load_sync(asset):
        if not asset.loaded:
            asset.do_load()
            return True
        else:
            return False

    @asyncio.coroutine
    def wait_for_asset_load(self, asset):
        """Wait for an asset to load."""
        result = self._load_sync(asset)
        if result:
            asset.is_loaded()
        self.num_assets_loaded += 1
        self._post_loading_event()

    def load_asset(self, asset):
        """Load an asset."""
        self.num_assets_to_load += 1
        task = self.machine.clock.loop.create_task(self.wait_for_asset_load(asset))
        task.add_done_callback(self._done)

    @staticmethod
    def _done(future):
        """Evaluate result of task.

        Will raise exceptions from within task.
        """
        future.result()


class AssetPool(object):

    """Pool of assets."""

    def __init__(self, mc, name, config, member_cls):
        """Initialise asset pool."""
        self.machine = mc
        self.priority = None
        self.name = name
        self.config = config
        self.member_cls = member_cls
        self.loading_members = set()
        self._callbacks = set()
        self.assets = list()
        self._last_asset = None
        self._asset_sequence = deque()
        self._assets_sent = set()
        self._total_weights = 0

        if 'load' not in config:
            config['load'] = 'on_demand'

        if 'type' not in config:
            config['type'] = 'sequence'

        for asset in Util.string_to_list(self.config[self.member_cls.config_section]):
            try:
                name, number = asset.split('|')
                if not number:
                    number = 1
                else:
                    number = int(number)
            except ValueError:
                name = asset
                number = 1

            try:
                self.assets.append((
                    getattr(self.machine, self.member_cls.attribute)[name],
                    number))
            except KeyError:
                raise ValueError("No asset named {}".format(name))

        self._configure_return_asset()

    def __repr__(self):
        """Return string representation."""
        return '<AssetPool: {}>'.format(self.name)

    @property
    def asset(self):
        """Pop one asset from the pool."""
        if self.config['type'] == 'random':
            return self._get_random_asset()
        elif self.config['type'] == 'sequence':
            return self._get_sequence_asset()
        elif self.config['type'] == 'random_force_next':
            return self._get_random_force_next_asset()
        elif self.config['type'] == 'random_force_all':
            return self._get_random_force_all_asset()

    def _configure_return_asset(self):
        self._total_weights = sum([x[1] for x in self.assets])

        if self.config['type'] == 'sequence':
            for index in range(len(self.assets)):
                self._asset_sequence.extend([self.assets[index][0]] *
                                            self.assets[index][1])
            self._asset_sequence.rotate(1)

    def load(self, callback=None, priority=None):
        """Load pool."""
        if priority is not None:
            self.priority = priority

        self._callbacks.add(callback)

        for asset in self.assets:
            if not asset[0].loaded:
                self.loading_members.add(asset)
                asset[0].load(callback=self._group_member_loaded)

        if not self.loading_members:
            self._call_callbacks()

    def _group_member_loaded(self, asset):
        self.loading_members.discard(asset)
        if not self.loading_members:
            self._call_callbacks()

    def _call_callbacks(self):
        for callback in self._callbacks:

            if callable(callback):
                callback(self)

        self._callbacks = set()

    def _get_random_asset(self):
        return self._pick_weighed_random(self.assets)[0]

    def _get_sequence_asset(self):
        self._asset_sequence.rotate(-1)
        return self._asset_sequence[0]

    def _get_random_force_next_asset(self):
        self._total_weights = sum([x[1] for x in self.assets
                                   if x is not self._last_asset])

        self._last_asset = self._pick_weighed_random([x for x in self.assets
                                                      if
                                                      x is not
                                                      self._last_asset])
        return self._last_asset[0]

    def _get_random_force_all_asset(self):
        if len(self._assets_sent) == len(self.assets):
            self._assets_sent = set()

        asset = self._pick_weighed_random([x for x in self.assets
                                           if x not in self._assets_sent])
        self._assets_sent.add(asset)
        return asset[0]

    def _pick_weighed_random(self, assets):
        value = random.randint(1, self._total_weights)
        index_value = assets[0][1]

        for asset in assets:
            if index_value >= value:
                return asset
            else:
                index_value += asset[1]

        return assets[-1]


class Asset(object):

    """Baseclass for all assets."""

    attribute = ''  # attribute in MC, e.g. self.machine.images
    path_string = ''  # entry from mpf-mc:paths: for asset folder name
    config_section = ''  # section in the config files for this asset
    disk_asset_section = ''  # option is assets: config name is different
    extensions = ('', '', '')  # tuple of strings, no dots
    class_priority = 0  # Order asset classes will be loaded. Higher is first.
    pool_config_section = None  # Create an associated AssetPool instance
    asset_group_class = AssetPool  # replace with your own asset group class

    @classmethod
    def initialize(cls, machine):
        """Initialise asset class."""
        if not cls.disk_asset_section:
            cls.disk_asset_section = cls.config_section

        machine.asset_manager.register_asset_class(
            asset_class=cls,
            attribute=cls.attribute,
            path_string=cls.path_string,
            config_section=cls.config_section,
            disk_asset_section=cls.disk_asset_section,
            extensions=cls.extensions,
            priority=cls.class_priority,
            pool_config_section=cls.pool_config_section)

    def __init__(self, machine, name, file, config):
        """Initialise asset."""
        self.machine = machine
        self.name = name
        self.file = file

        self.config = self.machine.config_validator.validate_config(
            'assets:{}'.format(self.config_section), config,
            base_spec='assets:common')

        self.priority = self.config.get('priority', 0)
        self._callbacks = set()
        self._id = machine.asset_manager.get_next_id()
        self.lock = threading.Lock()

        self.loading = False  # Is this asset in the process of loading?
        self.loaded = False  # Is this asset loaded and ready to use?
        self.unloading = False  # Is this asset in the process of unloading?

    def __repr__(self):
        """Return string representation."""
        return '<{} Asset: {}, loaded={}>'.format(self.attribute.capitalize(),
                                                  self.name, self.loaded)

    def __lt__(self, other):
        """Compare assets."""
        # Note this is "backwards" (It's the __lt__ method but the formula uses
        # greater than because the PriorityQueue puts lowest first.)
        return ("%s, %s" % (self.priority, self._id) >
                "%s, %s" % (other.priority, other.get_id()))

    def get_id(self):
        """Return id."""
        return self._id

    def load(self, callback=None, priority=None):
        """Start loading the asset."""
        if priority is not None:
            self.priority = priority

        self._callbacks.add(callback)

        if self.loaded:
            self._call_callbacks()
            return

        if self.unloading:
            pass
            # do something fancy here. Maybe just skip it and come back?

        self.loading = True
        self.machine.asset_manager.load_asset(self)

    def _call_callbacks(self):
        for callback in self._callbacks:
            if callable(callback):
                callback(self)

        self._callbacks = set()

    def do_load(self):
        """Load the asset blocking."""
        # This is the actual method that loads the asset. It's called by a
        # different thread so it's ok to block. Make sure you don't set any
        # attributes here or you don't need any since it's a separate thread.
        raise NotImplementedError

    def is_loaded(self):
        """Called when asset has been loaded."""
        self._call_callbacks()
        self.loading = False
        self.loaded = True
        self.unloading = False

    def unload(self):
        """Called when the asset has been unloaded."""
        self.unloading = True
        self.loaded = False
        self.loading = False
        self._do_unload()
        self.unloading = False

    def _do_unload(self):
        # This is the actual method that unloads the asset
        raise NotImplementedError
