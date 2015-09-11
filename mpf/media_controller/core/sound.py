"""MPF plugin for sounds. Includes SoundController, Channel, Sound, Track, and
StreamTrack parent classes."""
# sound.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import time
import Queue
import uuid
import copy
import sys

from mpf.system.assets import Asset, AssetManager
from mpf.system.config import Config

global import_success

try:
    import pygame
    import pygame.locals
    import_success = True
except:
    import_success = False


def preload_check(machine):

    if import_success:
        return True
    else:
        return False


class SoundController(object):
    """Parent class for the sound controller which is responsible for all audio,
    sounds, and music in the machine. There is only one of these per machine.

    Args:
        machine: The main machine controller object.

    """

    def __init__(self, machine):
        self.log = logging.getLogger('SoundController')
        self.machine = machine

        if 'sound_system' not in self.machine.config:
            self.config = dict()
            return  # todo move to preload_check()

        self.log.debug("Loading the Sound Controller")

        self.machine.sound = self
        self.config = self.machine.config['sound_system']
        self.tracks = dict()  # k = track name, v = track obj
        self.stream_track = None
        self.pygame_channels = list()
        self.sound_events = dict()
        self.volume = 1.0

        if 'volume_steps' not in self.config:
            self.config['volume_steps'] = 20

        if 'initial_volume' in self.config:
            self.volume = self.config['initial_volume']

        self.set_volume(volume=self.volume)

        self.machine.request_pygame()

        # Get the pygame pre-initiaiization audio requests in
        # 0 is the 'auto' setting for all of these
        if 'buffer' not in self.config or self.config['buffer'] == 'auto':
            self.config['buffer'] = 0

        if 'bits' not in self.config or self.config['bits'] == 'auto':
            self.config['bits'] = 0

        if 'frequency' not in self.config or self.config['frequency'] == 'auto':
            self.config['frequency'] = 0

        if 'channels' not in self.config:
                self.config['channels'] = 1

        pygame.mixer.pre_init(frequency=self.config['frequency'],
                              size=self.config['bits'],
                              channels=self.config['channels'],
                              buffer=self.config['buffer']
                              )
        # Note pygame docs says pre_init() kwarg should be 'buffersize', but
        # it's actually 'buffer'.

        # Register events
        self.machine.events.add_handler('action_set_volume', self.set_volume)
        self.machine.events.add_handler('pygame_initialized', self._initialize)

        if 'sound_player' in self.machine.config:
            self.machine.events.add_handler('init_phase_5',
                self.register_sound_events,
                config=self.machine.config['sound_player'])

        self.machine.mode_controller.register_start_method(self.register_sound_events,
                                                 'sound_player')

    def _initialize(self):
        # Initialize the sound controller. Not done in __init__() because we
        # need Pygame to be setup first.

        try:
            frequency, bits, channels = pygame.mixer.get_init()
        except TypError:
            self.log.error("Could not initialize audio. Does your computer "
                           "have an audio device? Maybe it doesn't create one"
                           "if there are no speakers plugged in?")
            sys.exit()

        self.log.debug("Pygame Sound Mixer configuration. Freq: %s, Bits: %s, "
                       "Channels: %s", frequency, bits, channels)

        # Configure Pygame to use the correct number of channels. We need one
        # for each simultaneous sound we want to play.
        num_channels = 0  # How many total

        if 'tracks' in self.config:
            for item in self.config['tracks'].values():
                if 'simultaneous_sounds' in item:
                    num_channels += item['simultaneous_sounds']
                else:
                    num_channels += 1

        if not num_channels:
            num_channels = 1

        pygame.mixer.set_num_channels(num_channels)

        # Configure Tracks
        if 'tracks' in self.config:
            for k, v in self.config['tracks'].iteritems():
                self.create_track(name=k, config=v)
        else:
            self.create_track(name='default')

        # Configure streaming track
        if 'stream' in self.config:

            if 'name' not in self.config['stream']:
                self.config['stream']['name'] = 'music'

            self.stream_track = StreamTrack(self.machine, self.config)

        # Create the sound AssetManager
        AssetManager(
            machine=self.machine,
            config_section=config_section,
            path_string=(self.machine.config['media_controller']['paths'][path_string]),
            asset_class=asset_class,
            asset_attribute=asset_attribute,
            file_extensions=file_extensions)

    def create_track(self, name, config=None):
        """ Creates a new MPF track add registers in the central track list.

        Args:
            name: String name of this track used for identifying where sounds
                are played.
            config: Config dictionary for this track.

        Note: "Tracks" in MPF are like channels.. you might have a "music"
        track, a "voice" track, a "sound effects" track, etc.
        """

        self.tracks[name] = Track(self.machine, name, self.pygame_channels,
                                  config)

    def register_sound_events(self, config, mode=None, priority=0):
        # config is sound_player subection of config dict

        self.log.debug("Processing sound_player configuration. Base Priority: "
                       "%s", priority)
        self.log.debug("config: %s", config)

        key_list = list()

        for entry_name in config:
            if 'block' not in config[entry_name]:
                config[entry_name]['block'] = False

            block = config[entry_name].pop('block')

            key_list.append(self.register_sound_event(config=config[entry_name],
                                                      priority=priority,
                                                      block=block))

        return self.unregister_sound_events, key_list

    def unregister_sound_events(self, key_list):

        self.log.debug("Unloading sound_player events")
        for key in key_list:
            self.unregister_sound_event(key)

    def register_sound_event(self, config, priority=0, block=False):
        """Sets up game sounds from the config file.

        Args:
            config: Python dictionary which contains the game sounds settings.
        """

        if 'sound' not in config:
            return False
        elif type(config['sound']) is str:
            config['sound'] = self.machine.sounds[config['sound']]
        # this is kind of weird because once the sound has been registered, the
        # sound will still be converted from the string to the object. This is
        # an unintended side effect of passing around a dict, but I guess it's
        # ok? We just have to check to make sure we have a string before we
        # try to convert it to an object. If not, the conversion has already
        # been done.

        if 'start_events' not in config:
            config['start_events'] = list()
        else:
            config['start_events'] = Config.string_to_list(
                config['start_events'])

        if 'stop_events' not in config:
            config['stop_events'] = list()
        else:
            config['stop_events'] = Config.string_to_list(
                config['stop_events'])

        if 'duration' not in config or config['duration'] is None:
            config['duration'] = None

        if 'loops' not in config or config['loops'] is None:
            config['loops'] = 0

        if 'priority' not in config or config['priority'] is None:
            config['priority'] = 0

        if 'fade_in' not in config or config['fade_in'] is None:
            config['fade_in'] = 0

        if 'fade_out' not in config or config['fade_out'] is None:
            config['fade_out'] = 0

        if 'channel' not in config or config['channel'] is None:
            config['channel'] = 'auto'

        if 'volume' not in config or config['volume'] is None:
            config['volume'] = 1
        elif config['volume'] > 2:
            config['volume'] = 2

        config['key'] = uuid.uuid4()

        #config['event_keys'] = set()

        for event in config['start_events']:
            settings = copy.copy(config)

            settings.pop('start_events')
            settings.pop('stop_events')

            if event not in self.sound_events:
                    self.sound_events[event] = list()
                    self.machine.events.add_handler(event,
                                                    self._sound_event_callback,
                                                    event_name=event)

            kwargs = dict()  # temp

            sound_event_entry = dict()

            sound_event_entry['settings'] = settings
            sound_event_entry['kwargs'] = kwargs
            sound_event_entry['priority'] = priority
            sound_event_entry['block'] = block
            sound_event_entry['type'] = 'start'

            self.sound_events[event].append(sound_event_entry)

        for event in config['stop_events']:

            settings = copy.copy(config)

            settings.pop('start_events')
            settings.pop('stop_events')

            if event not in self.sound_events:
                    self.sound_events[event] = list()
                    self.machine.events.add_handler(event,
                                                    self._sound_event_callback,
                                                    event_name=event)

            kwargs = dict()  # temp

            sound_event_entry = dict()

            sound_event_entry['settings'] = settings
            sound_event_entry['kwargs'] = kwargs
            sound_event_entry['priority'] = priority
            sound_event_entry['block'] = block
            sound_event_entry['type'] = 'stop'

            self.sound_events[event].append(sound_event_entry)

            # todo sort by priority

        return config['key']

    def unregister_sound_event(self, key):
        for event in self.sound_events.keys():
            for entry in self.sound_events[event][:]:
                if entry['settings']['key'] == key:
                    self.sound_events[event].remove(entry)

                if not self.sound_events[event]:
                    self.machine.events.remove_handler_by_event(event,
                        self._sound_event_callback)
                    del self.sound_events[event]

    def _sound_event_callback(self, event_name, **kwargs):

        # Loop through all the sound events for this event

        if event_name not in self.sound_events:
            self.log.critical("got sound callback but did not find event?")
            raise Exception()

        sound_list = self.sound_events[event_name]

        for sound in sound_list:

            sound_obj = sound['settings']['sound']
            kwargs = sound['settings']

            if sound['type'] == 'start':
                sound_obj.play(**kwargs)
            elif sound['type'] == 'stop':
                sound_obj.stop(**kwargs)

    def set_volume(self, volume=None, change=None, **kwargs):
        """Sets the overall volume of the sound system.

        Args:
            volume: The new volume level, a floating point value between 0.0
                and 1.0. 1.0 is full volume. 0.0 is mute.
            change: A positive or negative value between 0.0 and 1.0 of a
                change in volume that will be made.
            kwargs: Not used here. Included because this method is often
                called from events which might contain additional kwargs.

        Note that the volume can never be increased above 1.0. This sound
        volume level only affects MPF. You might have to set the overall
        system sound to in the OS.

        """

        old_volume = self.volume

        if volume:
            self.volume = float(volume)
        elif change:
            self.volume += float(change)

        if self.volume > 1.0:
            self.volume = 1.0
        elif self.volume < 0:
            self.volume = 0.0

        display_volume = int(self.volume * self.config['volume_steps'])

        if display_volume == self.config['volume_steps']:
            display_volume = "MAX"
        elif display_volume:
            display_volume = str(display_volume)
        else:
            display_volume = "OFF"  # todo move to config

        # todo change volume of currently playing sounds
        for channel in self.pygame_channels:
            if channel.pygame_channel.get_busy():
                playing_sound = channel.pygame_channel.get_sound()

                new_volume = (1.0 *
                              self.volume *
                              channel.current_sound.config['volume'] *
                              channel.parent_track.volume)

                playing_sound.set_volume(new_volume)

        if self.stream_track and pygame.mixer.music.get_busy():
            new_volume = (1.0 *
                          self.volume *
                          self.stream_track.volume *
                          self.stream_track.current_sound.config['volume'])
            pygame.mixer.music.set_volume(new_volume)

        self.machine.events.post('volume_change', volume=self.volume,
                                 change=old_volume-self.volume,
                                 display_volume=display_volume)

    def get_volume(self):
        return self.volume


class Track(object):
    """Parent class for an MPF track. Each sound track in MPF can be made up
    of one or more Pygame sound channels to support multiple simultaneous
    sounds.

    Args:
        machine: The main machine controller object.
        name: A string of the name this channel will be referred to, such as
            "voice" or "sfx."
        global_channel_list: A python list which keeps track of the global
            Pygame channels in use.
        config: A python dictionary containing the configuration settings for
            this track.
    """

    def __init__(self, machine, name, global_channel_list, config):

        self.log = logging.getLogger('Track.' + name)
        self.log.debug("Creating Track with config: %s", config)
        self.name = name
        self.config = config
        self.pygame_channels = list()
        self.volume = 1
        self.queue = Queue.PriorityQueue()

        if 'simultaneous_sounds' not in self.config:
            self.config['simultaneous_sounds'] = 1

        if 'preload' not in self.config:
            self.config['preload'] = False

        if 'volume' in self.config:
            self.volume = self.config['volume']

        for track in range(self.config['simultaneous_sounds']):
            self.create_channel(machine, global_channel_list)

        machine.events.add_handler('timer_tick', self._tick)

    def create_channel(self, machine, global_channel_list):
        """Factory method which creates a Pygame sound channel to be used with
        this track.

        Args:
            machine: The main machine object.
            global_channel_list: A list which contains the global list of
                Pygame channels in use by MPF.
        """
        next_channel_num = len(global_channel_list)
        this_channel_object = Channel(machine, self, next_channel_num)

        global_channel_list.append(this_channel_object)
        self.pygame_channels.append(this_channel_object)

    def play(self, sound, priority, **settings):
        """Plays a sound on this track.

            Args:
                sound: The MPF sound object you want to play.
                priority: The relative priority of this sound.
                **settings: One or more additional settings for this playback.

        This method will automatically find an available Pygame channel to use.

        If this new sound has a higher priority than the lowest playing sound,
        it will interrupt that sound to play. Otherwise it will be added to the
        queue to be played when a channel becomes available.

        """

        # Make sure we have a sound object. If not we assume the sound is being
        # loaded (is that dumb?) and we add it to the queue so it will be
        # picked up on the next loop.
        if not sound.sound_object:
            self.queue_sound(sound, priority, **settings)
            return

        # We have a sound object. Do we have an available channel?
        found_available_channel = False

        # todo check to see if this sound is already playing and what our
        # settings are for that.

        for channel in self.pygame_channels:  # todo change to generator
            if channel.current_sound_priority == -1:
                found_available_channel = True
                channel.play(sound, priority=priority, **settings)
                break

        # No available channels. What do we do with this sound now? Options:
        # 1. If the priority of the lowest currently-playing sound is lower than
        # ours, kill that sound and replace it with the new one.
        # 2. Add this to the queue, arranged by priority

        if not found_available_channel:
            lowest_channel = min(self.pygame_channels)
            if lowest_channel.current_sound_priority < priority:
                lowest_channel.play(sound, priority=priority, **settings)
            else:
                if sound.expiration_time:
                    exp_time = time.time() + sound.expiration_time
                else:
                    exp_time = None
                self.queue_sound(sound, priority=priority, exp_time=exp_time,
                                 **settings)

    def stop(self, sound):
        try:
            sound.sound_object.stop()
        except AttributeError:
            pass

    def queue_sound(self, sound, priority, exp_time=None, **settings):
        """Adds a sound to the queue to be played when a Pygame channel becomes
        free.

        Args:
            sound: The MPF sound object.
            priority: The priority of this sound.
            exp_time: Real world time of when this sound will expire. (It will
                not play if the queue is freed up after it expires.)
            **settings: Additional settings for this sound's playback.

        Note that this method will insert this sound into a position in the
        queue based on its priority, so highest-priority sounds are played
        first.
        """

        # Note the negative operator in front of priority since this queue
        # retrieves the lowest values first, and MPF uses higher values for
        # higher priorities.
        self.queue.put([-priority, sound, exp_time, settings])

    def get_sound(self):
        """Returns the next sound from the queue to be played.

        Returns: A tuple of the sound object, the priority, and dictionary of
            additional settings for that sound. If the queue is empty, returns
            None.

        This method will ensure that the sound returned has not expired. If the
        next sound in the queue is expired, it removes it and returns the next
        one.
        """
        try:
            next_sound = self.queue.get_nowait()

        except Queue.Empty:
            return

        if not next_sound[2] or next_sound[2] >= time.time():
            return next_sound[1], next_sound[0], next_sound[3]

        else:
            self.get_sound()  # todo this is bad, right?

    def _tick(self):
        if not self.queue.empty():

            sound, priority, settings = self.get_sound()

            self.play(sound, priority=priority, **settings)


class StreamTrack(object):
    """Parent class for MPF's "Stream" track which corresponds to Pygame's
    music channel.

    Args:
        machine: The main machine object.
        config: Python dictionary containing the configuration settings for
            this track.

    Sounds played on this track are streamed from disk rather than loaded into
    memory. This is good for background music since those files can be large
    and there's only one playing at a time.
    """

    def __init__(self, machine, config):

        self.log = logging.getLogger('Streaming Channel')
        self.log.debug("Creating Stream Track with config: %s", config)
        self.machine_sound = machine.sound

        self.config = config
        self.name = 'music'
        self.volume = 1
        self.current_sound = None

        if 'name' in self.config:
            self.name = self.config['name']

        if 'volume' in self.config:
            self.volume = self.config['volume']

        self.config['preload'] = False

    def play(self, sound, **settings):
        """Plays a sound on this track.

        Args:
            sound: The MPF sound object to play.
            **settings: Additional settings for this sound's playback.

        This stream track only supports playing one sound at a time, so if
        you call this when a sound is currently playing, the new sound will
        stop the current sound.
        """

        self.current_sound = sound
        pygame.mixer.music.load(sound.file_name)

        volume = (1.0 *
                  self.volume *
                  sound.config['volume'] *
                  self.machine_sound.volume)

        if 'volume' in settings:
            volume *= settings['volume']

        pygame.mixer.music.set_volume(volume)

        self.log.debug("Playing Sound: %s Vol: %s", sound.file_name,
                      pygame.mixer.music.get_volume())

        if 'loops' not in settings:
            settings['loops'] = 1

        pygame.mixer.music.play(settings['loops'])

    def stop(self, sound=None):
        """Stops the playing sound and resets the current position to the
        beginning.
        """
        pygame.mixer.music.stop()

        # todo add support for fade out

    def pause(self):
        """Pauses the current sound and remembers the current position so
        playback can be resumed from the same point via the unpause() method.
        """
        pygame.mixer.music.pause()

        # todo add support for fade out

    def unpause(self):
        """Resumes playing of a previously-paused sound. If the sound was not
        paused, it starts playing it from the beginning.
        """
        pygame.mixer.music.unpause()

        # todo add support for fade in

    def fadeout(self, ms):
        """Fades the sound out.

        Args:
            ms: The number of milliseconds to fade out the sound.
        """
        pygame.mixer.music.fadeout(ms)

        # todo add support for MPF time duration strings


class Channel(object):
    """Parent class that holds a Pygame sound channel. One or more of these are
    tied to an MPF Track.

    Args:
        machine: The main machine object.
        parent_track: The MPF track object this channel belongs to.
        channel_number: Integer number that is used to identify this channel.
    """

    def __init__(self, machine, parent_track, channel_number):

        self.log = logging.getLogger('Sound Channel ' + str(channel_number))
        self.machine_sound = machine.sound
        self.current_sound_priority = -1
        self.current_sound = None
        self.pygame_channel = pygame.mixer.Channel(channel_number)
        self.parent_track = parent_track

        # configure this pygame channel to post a pygame event when it's done
        # playing a sound
        self.pygame_channel.set_endevent(
            pygame.locals.USEREVENT + channel_number)

        # add a pygame event handler so this channel object gets notified of
        # the above
        machine.register_pygame_handler(
            pygame.locals.USEREVENT + channel_number, self.sound_is_done)

    def __cmp__(self, other):
        # Used so we can sort the channel list by the priority of the current
        # playing sound
        return cmp(self.current_sound_priority, other.current_sound_priority)

    def sound_is_done(self):
        """Indicates that the sound that was playing on this channel is now
        done.

        This is the callback method that's automatically called by Pygame. It
        will check the queue and automatically play any queued sounds."""

        self.current_sound_priority = -1

        if not self.parent_track.queue.empty():

            sound, priority, settings = self.parent_track.get_sound()

            self.play(sound, priority=priority, **settings)

    def play(self, sound, **settings):
        """Plays a sound on this channel.

        Args:
            sound: The sound object to play.
            **settings: Additional settings for this sound's playback.
        """

        self.current_sound = sound
        self.current_sound_priority = settings['priority']

        if 'loops' in settings:
            loops = settings['loops']

        # calculate the volume for this sound

        # start with the sound volume, multiply the overall and track volumes
        volume = (1.0 *
                  self.parent_track.volume *
                  sound.config['volume'] *
                  self.machine_sound.volume)

        if 'volume' in settings:
            volume *= settings['volume']

        # set the sound's current volume
        sound.sound_object.set_volume(volume)

        self.log.debug("Playing Sound: %s Vol: %s", sound.file_name,
                      sound.sound_object.get_volume())

        self.pygame_channel.play(sound.sound_object, loops)


class Sound(Asset):

    def _initialize_asset(self):
        if self.config['track'] in self.machine.sound.tracks:
            self.track = self.machine.sound.tracks[self.config['track']]

        elif self.config['track'] == self.machine.sound.stream_track.name:
            self.track = self.machine.sound.stream_track
        else:
            self.asset_manager.log.critical("Music track not found: %s",
                                            self.config['track'])
            raise Exception()

        self.sound_object = None
        self.priority = 0
        self.expiration_time = None

        if 'volume' not in self.config:
            self.config['volume'] = 1

        if 'max_queue_time' not in self.config:  # todo
            self.config['max_queue_time'] = None

        if 'max_simultaneous_playing' not in self.config:  # todo
            self.config['max_simultaneous_playing'] = None

        if 'fade_in' not in self.config:  # todo
            self.config['fade_in'] = 0

        if 'fade_out' not in self.config:  # todo
            self.config['fade_out'] = 0

        if 'loops' not in self.config:  # todo
            self.config['loops'] = None

        if 'start_time' not in self.config:  # todo
            self.config['start_time'] = None

        if 'end_time' not in self.config:  # todo
            self.config['end_time'] = None

    def do_load(self, callback):
        try:
            self.sound_object = pygame.mixer.Sound(self.file_name)
        except pygame.error:
            self.asset_manager.log.error("Pygame Error for file %s. '%s'",
                                         self.file_name, pygame.get_error())

        self.loaded = True

        if callback:
            callback()

    def _unload(self):
        self.sound_object = None

    def play(self, loops=0, priority=0, fade_in=0, volume=1, **kwargs):
        """Plays this sound.

        Args:
            loops: Integer of how many times you'd like this sound to repeat.
                A value of -1 means it will loop forever.
            priority: The relative priority of this sound which controls what
                happens if the track this sound is playing on is playing the
                max simultaneous sounds.
            fade_in: MPF time string for how long this sound should fade in
                when it starts.
            volume: Volume for this sound as a float between 0.0 and 1.0. Zero
                is mute, 1 is full volume, anything in between is in between.
            **kwargs: Catch all since this method might be used as an event
                callback which could include random kwargs.
        """

        self.asset_manager.log.info("Playing sound. Loops: %s, Priority: %s, "
                                    "Fade in: %s, Vol: %s, kwargs: %s",
                                    loops, priority, fade_in, volume, kwargs)

        if not self.sound_object:
            self.load()

        if 'sound' in kwargs:
            kwargs.pop('sound')

        self.track.play(self, priority=priority, loops=loops, volume=volume,
                        fade_in=fade_in, **kwargs)

    def stop(self, fade_out=0, reset=True, **kwargs):
        """Stops this sound playing.

        Args:
            fade_out: MPF time string for how long this sound will fade out as
                it stops.
            reset: Boolean for whether this sound should reset its playback
                position to the beginning. Default is True.
            **kwargs: Catch all since this method might be used as an event
                callback which could include random kwargs.
        """

        #self.sound_object.stop()

        self.track.stop(self)


asset_class = Sound
asset_attribute = 'sounds'  # self.machine.<asset_attribute>
#display_element_class = ImageDisplayElement
create_asset_manager = True
path_string = 'sounds'
config_section = 'sounds'
file_extensions = ('ogg', 'wav')

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
