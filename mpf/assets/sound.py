# pylint: disable=too-many-lines
"""Contains sound-related asset classes used by the audio system"""

import logging
import sys
import uuid
import weakref
from enum import Enum, unique
from typing import Optional, Union


from mpf.core.assets import Asset, AssetPool
from mpf.core.utility_functions import Util
# from mpfmc.core.audio.audio_interface import AudioInterface

# from mpfmc.assets.mc_asset import McAsset
# from mpfmc.core.audio.audio_exception import Exception


# ---------------------------------------------------------------------------
#    Default sound asset configuration parameter values
# ---------------------------------------------------------------------------
DEFAULT_VOLUME = 0.5
DEFAULT_PRIORITY = 0
DEFAULT_MAX_QUEUE_TIME = None
DEFAULT_LOOPS = 0
MINIMUM_DUCKING_DURATION = "10ms"


class SoundPool(AssetPool):
    """Allows several Sound assets to be grouped together in a 'pool' and referenced
    as a single sound when playing back.  Allows for easily managed variations
    of a sound.
    """
    # Be sure the pool group, if you use it, is first in the file ahead of the
    # asset class.
    # pylint: disable=invalid-name
    def __init__(self, mc, name, config, member_cls):
        super().__init__(mc, name, config, member_cls)

        self._track = None
        self._simultaneous_limit = None
        self._stealing_method = SoundStealingMethod.oldest
        self._key = None
        self.log = logging.getLogger('SoundPool')

        config.setdefault('track', None)
        config.setdefault('key', None)

        # Make sure a legal track name has been specified (unless only one track exists)
        if config['track']:
            # Track name specified in config, validate it
            track = self.machine.sound_system.audio_interface.get_track_by_name(self.config['track'])
            if track is None:
                self.log.error("'%s' is not a valid track name. "
                               "Could not create sound '%s' asset.", self.config['track'], name)
                raise Exception("'{}' is not a valid track name. "
                                     "Could not create sound '{}' asset"
                                     .format(self.config['track'], name))
        else:
            # Track not specified, determine track count
            if self.machine.sound_system.audio_interface.get_track_count() == 1:
                # Only one track exists, assign default track
                track = self.machine.sound_system.audio_interface.get_track(0)
                config['track'] = track.name
                self.log.debug("Sound '%s' has been assigned a default track value of '%s' "
                               "(only one track has been configured)", name, track.name)
            else:
                raise AssertionError("SoundPool {} does not have a valid track.".format(name))

        self._track = config['track']
        self._key = config['key']

        if 'simultaneous_limit' in self.config and self.config['simultaneous_limit'] is not None:
            self._simultaneous_limit = int(self.config['simultaneous_limit'])

        if 'stealing_method' in self.config and self.config['stealing_method'] is not None:
            method = str(self.config['stealing_method']).lower()
            if method == 'skip':
                self._stealing_method = SoundStealingMethod.skip
            elif method == 'oldest':
                self._stealing_method = SoundStealingMethod.oldest
            elif method == 'newest':
                self._stealing_method = SoundStealingMethod.newest
            else:
                raise Exception("Illegal value for sound_pool.stealing_method. "
                                     "Could not create sound pool '{}' asset".format(name))

    def __repr__(self):
        """String that's returned if someone prints this object"""
        return '<SoundPool: {} ({}), Loaded={}>'.format(self.name, self.id, self.loaded)

    # pylint: disable=invalid-name
    @property
    def id(self):
        """
        The id property contains a unique identifier for the sound pool (based on the Python id()
        function).  This id is used in the audio interface to uniquely identify a sound
        (rather than the name) due to the hassle of passing strings between Python and Cython.
        Return:
            An integer uniquely identifying the sound pool
        """
        return id(self)

    @property
    def loops(self):
        """Return loops."""
        return 0

    @property
    def key(self):
        """Return the unique key value for this sound pool"""
        return self._key

    @property
    def track(self):
        """The default track name on which to play the sound"""
        return self._track

    @property
    def sound(self):
        """The currently selected Sound object from the pool"""
        return self.asset

    @property
    def simultaneous_limit(self):
        """Return the maximum number of instances of the sound pool sounds that may be
        played simultaneously"""
        return self._simultaneous_limit

    @property
    def stealing_method(self):
        """Return the method used when stealing a sound instance (when a new sound
        instance is requested from the sound pool but the maximum number of instances
        has currently been reached)."""
        if self.simultaneous_limit is None:
            return None

        return self._stealing_method

    def play(self, context=None, settings=None):
        """
        Plays the sound pool on the track specified in the settings.
        Args:
            context: The context from which the sound is played.
            settings: A dictionary of settings for playback
        Returns:
            A SoundInstance object if the sound pool will be played (or queued for playback).
            None if the sound pool could not be played.
        """
        if settings and 'track' in settings:
            track_name = settings['track']
        else:
            track_name = self.track

        if track_name:
            track = self.machine.sound_system.audio_interface.get_track_by_name(track_name)
            if track:
                return track.play_sound(self, context, settings)

        return None

    def stop(self, fade_out=None):
        """
        Stops all instances of the the sound pool.

        Args:
            fade_out: Optional number of seconds over which to fade out before stopping. When
                      None, the SoundInstance value will be used.
        """
        if not fade_out:
            fade_out = 0.0

        self.machine.sound_system.audio_interface.stop_sound(self, fade_out)

    def stop_looping(self):
        """Stops all instances of the sound pool from continuing to loop."""
        self.machine.sound_system.audio_interface.stop_sound_looping(self)


@unique
class SoundStealingMethod(Enum):
    """Enumerated class containing sound stealing methods."""
    skip = 0    # Sound will be skipped (not played)
    oldest = 1  # The oldest sound will be replaced
    newest = 2  # The newest (most-recent) sound will be replaced


@unique
class ModeEndAction(Enum):
    """Enumerated class containing sound mode (context) end actions."""
    stop = 0          # Sound will stop immediately (uses fade_out setting)
    stop_looping = 1  # Looping will be canceled and the sound will be allowed to finish


# pylint: disable=too-many-instance-attributes, too-many-public-methods
class SoundAsset(Asset):
    """
    Sound asset class contains a single sound that may be played using the audio engine.

    Notes:
        It is critical that the AudioInterface be initialized before any Sound assets
        are loaded.  The loading code relies upon having an active audio interface.
    """
    attribute = 'sounds'  # attribute in MC, e.g. self.mc.images
    path_string = 'sounds'  # entry from mpf_mc:paths: for asset folder name
    config_section = 'sounds'  # section in the config files for this asset
    extensions = ('wav',)  # Additional extensions may be added at runtime
    class_priority = 100  # Order asset classes will be loaded. Higher is first.
    pool_config_section = 'sound_pools'  # Will setup groups if present
    asset_group_class = SoundPool  # Class or None to not use pools

    def __init__(self, mc, name, file, config):     # noqa
        """ Constructor"""
        super().__init__(mc, name, file, config)

        # Create a weakref dictionary to store all sound objects by id
        if not hasattr(self.machine, "sounds_by_id"):
            self.machine.sounds_by_id = weakref.WeakValueDictionary()
        self.machine.sounds_by_id[self.id] = self

        self._track = None
        self._streaming = False
        self._volume = DEFAULT_VOLUME
        self.priority = DEFAULT_PRIORITY
        self._max_queue_time = DEFAULT_MAX_QUEUE_TIME
        self._loops = DEFAULT_LOOPS
        self._loop_start_at = 0
        self._loop_end_at = None
        self._start_at = 0
        self._fade_in = 0
        self._fade_out = 0
        self._about_to_finish_time = None
        self._simultaneous_limit = None
        self._stealing_method = SoundStealingMethod.oldest
        self._events_when_played = None
        self._events_when_stopped = None
        self._events_when_looping = None
        self._events_when_about_to_finish = None
        self._mode_end_action = ModeEndAction.stop_looping
        self._markers = list()
        self._container = None  # holds the actual sound samples in memory
        self._ducking = None
        self._key = None
        self.log = logging.getLogger('SoundAsset')

        config.setdefault('track', None)

        # Make sure a legal track name has been specified (unless only one track exists)
        if config['track']:
            # Track name specified in config, validate it
            track = self.machine.sound_system.audio_interface.get_track_by_name(self.config['track'])
            if track is None:
                self.log.error("'%s' is not a valid track name. "
                               "Could not create sound '%s' asset.", self.config['track'], name)
                raise Exception("'{}' is not a valid track name. "
                                     "Could not create sound '{}' asset"
                                     .format(self.config['track'], name))
        else:
            # Track not specified, determine track count
            if self.machine.sound_system.audio_interface.get_track_count() == 1:
                # Only one track exists, assign default track
                track = self.machine.sound_system.audio_interface.get_track(0)
                config['track'] = track.name
                self.log.debug("Sound '%s' has been assigned a default track value of '%s' "
                               "(only one track has been configured)", name, track.name)
            else:
                raise AssertionError("Sound {} does not have a valid track.".format(name))

        self._track = config['track']

        # Validate sound attributes and provide default values
        self.config.setdefault('streaming', False)
        self._streaming = self.config['streaming']

        self.config.setdefault('volume', 0.5)
        self._volume = min(max(float(self.config['volume']), 0.0), 1.0)

        self.config.setdefault('priority', 0)
        self.priority = int(self.config['priority'])

        self.config.setdefault('max_queue_time', None)
        if self.config['max_queue_time'] is None:
            self._max_queue_time = None
        else:
            self._max_queue_time = Util.string_to_secs(self.config['max_queue_time'])

        self.config.setdefault('loops', 0)
        self._loops = int(self.config['loops'])

        self.config.setdefault('loop_start_at', 0)
        self._loop_start_at = Util.string_to_secs(self.config['loop_start_at'])

        self.config.setdefault('loop_end_at', None)
        if self.config['loop_end_at'] is None:
            self._loop_end_at = None
        else:
            self._loop_end_at = Util.string_to_secs(self.config['loop_end_at'])

        self.config.setdefault('simultaneous_limit', None)
        if self.config['simultaneous_limit'] is None:
            self._simultaneous_limit = None
        else:
            self._simultaneous_limit = int(self.config['simultaneous_limit'])

        self.config.setdefault('start_at', 0)
        self._start_at = Util.string_to_secs(self.config['start_at'])

        self.config.setdefault('fade_in', 0)
        self._fade_in = Util.string_to_secs(self.config['fade_in'])

        self.config.setdefault('fade_out', 0)
        self._fade_out = Util.string_to_secs(self.config['fade_out'])

        self.config.setdefault('about_to_finish_time', None)
        if self.config['about_to_finish_time'] is None:
            self._about_to_finish_time = None
        else:
            self._about_to_finish_time = Util.string_to_secs(self.config['about_to_finish_time'])

        self.config.setdefault('stealing_method', 'oldest')
        method = str(self.config['stealing_method']).lower()
        if method == 'skip':
            self._stealing_method = SoundStealingMethod.skip
        elif method == 'oldest':
            self._stealing_method = SoundStealingMethod.oldest
        elif method == 'newest':
            self._stealing_method = SoundStealingMethod.newest
        else:
            raise Exception("Illegal value for sound.stealing_method. "
                                 "Could not create sound '{}' asset".format(name))

        if 'events_when_played' in self.config and isinstance(
                self.config['events_when_played'], str):
            self._events_when_played = Util.string_to_event_list(self.config['events_when_played'])

        if 'events_when_stopped' in self.config and isinstance(
                self.config['events_when_stopped'], str):
            self._events_when_stopped = Util.string_to_event_list(self.config['events_when_stopped'])

        if 'events_when_looping' in self.config and isinstance(
                self.config['events_when_looping'], str):
            self._events_when_looping = Util.string_to_event_list(self.config['events_when_looping'])

        if 'events_when_about_to_finish' in self.config and isinstance(
                self.config['events_when_about_to_finish'], str):
            self._events_when_about_to_finish = Util.string_to_event_list(self.config['events_when_about_to_finish'])

        if 'mode_end_action' in self.config and self.config['mode_end_action'] is not None:
            action = str(self.config['mode_end_action']).lower()
            if action == 'stop':
                self._mode_end_action = ModeEndAction.stop
            elif action == 'stop_looping':
                self._mode_end_action = ModeEndAction.stop_looping
            else:
                raise Exception("Illegal value for sound.mode_end_action. "
                                     "Could not create sound '{}' asset".format(name))

        if 'key' in self.config:
            self._key = self.config['key']

        if 'markers' in self.config:
            self._markers = SoundAsset.load_markers(self.config['markers'], self.name)

        if 'ducking' in self.config:
            try:
                self._ducking = DuckingSettings(self.machine, self.config['ducking'])
            except Exception:
                raise Exception("Error in ducking settings: {}. "
                                     "Could not create sound '{}' asset"
                                     .format(sys.exc_info()[1], self.name))

        elif self._track and "tracks" in self.machine.sound_system.config and \
                'ducking' in self.machine.sound_system.config['tracks'][self._track]:
            try:
                self._ducking = DuckingSettings(
                    self.machine, self.machine.sound_system.config['tracks'][self.config['track']]['ducking'])
            except Exception:
                raise Exception("Error in ducking settings: {} of track {}"
                                     "Could not create sound '{}' asset"
                                     .format(sys.exc_info()[1], self.config['track'], self.name))

        # An attenuation value of exactly 1.0 does absolutely nothing so
        # there is no point in keeping the ducking settings for this
        # sound when attenuation is 1.0.
        if self._ducking and self._ducking.attenuation == 1.0:
            self._ducking = None

    def __del__(self):
        """Destructor"""
        self.unload()

    def __repr__(self):
        """String that's returned if someone prints this object"""
        return '<Sound: {} ({}), Loaded={}>'.format(self.name, self.id, self.loaded)

    def __lt__(self, other):
        """Less than comparison operator"""
        # Note this is "backwards" (It's the __lt__ method but the formula uses
        # greater than because the PriorityQueue puts lowest first.)
        if other is None:
            return False

        return ("%s, %s" % (self.priority, self._id) >
                "%s, %s" % (other.priority, other.get_id()))

    # pylint: disable=invalid-name
    @property
    def id(self):
        """
        The id property contains a unique identifier for the sound (based on the Python id()
        function).  This id is used in the audio interface to uniquely identify a sound
        (rather than the name) due to the hassle of passing strings between Python and Cython.
        Return:
            An integer uniquely identifying the sound
        """
        return id(self)

    @property
    def streaming(self):
        """Return whether or not this sound streamed (if not it will be loaded in memory)"""
        return self._streaming

    @property
    def track(self):
        """The default track name on which to play the sound"""
        return self._track

    @property
    def volume(self):
        """Return the volume of the sound (float 0.0 to 1.0)"""
        return self._volume

    @property
    def start_at(self):
        """Return the start at time for the sound (in seconds)"""
        return self._start_at

    @property
    def loop_start_at(self):
        """Return the loop start at time for the sound (in seconds)."""
        return self._loop_start_at

    @property
    def loop_end_at(self):
        """
        Return the loop end at time for the sound (in seconds). If None, the loop end at point will be
        at the end of the sound.
        """
        return self._loop_end_at

    @property
    def fade_in(self):
        """Return the fade in time for the sound (in seconds)"""
        return self._fade_in

    @property
    def fade_out(self):
        """Return the fade out time for the sound (in seconds)"""
        return self._fade_out

    @property
    def about_to_finish_time(self):
        """
        Return the time before the end when an about to finish marker will be generated (in seconds).
        If set to None, no about to finish marker will be generated.
        """
        return self._about_to_finish_time

    @property
    def max_queue_time(self):
        """Return the maximum time a sound may be queued before
        playing or being discarded"""
        return self._max_queue_time

    @property
    def loops(self):
        """Return the looping setting for the sound.
        0 - do not loop, -1 loop infinitely, >= 1 the number of
        times to loop."""
        return self._loops

    @property
    def simultaneous_limit(self):
        """Return the maximum number of instances of the sound that may be
        played simultaneously"""
        if self.streaming:
            # Streamed sounds only support a single instance at a time, no matter what the
            # 'simultaneous_limit' setting is.
            return 1

        return self._simultaneous_limit

    @property
    def stealing_method(self):
        """Return the method used when stealing a sound instance (when a new sound
        instance is requested but the maximum number of instances has currently
        been reached)."""
        if self.simultaneous_limit is None:
            return None

        return self._stealing_method

    @property
    def events_when_played(self):
        """Return the list of events that are posted when the sound is played"""
        return self._events_when_played

    @property
    def events_when_stopped(self):
        """Return the list of events that are posted when the sound is stopped"""
        return self._events_when_stopped

    @property
    def events_when_looping(self):
        """Return the list of events that are posted when the sound begins a new loop"""
        return self._events_when_looping

    @property
    def events_when_about_to_finish(self):
        """Return the list of events that are posted when the sound is about to finish"""
        return self._events_when_about_to_finish

    @property
    def mode_end_action(self):
        """Return the action to take when the owning mode (context) ends"""
        return self._mode_end_action

    @property
    def stop_on_mode_end(self):
        """Return whether or not the sound should stop immediately upon mode end"""
        return self._mode_end_action == ModeEndAction.stop

    @property
    def markers(self):
        """List of marker dictionary objects containing markers for this sound (optional)"""
        return self._markers

    @property
    def marker_count(self):
        """Return the number of markers specified for the sound"""
        return len(self._markers)

    @property
    def container(self):
        """The container object wrapping the structure containing the actual sound data"""
        return self._container

    @property
    def ducking(self):
        """A DuckingSettings object containing the ducking settings for this sound (optional)"""
        return self._ducking

    @property
    def has_ducking(self):
        """Return whether or not this sound has ducking"""
        return self._ducking is not None

    def set_ducking(self, ducking_settings=None):
        if not ducking_settings:
            self._ducking = None
            return
        self._ducking = DuckingSettings(self.machine, ducking_settings)

    @property
    def key(self):
        """Return the unique key value for this sound"""
        return self._key

    def create_instance(self, context: Optional[str] = None, settings: Optional[dict] = None) -> "SoundInstance":
        """Creates a new SoundInstance."""
        return SoundInstance(self, context, settings)

    def play(self, context=None, settings=None):
        """
        Plays the sound on the track specified in the settings.
        Args:
            context: The context from which the sound is played.
            settings: A dictionary of settings for playback
        Returns:
            A SoundInstance object if the sound will be played (or queued for playback).
            None if the sound could not be played.
        """
        if settings and 'track' in settings:
            track_name = settings['track']
        else:
            track_name = self.track

        if track_name:
            track = self.machine.sound_system.audio_interface.get_track_by_name(track_name)
            if track:
                return track.play_sound(self, context, settings)

        return None

    def stop(self, fade_out=None):
        """
        Stops all instances of the the sound.

        Args:
            fade_out: Optional number of seconds over which to fade out before stopping. When
                      None, the SoundAsset value will be used.
        """
        if not fade_out:
            fade_out = self.fade_out

        self.machine.sound_system.audio_interface.stop_sound(self, fade_out)

    def stop_looping(self):
        """Stops all instances of the sound from continuing to loop."""
        self.machine.sound_system.audio_interface.stop_sound_looping(self)

    def do_load(self):
        """Loads the sound asset from disk."""

        # Load the sound file into memory
        if self._container is not None:
            self.log.debug("Sound %s already loaded", self.name)
            return

        try:
            if self.streaming:
                self.log.debug("Sound %s loading for streaming", self.name)
                self._container = self.machine.sound_system.audio_interface.load_sound_file_for_streaming(self.file)
            else:
                self.log.debug("Sound %s loading to memory", self.name)
                self._container = self.machine.sound_system.audio_interface.load_sound_file_to_memory(self.file)

        except Exception as exception:
            self.log.error("Load sound %s failed due to an exception - %s",
                           self.name, str(exception))
            raise Exception("Load sound {} failed due to an exception: {}".format(
                self.name, exception)) from exception

        # Validate ducking now that the sound has been loaded
        # TODO: Implement me
        # if self._ducking is not None:
        #    try:
        #        self._ducking.validate(self._container.length)
        #    except Exception as exception:
        #        self.log.error("Ducking settings for sound %s are not valid: %s",
        #                       self.name, str(exception))
        #        raise
        #

    def _do_unload(self):
        """Unloads the asset from memory"""
        self.log.debug("Sound %s unloading", self.name)
        self.stop(0)
        if self._container is not None:
            self.machine.sound_system.audio_interface.unload_sound_file(self._container)
            self._container = None

    def is_loaded(self):
        """Called when the asset has finished loading"""
        super().is_loaded()
        self.log.debug("Loaded %s (Track %s)", self.name, self.track)

    @staticmethod
    def load_markers(config, sound_name):
        """
        Load and validate the markers config section
        Args:
            config: The 'markers' configuration file section for the sound
            sound_name: The name of the sound

        Returns:
            List of sound marker dictionary objects
        """

        markers = list()

        if isinstance(config, dict):
            config_markers = list(config)
        elif isinstance(config, list):
            config_markers = config
        else:
            raise Exception("Sound {} has an invalid markers section".format(sound_name))

        last_marker_time = 0

        # Loop over all markers in the list
        for settings in config_markers:
            marker = dict()

            # Set marker parameters
            marker['time'] = Util.string_to_secs(settings['time'])
            if marker['time'] < last_marker_time:
                raise Exception("Sound markers for sound {} must be in ascending time order".format(sound_name))
            last_marker_time = marker['time']

            if 'events' in settings and settings['events'] is not None:
                marker['events'] = Util.string_to_event_list(settings['events'])
            else:
                raise Exception("Sound markers for sound {} must specify at least one event".format(sound_name))

            if 'name' in settings and settings['name'] is not None:
                marker['name'] = settings['name'].lower()
            else:
                marker['name'] = None

            if len(markers) == AudioInterface.get_max_markers():
                raise Exception("Cannot add marker - the limit of {} sound markers has been "
                                     "reached for sound {}.".format(AudioInterface.get_max_markers(), sound_name))

            markers.append(marker)

        return markers


@unique
class SoundInstanceStatus(Enum):
    """Enumerated class containing status values for SoundInstance class."""
    pending = 0
    queued = 1
    playing = 2
    finished = 3


# pylint: disable=too-many-public-methods
class SoundInstance:
    """An instance of a playing sound asset. This class is essentially a wrapper container
    for sound assets that contains all the overridden parameter values for playback."""

    def __init__(self, sound: Union[SoundAsset, SoundPool],     # noqa
                 context: Optional[str] = None, settings: Optional[dict] = None):
        """Construct sound instance."""
        if sound is None:
            raise ValueError("Cannot create sound instance: sound parameter is None")

        # pylint: disable=invalid-name
        self.mc = sound.machine
        self._timestamp = self.mc.clock.get_time()

        if context and isinstance(context, str):
            self._context = context
        else:
            self._context = None

        self._status = SoundInstanceStatus.pending
        self._pan = 0
        self._played = False
        self._loop_count = 0
        self._registered_finished_handlers = list()
        self.log = logging.getLogger('SoundInstance')
        self._sound_id = sound.id

        # The underlying sound must be accessed differently for SoundAsset objects
        # (just use the object itself) and SoundPool object (retrieve the next
        # SoundAsset object in the pool).
        if isinstance(sound, SoundAsset):
            self._sound = sound
        elif isinstance(sound, SoundPool):
            self._sound = sound.sound

        # Simultaneous limit comes from the SoundAsset or SoundPool class and may not
        # be overridden
        self._simultaneous_limit = sound.simultaneous_limit
        self._stealing_method = sound.stealing_method
        self._markers = self._sound.markers
        self._exp_time = None

        # Assign default values from parent sound for parameters that can be overridden
        self._track = sound.track
        self._loops = self._sound.loops
        self._volume = self._sound.volume
        self._priority = self._sound.priority
        self._start_at = self._sound.start_at
        self._loop_start_at = self._sound.loop_start_at
        self._loop_end_at = self._sound.loop_end_at
        self._fade_in = self._sound.fade_in
        self._fade_out = self._sound.fade_out
        self._about_to_finish_time = self._sound.about_to_finish_time
        self._max_queue_time = self._sound.max_queue_time
        self._events_when_played = self._sound.events_when_played
        self._events_when_stopped = self._sound.events_when_stopped
        self._events_when_looping = self._sound.events_when_looping
        self._events_when_about_to_finish = self._sound.events_when_about_to_finish
        self._mode_end_action = self._sound.mode_end_action
        self._key = sound.key

        if settings is None:
            settings = dict()

        # TODO: Implement parameter validation for overridden parameters

        # Assign any overridden parameter values
        if settings.get('track'):
            self._track = settings['track']

        if settings.get('loops'):
            self._loops = settings['loops']

        if settings.get('volume'):
            self._volume = settings['volume']

        if settings.get('pan'):
            self._pan = settings['pan']

        if settings.get('priority'):
            self._priority = settings['priority']

        if settings.get('start_at'):
            self._start_at = settings['start_at']

        if settings.get('loop_start_at'):
            self._loop_start_at = settings['loop_start_at']

        if settings.get('loop_end_at'):
            self._loop_end_at = settings['loop_end_at']

        if settings.get('fade_in'):
            self._fade_in = settings['fade_in']

        if settings.get('fade_out'):
            self._fade_out = settings['fade_out']

        if settings.get('about_to_finish_time', -1) != -1:
            self._about_to_finish_time = settings['about_to_finish_time']

        if settings.get('max_queue_time', -1) != -1:
            self._max_queue_time = settings['max_queue_time']

        if settings.get('events_when_played', ['use_sound_setting']) != ['use_sound_setting']:
            self._events_when_played = settings['events_when_played']

        if settings.get('events_when_stopped', ['use_sound_setting']) != ['use_sound_setting']:
            self._events_when_stopped = settings['events_when_stopped']

        if settings.get('events_when_looping', ['use_sound_setting']) != ['use_sound_setting']:
            self._events_when_looping = settings['events_when_looping']

        if settings.get('events_when_about_to_finish', ['use_sound_setting']) != ['use_sound_setting']:
            self._events_when_about_to_finish = settings['events_when_about_to_finish']

        if settings.get('mode_end_action', 'use_sound_setting') != 'use_sound_setting':
            action = str(settings['mode_end_action']).lower()
            if action == 'stop':
                self._mode_end_action = ModeEndAction.stop
            elif action == 'stop_looping':
                self._mode_end_action = ModeEndAction.stop_looping

        if settings.get('key', 'use_sound_setting') != 'use_sound_setting':
            self._key = settings['key']

    def __repr__(self):
        """String that's returned if someone prints this object"""
        return '<SoundInstance: {} ({}), Volume={}, Loops={}, Priority={}, Loaded={}, Track={}>'.format(
            self.sound.name, self.id, self.volume, self.loops, self.priority, self.sound.loaded, self.track)

    def __lt__(self, other):
        """Less than comparison operator"""
        # Note this is "backwards" (It's the __lt__ method but the formula uses
        # greater than because the PriorityQueue puts lowest first.)
        if other is None:
            return False
        if self.priority != other.priority:
            return self.priority > other.priority
        if self.exp_time is None and other.exp_time is not None:
            return True
        if self.exp_time is not None and other.exp_time is None:
            return False
        if self.exp_time != other.exp_time:
            return self.exp_time > other.exp_time
        return self.id > other.id

    # pylint: disable=invalid-name
    @property
    def id(self):
        """
        The id property contains a unique identifier for the sound reference(based on the Python
        id() function).  This id is used in the audio interface to uniquely identify a sound
        instance (rather than the name) due to the hassle of passing strings between Python and
        Cython.
        Return:
            An integer uniquely identifying the sound reference
        """
        return id(self)

    @property
    def timestamp(self):
        """Return the time at which the sound instance was created"""
        return self._timestamp

    @property
    def context(self):
        """Return the context in which the sound instance was created"""
        return self._context

    @property
    def exp_time(self):
        """Return the expiration time of the sound instance"""
        return self._exp_time

    @exp_time.setter
    def exp_time(self, value):
        """Set the expiration time of the sound instance"""
        self._exp_time = value

    @property
    def sound(self):
        """The sound asset wrapped by this object"""
        return self._sound

    @property
    def sound_id(self):
        """The parent sound asset (or sound pool) object id this instance was created from"""
        return self._sound_id

    @property
    def streaming(self):
        """Return whether or not the wrapped sound is streamed
        (if not it will be loaded in memory)"""
        return self._sound.streaming

    @property
    def loaded(self):
        """Return whether or not the underlying sound asset file is loaded into memory"""
        return self._sound.loaded

    @property
    def name(self):
        """The name of the sound"""
        return self._sound.name

    @property
    def track(self):
        """The audio track name on which to play the sound"""
        return self._track

    @property
    def volume(self):
        """Return the volume of the sound (float 0.0 to 1.0)"""
        return self._volume

    @property
    def pan(self):
        """Return the pan setting of the sound (float -1.0 to 1.0)"""
        return self._pan

    @property
    def priority(self):
        """Return the priority of the sound"""
        return self._priority

    @property
    def max_queue_time(self):
        """Return the maximum time a sound may be queued before
        playing or being discarded"""
        return self._max_queue_time

    @property
    def start_at(self):
        """Return the start at time for the sound (in seconds)"""
        return self._start_at

    @property
    def loop_start_at(self):
        """Return the loop start at time for the sound (in seconds)."""
        return self._loop_start_at

    @property
    def loop_end_at(self):
        """
        Return the loop end at time for the sound (in seconds). If None, the loop end at point will be
        at the end of the sound.
        """
        return self._loop_end_at

    @property
    def fade_in(self):
        """Return the fade in time for the sound (in seconds)"""
        return self._fade_in

    @property
    def fade_out(self):
        """Return the fade out time for the sound (in seconds)"""
        return self._fade_out

    @property
    def about_to_finish_time(self):
        """
        Return the time before the end when an about to finish marker will be generated (in seconds).
        If set to None, no about to finish marker will be generated.
        """
        return self._about_to_finish_time

    @property
    def loops(self):
        """Return the looping setting for the sound.
        0 - do not loop, -1 loop infinitely, >= 1 the number of
        times to loop."""
        return self._loops

    @property
    def simultaneous_limit(self):
        """Return the maximum number of instances of the sound that may be
        played simultaneously"""
        return self._simultaneous_limit

    @property
    def stealing_method(self):
        """Return the method used when stealing a sound instance (when a new sound
        instance is requested but the maximum number of instances has currently
        been reached)."""
        return self._stealing_method

    @property
    def events_when_played(self):
        """Return the list of events that are posted when the sound is played"""
        return self._events_when_played

    @property
    def events_when_stopped(self):
        """Return the list of events that are posted when the sound is stopped"""
        return self._events_when_stopped

    @property
    def events_when_looping(self):
        """Return the list of events that are posted when the sound begins a new loop"""
        return self._events_when_looping

    @property
    def events_when_about_to_finish(self):
        """Return the list of events that are posted when the sound is about to finish"""
        return self._events_when_about_to_finish

    @property
    def mode_end_action(self):
        """Return the action to take when the owning mode (context) ends"""
        return self._mode_end_action

    @property
    def stop_on_mode_end(self):
        """Return whether or not the sound should stop immediately upon mode end"""
        return self._mode_end_action == ModeEndAction.stop

    @property
    def markers(self):
        """Return the list of marker dictionary objects for the sound"""
        return self._markers

    @property
    def marker_count(self):
        """Return the number of markers specified for the sound"""
        return len(self._markers)

    @property
    def container(self):
        """The container object wrapping the SDL structure containing the actual sound data"""
        return self._sound.container

    @property
    def ducking(self):
        """A DuckingSettings object containing the ducking settings for this sound (optional)"""
        return self._sound.ducking

    @property
    def has_ducking(self):
        """Return whether or not this sound has ducking"""
        return self._sound.ducking is not None

    @property
    def key(self):
        """Return the unique key value for this sound instance"""
        return self._key

    @property
    def queued(self):
        """Indicates whether or not this sound reference is currently queued for playback."""
        return self._status == SoundInstanceStatus.queued

    @property
    def pending(self):
        """Indicates whether or not this sound instance is currently pending playback."""
        return self._status == SoundInstanceStatus.pending or \
            self._status == SoundInstanceStatus.queued

    @property
    def playing(self):
        """Return whether or not this sound instance is currently playing."""
        return self._status == SoundInstanceStatus.playing

    def stop(self, fade_out=None):
        """
        Stops the sound instance.

        Args:
            fade_out: Optional number of seconds over which to fade out before stopping. When
                      None, the SoundInstance value will be used.
        """
        if not fade_out:
            fade_out = self.fade_out

        if self.track is not None:
            track = self.mc.sound_system.audio_interface.get_track_by_name(self.track)
            if track:
                track.stop_sound_instance(self, fade_out)
        else:
            self.mc.sound_system.audio_interface.stop_sound_instance(self, fade_out)

    def stop_looping(self):
        """Stops the sound instance from continuing to loop."""
        if self.track is not None:
            track = self.mc.sound_system.audio_interface.get_track_by_name(self.track)
            if track:
                track.stop_sound_instance_looping(self)
        else:
            self.mc.sound_system.audio_interface.stop_sound_instance_looping(self)

    def set_pending(self):
        """Set the sound instance status to pending."""
        self._status = SoundInstanceStatus.pending

    def set_queued(self):
        """Notifies the sound instance that it is now queued and triggers any
        corresponding actions"""
        self._status = SoundInstanceStatus.queued

    def set_playing(self):
        """Notifies the sound instance that it is now playing and triggers any
        corresponding actions."""
        self._status = SoundInstanceStatus.playing
        self._played = True
        if self.events_when_played is not None:
            for event in self.events_when_played:
                self.mc.post_mc_native_event(event, sound_instance=self)

    def set_stopped(self):
        """Notifies the sound instance that it has now stopped and triggers any
        corresponding actions."""

        # Trigger any events
        if self.events_when_stopped is not None:
            for event in self.events_when_stopped:
                self.mc.post_mc_native_event(event, sound_instance=self)

        self._finished()

    def set_looping(self):
        """Notifies the sound instance that it is now looping and triggers any
        corresponding actions."""
        # Increment the total loop count (how many times has instance looped)
        self._loop_count += 1

        # Trigger any events
        if self.events_when_looping is not None:
            for event in self.events_when_looping:
                self.mc.post_mc_native_event(event, sound_instance=self)

    def set_about_to_finish(self):
        """Notifies the sound instance that it is about to finish and triggers any
        corresponding actions."""

        # Trigger any events
        if self.events_when_about_to_finish is not None:
            for event in self.events_when_about_to_finish:
                self.mc.post_mc_native_event(event, sound_instance=self)

    def set_marker(self, marker_id):
        """Notifies the sound instance that the specified marker has just been reached
        during playback and triggers any corresponding actions."""
        try:
            marker = self._markers[marker_id]
        except ValueError:
            self.log.warning("An invalid marker ID was received: %d", marker_id)
            return

        # Trigger any events
        if marker['events'] is not None:
            for event in marker['events']:
                self.mc.post_mc_native_event(event, sound_instance=self, marker_id=marker_id)

    def set_expired(self):
        """Notifies the sound instance that it has expired and will not be played."""
        self._finished()

    def set_canceled(self):
        """Notifies the sound instance that is has been canceled and will not be played."""
        self._finished()

    def add_finished_handler(self, handler, priority=1, **kwargs):
        """
        Register a handler to be called when the sound instance has finished.
        Args:
            handler: The method that will be called when the sound instance has finished
            priority: An arbitrary integer value that defines what order the handlers will
                be called in (highest to lowest).
            **kwargs: Any additional keyword/arguments pairs

        Returns:
            A GUID reference to the handler which you can use to later remove the handler
            via ``remove_finished_handler_by_key``.
        """
        if not callable(handler):
            raise ValueError("Cannot add finished handler '{}' for sound '{}'"
                             .format(handler, self.name))

        key = uuid.uuid4()

        # A 'handler' in our case is a tuple with 4 elements:
        # the handler method, priority, dict of kwargs, & uuid key

        self._registered_finished_handlers.append((handler, priority, kwargs, key))
        try:
            self.log.debug("Registered %s as a finished handler for sound '%s', priority: %s, "
                           "kwargs: %s",
                           (str(handler).split(' '))[2], self.name, priority, kwargs)
        except IndexError:
            pass

        # Sort the handlers for this event based on priority. We do it now
        # so the list is pre-sorted so we don't have to do that with each
        # event post.
        self._registered_finished_handlers.sort(key=lambda x: x[1], reverse=True)

        return key

    def remove_finished_handler_by_key(self, key):
        """Remove a registered finished handler by key.

        Args:
            key: The key of the handler you want to remove
        """
        for handler in self._registered_finished_handlers:
            if handler[3] == key:
                self._registered_finished_handlers.remove(handler)
                self.log.debug("Removing finished handler method %s from sound %s",
                               (str(handler[0]).split(' '))[2], self.name)

    def _finished(self):
        """Internal function to trigger finished state and related processing."""
        self._status = SoundInstanceStatus.finished

        # Call any registered finished handlers
        for handler in self._registered_finished_handlers:
            merged_kwargs = dict(list(handler[2].items()))
            merged_kwargs['sound_instance'] = self

            handler[0](**merged_kwargs)

    @property
    def status(self):
        """Return the current status of the sound instance."""
        return self._status

    @property
    def played(self):
        """Return whether or not this sound instance has been played."""
        return self._played

    @property
    def finished(self):
        """Return whether or not this sound instance has finished playing."""
        return self._status == SoundInstanceStatus.finished

    @property
    def loop_count(self):
        """Return how many times this sound instance has looped back to the beginning."""
        return self._loop_count


class DuckingSettings:
    """ DuckingSettings contains the parameters needed to control audio ducking
    for a sound.
    """

    def __init__(self, mc, config):
        """
        Constructor
        Args:
            mc: The media controller instance.
            config: The ducking configuration file section that contains all the ducking
                settings for the sound.

        Notes:
            The config section should contain the following attributes:
                target: A list of track names to apply the ducking to when the sound is played.
                delay: The duration (in seconds) of the delay period (time before attack starts)
                attack: The duration (in seconds) of the attack stage of the ducking envelope
                attenuation: The attenuation (gain) (0.0 to 1.0) to apply to the target track while
                    ducking
                release_point: The point (in seconds) relative to the end of the sound at which
                    to start the release stage.  A positive value indicates prior to the end of
                    the sound while a negative value indicates to start the release after the
                    end of the sound.
                release: The duration (in seconds) of the release stage of the ducking process.
        """
        if config is None:
            raise Exception("The 'ducking' configuration must include the following "
                                 "attributes: track, delay, attack, attenuation, "
                                 "release_point, and release")

        if 'target' not in config:
            raise Exception("'ducking.target' must contain at least one "
                                 "valid audio track name")

        # Target can contain a list of track names - convert string to list and validate
        self._targets = Util.string_to_event_list(config['target'])
        if not self._targets:
            raise Exception("'ducking.target' must contain at least one "
                                 "valid audio track name")

        # Create a bit mask of target tracks based on their track number (will be used to pass
        # the target data to the audio library).
        self._track_bit_mask = 0
        for target in self._targets:
            track = mc.sound_system.audio_interface.get_track_by_name(target)
            if track is None:
                raise Exception("'ducking.target' contains an invalid track name '{}'".format(target))
            self._track_bit_mask += (1 << track.number)

        # Delay is optional (defaults to 0, must be >= 0)
        if 'delay' in config:
            self._delay = max(Util.string_to_secs(
                config['delay']), 0)
        else:
            self._delay = 0

        if 'attack' not in config:
            raise Exception("'ducking.attack' must contain a valid attack value (time "
                                 "string)")
        self._attack = max(Util.string_to_secs(config['attack']),
                           Util.string_to_secs(
                               MINIMUM_DUCKING_DURATION))

        if 'attenuation' not in config:
            raise Exception("'ducking.attenuation' must contain valid attenuation "
                                 "value (0.0 to 1.0)")
        self._attenuation = min(max(float(AudioInterface.string_to_gain(
            config['attenuation'])), 0.0), 1.0)

        if 'release_point' not in config:
            raise Exception("'ducking.release_point' must contain a valid release point "
                                 "value (time string)")
        # Release point cannot be negative (must be before or at the end of the sound)
        self._release_point = max(Util.string_to_secs(
            config['release_point']), 0)

        if 'release' not in config:
            raise Exception("'ducking.release' must contain a valid release "
                                 "value (time string)")
        self._release = max(Util.string_to_secs(config['release']),
                            Util.string_to_secs(
                                MINIMUM_DUCKING_DURATION))

    @property
    def targets(self):
        """Return the list of target track names"""
        return self._targets

    @property
    def track_bit_mask(self):
        """ A bit mask of target tracks (each bit represents a track)"""
        return self._track_bit_mask

    @property
    def delay(self):
        """The duration (in samples) of the delay period (time before attack starts)"""
        return self._delay

    @property
    def attack(self):
        """The duration (in samples) of the attack stage of the ducking envelope"""
        return self._attack

    @property
    def attenuation(self):
        """The attenuation (gain) (0.0 to 1.0) to apply to the target track while ducking"""
        return self._attenuation

    @property
    def release_point(self):
        """The point (in samples) relative to the end of the sound at which
        to start the release stage.  A positive value indicates prior to the end of
        the sound while a negative value indicates to start the release after the
        end of the sound.
        """
        return self._release_point

    @property
    def release(self):
        """The duration (in samples) of the release stage of the ducking process."""
        return self._release

    def validate(self, sound_length):
        """
        Validates the ducking settings against the length of the sound to ensure all
        settings are valid.
        Args:
            sound_length: The length of the sound in samples

        Return:
            True if all settings are valid, otherwise an exception will be thrown
        """
        if sound_length is None or sound_length == 0:
            raise Exception("ducking may not be applied to an empty/zero length sound")

        if self._attack > sound_length:
            raise Exception("'ducking.attack' value may not be longer than the "
                                 "length of the sound")

        if self._release_point >= sound_length:
            raise Exception("'ducking.release_point' value may not occur before the "
                                 "beginning of the sound")

        if self._release_point + self._attack >= sound_length:
            raise Exception("'ducking.release_point' value may not occur before "
                                 "the ducking attack segment has completed")

        return True
