"""MPF plugin for the sound controller."""
# sound.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import os
import time
import threading
import Queue

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

    # todo add check for Sound in config?


class SoundController(object):
    """Parent class for the sound controller which is responsible for all audio,
    sounds, and music in the machine. There is only one of these per machine.

    Args:
        machine: The main machine controller object.

    """

    def __init__(self, machine):
        self.log = logging.getLogger('SoundController')
        self.machine = machine

        if 'SoundSystem' not in self.machine.config:
            self.config = dict()
            return  # todo move to preload_check()

        self.machine.sound = self
        self.config = self.machine.config['SoundSystem']

        self.tracks = dict()  # k = track name, v = track obj
        self.stream_track = None
        self.pygame_channels = list()

        self.volume = 1.0

        if 'volume_steps' not in self.config:
            self.config['volume_steps'] = 20

        if 'initial_volume' in self.config:
            self.volume = self.config['initial_volume']

        self.set_volume(volume=self.volume)

        self.machine.request_pygame()

        self.machine.events.add_handler('pygame_initialized', self._initialize)

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

    def _initialize(self):
        # Initialize the sound controller. Not done in __init__() because we
        # need Pygame to be setup first.

        frequency, bits, channels = pygame.mixer.get_init()

        self.log.info("Pygame Sound Mixer configuration. Freq: %s, Bits: %s, "
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

        # Load sounds
        self._load_sounds()
        self._setup_soundplayer()

    def _load_sounds(self):
        # Loads the sound files by loading everything it finds on disk. It will
        # also look for (optional) associated configuration options for each
        # file. Sound files on disk are in subfolders by track.

        sound_path = os.path.join(self.machine.machine_path,
                                  self.machine.config['MPF']['paths']['sounds'])

        self.log.info("Loading sound files from: %s", sound_path)

        self.machine.sounds = dict()
        self.sound_file_map = dict()

        if 'Sounds' in self.machine.config:
            self.sound_file_map = self.create_sound_file_map(
                                                self.machine.config['Sounds'])

        found_a_sound = False  # tracks whether we found any sounds at all

        for root, path, files in os.walk(sound_path, followlinks=True):
            found_a_sound = True
            for f in files:
                if f.endswith('.ogg') or f.endswith('.wav'):
                    # todo should probably not hardcode that
                    file_name = os.path.join(root, f)
                    self.load(file_name)

        if not found_a_sound:
            self.log.warning("No sound files found.")

    def _setup_soundplayer(self):
        # Sets up sounds that are played automatically via the SoundPlayer entry
        # in the config file.
        if 'SoundPlayer' in self.machine.config:
            for gamesound in self.machine.config['SoundPlayer']:
                self.log.debug("Configuring SoundPlayer '%s'", gamesound)
                self.setup_game_sound(self.machine.config['SoundPlayer'][gamesound])

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

    def create_sound_file_map(self, config):
        """Creates a mapping dictionary of sound file names to sound entries.
        This is done to speed up searching for sounds by filename later.

        Args:
            config: Python dictionary which holds its configuration.
        """

        self.log.debug("Creating the sound file mapping dictionary")

        sound_map = dict()

        for track, sounds in config.iteritems():
            if sounds:
                for k, v in sounds.iteritems():
                    sound_map[v['file']] = (track, k)

        self.log.debug("Sound file mapping dictionary is complete")

        return sound_map

    def load(self, file_name):
        """Creates an MPF sound object from a file name.

        Args:
            file_name: A string of the file name (optionally with path)

        Note: This is very preliminary. Not done yet.

        """
        self.log.info("Loading sound file: %s", file_name)
        track = os.path.basename(os.path.split(file_name)[0])

        config = dict()

        short_name = os.path.split(file_name)[1]

        # todo change the track name so it's the first subfolder under the root
        # sounds folder, rather than just the last folder.

        # do we have a configuration for this file?
        if short_name in self.sound_file_map:
            name = self.sound_file_map[short_name][1]
            track = self.sound_file_map[short_name][0]
            config = self.machine.config['Sounds'][track][name]

        else:
            name = short_name.split('.')[0]

        if 'track' in config:
            track = config['track']

        if track in self.tracks:
            track = self.tracks[track]
        elif track == self.stream_track.name:
            track = self.stream_track

        if 'volume' not in config:
            config['volume'] = 1
        elif config['volume'] > 2:
            config['volume'] = 2

        self.machine.sounds[name] = Sound(name=name,
                                          file_name=file_name,
                                          track=track,
                                          config=config)

    def setup_game_sound(self, config):
        """Sets up game sounds from the config file.

        Args:
            config: Python dictionary which contains the game sounds settings.
        """

        if 'sound' not in config:
            return False
        else:
            config['sound'] = self.machine.sounds[config['sound']]

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

        if 'start_events' in config and config['start_events'] is not None:
            for event in self.machine.string_to_list(config['start_events']):
                self.machine.events.add_handler(event,
                                        config['sound'].play,
                                        loops=config['loops'],
                                        priority=config['priority'],
                                        fade_in=config['fade_in'],
                                        volume=config['volume'])

        if 'stop_events' in config and config['stop_events'] is not None:
            for event in self.machine.string_to_list(config['stop_events']):
                self.machine.events.add_handler(event,
                                                config['sound'].stop,
                                                fade_out=config['fade_out'])

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
            self.volume = volume
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

        pygame.mixer.music.set_volume(volume)

        if 'loops' not in settings:
            settings['loops'] = 1

        pygame.mixer.music.play(settings['loops'])

    def stop(self):
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

        self.log.info("Playing Sound: %s Vol: %s", sound.file_name, volume)

        # set the sound's current volume
        sound.sound_object.set_volume(volume)

        self.pygame_channel.play(sound.sound_object, loops)


class Sound(object):
    """Parent class for a Sound object in MPF.

    Args:
        file_name: String of the file name and path for the sound file.
        track: not yet implemented
        volume:
        preload: Boolean which controls whether the sound file will be
        preloaded into memory. This makes it so the sound can be played
        instantly, but with a penalty of memory usage to store the file.

    Note: This class is very basic now. Much more work to do.
    """

    def __init__(self, name, file_name, track, config):
        self.name = name
        self.file_name = file_name
        self.track = track
        self.config = config
        self.sound_object = None
        self.priority = 0
        self.expiration_time = None
        self.tags = list()

        # if this sound doesn't have a preload setting, pull the default from
        # the track
        if 'preload' not in self.config:
            self.config['preload'] = self.track.config['preload']

        if 'tags' in self.config:  # todo
            self.tags = self.config['tags']  # todo verify this

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

        if 'unload_events' not in self.config:  # todo
            self.config['unload_events'] = None

        if 'load_events' not in self.config:  # todo
            self.config['load_events'] = None

        if self.config['preload']:  # todo
            self.load()

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

        if not self.sound_object:
            self.load()

        self.track.play(self, priority=priority, loops=loops)

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
        pass
        # todo

    def load(self):
        """Loads this sound file from disk into memory.

        A sound in MPF must be loaded before it can be played. If you set
        preload to True when this sound was created, this method will be called
        then. If not, then this method is automatically called when the sound
        is played.

        This message creates a new thread to load the sound in the background
        so MPF doesn't hang while the sound file is being loaded.
        """
        loader = threading.Thread(name='loader', target=self._load_thread)
        loader.daemon = True
        loader.start()

    def unload(self):
        """Unloads this sound file from memory.

        This method does not destroy this sound object, rather, it only frees
        up the memory that the actual sound file was using. You can still play
        this sound even after you unload the sound file, either by manually
        calling the load() method or by just playing it (where the load()
        method will be called manually.)
        """
        self.sound_object = None

    def _load_thread(self):
        self.sound_object = pygame.mixer.Sound(self.file_name)


# The MIT License (MIT)

# Copyright (c) 2013-2014 Brian Madden and Gabe Knuth

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
