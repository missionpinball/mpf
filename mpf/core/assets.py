"""Contains AssetManager, AssetLoader, and Asset base classes."""
import copy
import os
import random
import threading
from collections import deque, namedtuple
from pathlib import PurePath

import asyncio

from typing import Iterable, Optional, Set, Callable, Tuple
from typing import List

from mpf.core.mode import Mode

from mpf.core.machine import MachineController
from mpf.core.mpf_controller import MpfController
from mpf.core.utility_functions import Util
from mpf.core.logging import LogMixin

AssetClass = namedtuple("AssetClass", ["attribute", "cls", "path_string", "config_section", "disk_asset_section",
                                       "extensions", "priority", "pool_config_section", "defaults"])


class BaseAssetManager(MpfController, LogMixin):

    """Base class for the Asset Manager."""

    # needed here so the auto-detection of child classes works
    module_name = 'AssetManager'
    config_name = 'asset_manager'

    __slots__ = ["_asset_classes", "num_assets_to_load", "num_assets_loaded", "num_bcp_assets_to_load",
                 "num_bcp_assets_loaded", "_next_id", "_last_asset_event_time", "initial_assets_loaded"]

    def __init__(self, machine: MachineController) -> None:
        """Initialise asset manager.

        Args:
            machine: The machine controller
        """
        super().__init__(machine)

        self.machine.register_boot_hold('assets')

        self._asset_classes = list()        # type: List[AssetClass]
        # List of dicts, with each dict being an asset class. See
        # register_asset_class() method for details.

        self.initial_assets_loaded = False  # type: bool
        # True if the initial asset loaded is done

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
        if 'force_assets_load' in self.machine.options:
            force_assets_load = self.machine.options['force_assets_load']
        else:
            force_assets_load = False
        self.machine.events.add_handler('init_phase_3', self._create_assets,
                                        force_assets_load=force_assets_load)

        # Picks up asset load information from connected BCP client(s)
        self.machine.events.add_handler('assets_to_load',
                                        self._bcp_client_asset_load)

        # prevent excessive loading_assets events
        self._last_asset_event_time = None

    def get_next_id(self) -> int:
        """Return the next free id."""
        self._next_id += 1
        return self._next_id

    @property
    def loading_percent(self) -> int:
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

        except ZeroDivisionError:   # pragma: no cover
            return 100

    # pylint: disable-msg=too-many-arguments
    def register_asset_class(self, asset_class: str, attribute: str, config_section: str,
                             disk_asset_section: str,
                             path_string: str, extensions: Iterable[str], priority: int,
                             pool_config_section: str) -> None:
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
            setattr(self.machine, attribute, dict())

        ac = AssetClass(attribute=attribute,
                        cls=asset_class,
                        path_string=path_string,
                        config_section=config_section,
                        disk_asset_section=disk_asset_section,
                        extensions=extensions,
                        priority=priority,
                        pool_config_section=pool_config_section,
                        defaults=self._get_asset_class_defaults(disk_asset_section, self.machine.machine_config))

        self._asset_classes.append(ac)
        self._asset_classes.sort(key=lambda x: x.priority, reverse=True)

    @classmethod
    def _get_asset_class_defaults(cls, disk_asset_section: str, config) -> dict:
        # Creates the folder-based default configs for the asset class
        # starting with the default section and then created folder-specific
        # entries based on that. Just runs once on startup for each asset
        # class.
        default_config_dict = dict()

        if 'assets' in config and config['assets']:

            if (disk_asset_section in config['assets'] and
                    config['assets'][disk_asset_section]):

                this_config = config['assets'][disk_asset_section]

                # set the default
                default_config_dict['default'] = this_config['default']

                for default_section_name in this_config:
                    # first get a copy of the default for this section
                    default_config_dict[default_section_name] = (
                        copy.deepcopy(default_config_dict['default']))

                    # then merge in this section's specific settings
                    default_config_dict[default_section_name].update(
                        this_config[default_section_name])

        return default_config_dict

    def _create_assets(self, **kwargs) -> None:
        force_assets_load = kwargs.get('force_assets_load', False)

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
                [x for x in getattr(self.machine, ac.attribute).values() if
                 x.config['load'] == 'preload' or force_assets_load])

        wait_for_assets = False
        for asset in preload_assets:
            if not asset.load():
                wait_for_assets = True

        if not wait_for_assets:
            self.machine.clear_boot_hold('assets')

    def _create_assets_from_disk(self, config: dict, mode: Optional[Mode] = None) -> dict:
        """Walk a folder (and subfolders) and finds all the assets.

        Check to see if those assets have config entries in the passed config file, and
        then builds a config for each asset based on its config entry, and/or
        defaults based on the subfolder it was in or the general defaults.
        Then it creates the asset objects based on the built-up config.

        Args:
            config: A config dictionary.
            mode: Optional reference to the mode object which is used when
                  assets are being created from mode folders.

        Returns:
            An updated config dictionary. (See the "How it works" section below for details.)

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
        if not config:      # pragma: no cover
            config = dict()

        try:
            mode_name = mode.name
            path = mode.path
        except AttributeError:
            mode_name = None
            path = self.machine.machine_path

        for ac in self._asset_classes:
            if ac.disk_asset_section not in config:
                config[ac.disk_asset_section] = dict()

            # Populate the config section for this asset class with all the
            # assets found on disk
            config[ac.disk_asset_section] = self._create_asset_config_entries(
                asset_class=ac,
                config=config[ac.disk_asset_section],
                mode_name=mode_name,
                path=path)

            # create the actual instance of the Asset object and add it
            # to the self.machine asset attribute dict for that asset class
            for asset in config[ac.disk_asset_section]:
                if 'file' not in config[ac.disk_asset_section][asset]:      # pragma: no cover
                    msg = "The file associated with the disk-based asset '%s' declared in the " \
                          "'%s' config section could not be found" % (asset, ac.disk_asset_section)
                    self.error_log(msg)
                    raise FileNotFoundError(msg)

                getattr(self.machine, ac.attribute)[asset] = ac.cls(
                    self.machine, name=asset,
                    file=config[ac.disk_asset_section][asset]['file'],
                    config=config[ac.disk_asset_section][asset])

        return config

    # pylint: disable-msg=too-many-locals
    def _create_asset_config_entries(self, asset_class: AssetClass, config, mode_name: Optional[str] = None,
                                     path: Optional[str] = None) -> dict:
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
        on the file name.

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

        root_path = os.path.join(path, asset_class.path_string)
        self.debug_log("Processing assets from base folder: %s", root_path)

        # ignore temporary files
        ignore_prefixes = (".", "~")
        # do not get fooled by windows or mac garbage
        ignore_files = ("desktop.ini", "Thumbs.db")

        # walk files in the asset root directory (include all subfolders)
        for this_path, _, files in os.walk(root_path, followlinks=True):
            # Determine the first-level sub-folder of the current path relative to the
            # asset root path.  The first level sub-folder is used to determine the
            # default asset keys based on the assets config section.
            relative_path = PurePath(this_path).relative_to(root_path)
            if relative_path.parts:
                first_level_subfolder = relative_path.parts[0]
            else:
                first_level_subfolder = None

            valid_files = [f for f in files if f.endswith(
                           asset_class.extensions) and not f.startswith(ignore_prefixes) and f != ignore_files]

            # loop over valid files in the current path
            for file_name in valid_files:
                name = os.path.splitext(file_name)[0]
                full_file_path = os.path.join(this_path, file_name)

                # determine default group based on first level sub-folder and location groups
                # configured in the assets section
                if first_level_subfolder is None or first_level_subfolder not in asset_class.defaults:
                    default_string = 'default'
                else:
                    default_string = first_level_subfolder

                # built_up_config is the built-up config dict for that will be
                # used for the entry for this asset.

                # first deepcopy the default config for this asset based
                # on its default_string (folder) since we use it as the base
                # for everything in case one of the custom folder configs
                # doesn't include all settings
                built_up_config = copy.deepcopy(
                    asset_class.defaults[default_string])

                # scan through the existing config to see if this file is used
                # as the file setting for any entry.
                found_in_config = False
                for k, v in config.items():
                    if ('file' in v and v['file'] == file_name) or name == k:
                        # if it's found, set the asset entry's name to whatever
                        # the name of this entry is
                        name = k
                        # merge in the config settings for this asset, updating
                        #  the defaults
                        built_up_config.update(config[k])
                        found_in_config = True
                        break

                # need to send the full file path to the Asset that will
                # be created so it will be able to load it later.
                built_up_config['file'] = full_file_path

                # If this asset is set to load on mode start, replace the load
                # value with one based on mode name
                if built_up_config['load'] == 'mode_start':
                    built_up_config['load'] = '{}_start'.format(mode_name)

                # Update the config for that asset

                if name in config and not found_in_config:      # pragma: no cover
                    raise RuntimeError(
                        "Duplicate Asset name found: {}".format(name))

                config[name] = built_up_config

                self.info_log("Registering Asset: %s, File: %s, Default "
                              "Group: %s, Final Config: %s", name, file_name,
                              default_string, built_up_config)
        return config

    def _create_asset_groups(self, config, mode=None) -> None:
        # creates named groups of assets and adds them to to the mc's asset
        # dicts
        del mode
        for ac in [x for x in self._asset_classes
                   if x.pool_config_section]:

            if ac.pool_config_section in config:
                for name, settings in config[ac.pool_config_section].items():
                    getattr(self.machine, ac.attribute)[name] = (
                        ac.cls.asset_group_class(self.machine, name, settings,
                                                 ac.cls))

    def _load_mode_assets(self, config, priority: int, mode: Mode) -> \
            Tuple[Callable[[Iterable["Asset"]], None], Set["Asset"]]:
        # Called on mode start to load the assets that are set to automatically
        # load based on that mode starting
        del config
        return (self.unload_assets,
                self.load_assets_by_load_key(
                    key_name='{}_start'.format(mode.name),
                    priority=priority))

    def load_assets_by_load_key(self, key_name: str, priority: int = 0) -> Set["Asset"]:
        """Load all the assets with a given load key.

        Args:
            key_name: String of the load: key name.
        """
        del priority
        assets = set()
        # loop through all the registered assets of each class and look for
        # this key name
        for ac in self._asset_classes:
            asset_objects = getattr(self.machine, ac.attribute).values()
            for asset in [x for x in asset_objects if
                          x.config['load'] == key_name]:
                asset.load()
                assets.add(asset)

        return assets

    @classmethod
    def unload_assets(cls, assets: Iterable["Asset"]) -> None:
        """Unload multiple assets.

        Args:
            assets: An iterable of asset objects. You can safely mix
                    different classes of assets.
        """
        for asset in assets:
            asset.unload()

    def load_asset(self, asset: "Asset") -> None:
        """Load an asset."""
        raise NotImplementedError("implement")

    def _bcp_client_asset_load(self, total, remaining, **kwargs):
        # Callback for the BCP assets_to_load command which tracks asset
        # loading from a connected BCP client.
        del kwargs
        self.num_bcp_assets_loaded = int(total) - int(remaining)
        self.num_bcp_assets_to_load = int(total)
        self._post_loading_event()

    def _post_loading_event(self):
        # Called each time an asset is loaded.
        total = self.num_assets_to_load + self.num_bcp_assets_to_load
        remaining = total - self.num_assets_loaded - self.num_bcp_assets_loaded

        # limit loading_assets events to max 5 per second
        if remaining and self._last_asset_event_time and \
                self._last_asset_event_time > self.machine.clock.get_time() - 0.2:
            return

        self._last_asset_event_time = self.machine.clock.get_time()

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
            self._last_asset_event_time = None
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

        self.info_log('Loading assets: %s/%s (%s%%)',
                      self.num_assets_loaded + self.num_bcp_assets_loaded,
                      total, self.loading_percent)

        if not remaining and not self.machine.is_init_done.is_set():
            self.machine.clear_boot_hold('assets')
            self.initial_assets_loaded = True


class AsyncioSyncAssetManager(BaseAssetManager):

    """AssetManager which uses asyncio to load assets."""

    __slots__ = []

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


# pylint: disable=too-many-instance-attributes
class AssetPool:

    """Pool of assets."""

    __slots__ = ["machine", "priority", "name", "config", "member_cls", "loading_members", "_callbacks", "assets",
                 "_last_asset", "_asset_sequence", "_assets_sent", "_total_weights", "_has_conditions"]

    # Could possibly combine some or make @properties?
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
        self._has_conditions = False

        if 'load' not in config:
            config['load'] = 'on_demand'

        if 'type' not in config:
            config['type'] = 'sequence'

        for asset in Util.string_to_list(self.config[self.member_cls.config_section]):
            asset_dict = self.machine.placeholder_manager.parse_conditional_template(asset, default_number=1)

            # For efficiency, track whether any assets have conditions
            if asset_dict['condition']:
                self._has_conditions = True

            try:
                self.assets.append((
                    getattr(self.machine, self.member_cls.attribute)[asset_dict['name']],
                    asset_dict['number'], asset_dict['condition']))
            except KeyError:    # pragma: no cover
                raise ValueError("No asset named {}".format(asset_dict['name']))

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
        else:
            raise AssertionError("Invalid type {}".format(self.config['type']))

    @property
    def loaded(self):
        """Return if loaded."""
        for asset in self.assets:
            if not asset[0].loaded:
                return False

        return True

    @property
    def loading(self):
        """Return if loading."""
        for asset in self.assets:
            if asset[0].loading:
                return True

        return False

    @property
    def unloading(self):
        """Return if unloading."""
        for asset in self.assets:
            if asset[0].unloading:
                return True

        return False

    def _configure_return_asset(self):
        self._total_weights = sum([x[1] for x in self.assets])

        if self.config['type'] == 'sequence':
            for index in range(len(self.assets)):
                self._asset_sequence.extend([self.assets[index][0]] *
                                            self.assets[index][1])
            self._asset_sequence.rotate(1)

    def load(self, callback=None, priority=None) -> bool:
        """Load all assets in the pool."""
        # No need to attempt to load the asset if it is already loading
        if priority is not None:
            self.priority = priority

        if callback:
            self._callbacks.add(callback)

        for asset in self.assets:
            if not asset[0].loaded and not asset[0].loading:
                self.loading_members.add(asset)
                asset[0].load(callback=self._group_member_loaded)

        if not self.loading_members:
            self._call_callbacks()
            return True

        return False

    def unload(self):
        """Unload all assets in the pool."""
        for asset in self.assets:
            if asset[0].loaded:
                asset[0].unload()

    def _group_member_loaded(self, asset):
        self.loading_members.discard(asset)
        if not self.loading_members:
            self._call_callbacks()

    def _call_callbacks(self):
        for callback in self._callbacks:

            if callable(callback):
                callback(self)

        self._callbacks = set()

    def _get_conditional_assets(self):
        if not self._has_conditions:
            return self.assets

        result = [asset for asset in self.assets
                  if not asset[2] or asset[2].evaluate([])]
        # Avoid crashes, return None as the asset if no conditions evaluate true
        if not result:
            self.machine.log.warning("AssetPool {}: {}".format(
                self.name, "All conditional assets evaluated False and no other assets defined."))
            result.append((None, 0))
        return result

    def _get_random_asset(self) -> AssetClass:
        conditional_assets = self._get_conditional_assets()  # Store to variable to avoid calling twice
        # If any asset in the group has a condition, recalculate the total weight based on what's valid
        if self._has_conditions:
            self._total_weights = sum([x[1] for x in conditional_assets])
        return self._pick_weighed_random(conditional_assets)[0]

    def _get_sequence_asset(self) -> AssetClass:
        self._asset_sequence.rotate(-1)
        if self._has_conditions:
            # Get the names of all assets that evaluate true
            truthy_asset_names = [asset[0].name for asset in self._get_conditional_assets()]
            # Skip any assets that have falsey conditions
            for x in range(len(self._asset_sequence)):
                if self._asset_sequence[0].name in truthy_asset_names:
                    break
                elif x == len(self._asset_sequence) - 1:
                    self.machine.log.warning("AssetPool {}: All assets in sequence evaluated False.".format(self.name))
                    return None
                else:
                    self._asset_sequence.rotate(-1)
        return self._asset_sequence[0]

    def _get_random_force_next_asset(self) -> AssetClass:
        conditional_assets = self._get_conditional_assets()  # Store to variable to avoid calling twice
        self._total_weights = sum([x[1] for x in conditional_assets
                                   if x is not self._last_asset])

        self._last_asset = self._pick_weighed_random([x for x in conditional_assets
                                                      if
                                                      x is not
                                                      self._last_asset])
        return self._last_asset[0]

    def _get_random_force_all_asset(self) -> AssetClass:
        conditional_assets = self._get_conditional_assets()  # Store to variable to avoid calling twice
        if len(self._assets_sent) == len(conditional_assets):
            self._assets_sent = set()

        asset = self._pick_weighed_random([x for x in conditional_assets
                                           if x not in self._assets_sent])
        if asset[0] is not None:
            self._assets_sent.add(asset)
        return asset[0]

    def _pick_weighed_random(self, assets: List[Tuple[AssetClass, int]]) -> Tuple[AssetClass, int]:
        if not assets or assets[0][0] is None:
            return (None, 0)

        value = random.randint(1, self._total_weights)  # nosec
        index_value = assets[0][1]

        for asset in assets:
            if index_value >= value:
                return asset
            else:
                index_value += asset[1]

        return assets[-1]


class Asset:

    """Baseclass for all assets."""

    attribute = ''  # attribute in MC, e.g. self.machine.images
    path_string = ''  # entry from mpf-mc:paths: for asset folder name
    config_section = ''  # section in the config files for this asset
    disk_asset_section = ''  # option is assets: config name is different

    # tuple of strings, no dots
    extensions = tuple()  # type: Iterable[str]
    class_priority = 0  # Order asset classes will be loaded. Higher is first.

    # Create an associated AssetPool instance
    pool_config_section = None  # type: str

    asset_group_class = AssetPool  # replace with your own asset group class

    __slots__ = ["machine", "name", "file", "config", "priority", "_callbacks", "_id", "lock", "loading", "loaded",
                 "unloading"]

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
        self.machine = machine      # type: MachineController
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

    def load(self, callback=None, priority=None) -> bool:
        """Start loading the asset.

        Returns True if the asset is already loaded.
        """
        # No need to attempt to load the asset if it is already loading
        if self.loading:
            # Add the supplied callback before returning
            if callback:
                self._callbacks.add(callback)
            return False

        if priority is not None:
            self.priority = priority

        if callback:
            self._callbacks.add(callback)

        if self.loaded:
            self._call_callbacks()
            return True

        if self.unloading:
            pass
            # do something fancy here. Maybe just skip it and come back?

        self.loading = True
        self.machine.asset_manager.load_asset(self)
        return False

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
        """Handle that asset has been loaded."""
        self._call_callbacks()
        self.loading = False
        self.loaded = True
        self.unloading = False

    def unload(self):
        """Handle that asset has been unloaded."""
        self.unloading = True
        self.loaded = False
        self.loading = False
        self._do_unload()
        self.unloading = False

    def _do_unload(self):
        # This is the actual method that unloads the asset
        raise NotImplementedError
