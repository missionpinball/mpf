"""MPF plugin for the sound controller."""
# sound.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
import os
import time

# todo do not set toggle keys if real hw is being used.

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
    """

    def __init__(self, machine):
        self.log = logging.getLogger('Sound')
        self.machine = machine

        self.machine.request_pygame()

        self.machine.events.add_handler('pygame_initialized', self._initialize)

        # Get the pygame pre-initiaiization audio requests in
        # 0 is the 'auto' setting for all of these
        if ('buffer' not in self.machine.config['Sound'] or
                self.machine.config['Sound']['buffer'] == 'auto'):
            self.machine.config['Sound']['buffer'] = 0

        if ('bits' not in self.machine.config['Sound'] or
                self.machine.config['Sound']['bits'] == 'auto'):
            self.machine.config['Sound']['bits'] = 0

        if ('frequency' not in self.machine.config['Sound'] or
                self.machine.config['Sound']['frequency'] == 'auto'):
            self.machine.config['Sound']['frequency'] = 0

        # todo add channels

        pygame.mixer.pre_init(frequency=self.machine.config['Sound']['frequency'],
                              size=self.machine.config['Sound']['bits'],
                              buffer=self.machine.config['Sound']['buffer']
                              )

    def _initialize(self):
        # Initialized the sound controller. Not done in __init__() because we
        # need Pygame to be setup first.

        # If the sound has an associated config then we'll use that to set it
        # up. Otherwise we'll set up that sound with generic settings

        frequency, bits, channels = pygame.mixer.get_init()

        self.log.debug("Pygame Sound Mixer configuration. Freq: %s, Bits: %s, "
                       "Channels: %s", frequency, bits, channels)

        sound_path = os.path.join(self.machine.machine_path,
                                  self.machine.config['MPF']['paths']['sounds'])

        self.log.debug("Loading sound files from: %s", sound_path)

        self.machine.sounds = dict()
        self.sound_file_map = dict()

        if 'Sounds' in self.machine.config:
            self.sound_file_map = self.create_sound_file_map(
                                                self.machine.config['Sounds'])

        found_a_sound = False
        load_start = time.time()
        count = 0

        for root, path, files in os.walk(sound_path, followlinks=True):
            found_a_sound = True
            for f in files:
                if f.endswith('.ogg') or f.endswith('.wav'):
                    # todo should probably not hardcode that
                    file_name = os.path.join(root, f)
                    self.load(file_name)
                    count += 1

        self.log.info("Loaded %s sounds in %s secs", count,
                      round(time.time() - load_start, 3))

        if not found_a_sound:
            self.log.warning("No sound files found.")

        # Set up game sounds
        if 'GameSounds' in self.machine.config:
            for gamesound in self.machine.config['GameSounds']:
                self.log.debug("Configuring GameSound '%s'", gamesound)
                self.setup_game_sound(self.machine.config['GameSounds'][gamesound])

    def create_sound_file_map(self, config):
        """Creates a mapping dictionary of sound file names to sound entries.
        This is done to speed up searching for sounds by filename later.

        Args:
            config: Python dictionary which holds its configuration.
        """

        self.log.debug("Creating the sound file mapping dictionary")

        sound_map = dict()

        for k, v in config.iteritems():
            sound_map[v['file']] = k

        self.log.debug("Sound file mapping dictionary is complete")

        return sound_map

    def load(self, file_name):
        """Creates an MPF sound object from a file name.

        Args:
            file_name: A string of the file name (optionally with path)

        Note: This is very preliminary. Not done yet.

        """

        self.log.debug("Loading sound file: %s", file_name)

        config = dict()

        short_name = os.path.split(file_name)[1]

        # do we have a configuration for this file?

        if short_name in self.sound_file_map:
            name = self.sound_file_map[short_name]
            config = self.machine.config['Sounds'][name]

        else:
            name = short_name.split('.')[0]

        if 'channel' not in config:
            config['channel'] = 'sfx'

        if 'volume_offset' not in config:
            config['volume_offset'] = 0

        self.machine.sounds[name] = Sound(file_name, config['channel'],
                                          config['volume_offset'])

    def setup_game_sound(self, config):
        """Sets up game sounds from the config file. More work to be done here.
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

        if 'volume_offset' not in config or config['volume_offset'] is None:
            config['volume_offset'] = 0

        if 'start_events' in config and config['start_events'] is not None:
            for event in self.machine.string_to_list(config['start_events']):
                self.machine.events.add_handler(event,
                                        config['sound'].play,
                                        loops=config['loops'],
                                        priority=config['priority'],
                                        fade_in=config['fade_in'],
                                        channel=config['channel'],
                                        volume_offset=config['volume_offset'])

        if 'stop_events' in config and config['stop_events'] is not None:
            for event in self.machine.string_to_list(config['stop_events']):
                self.machine.events.add_handler(event,
                                                config['sound'].stop,
                                                fade_out=config['fade_out'])


class Sound(object):
    """Parent class for a Sound object in MPF.

    Args:
        file_name: String of the file name and path for the sound file.
        channel: not yet implemented
        volume_offset: not yet implemented
        preload: Boolean which controls whether the sound file will be
        preloaded into memory. This makes it so the sound can be played
        instantly, but with a penalty of memory usage to store the file.

    Note: This class is very basic now. Much more work to do.
    """

    def __init__(self, file_name, channel, volume_offset, preload=True):
        self.file_name = file_name
        self.channel = channel
        self.volume_offset = volume_offset
        self.sound = None

        if preload:
            self.load()

    def play(self, loops=0, priority=0, fade_in=0, channel='auto',
             volume_offset=0, **kwargs):

        # todo fade_in

        if not self.sound:
            self.load()

        self.sound.play(loops=loops)

        # todo add priority
        # todo add channel, if channel is busy, do we interrupt?
        # todo need to add some kind of queue for each channel

    def stop(self, fade_out=0, reset=True, **kwargs):
        self.sound.stop()
        # todo options

    def load(self):
        self.sound = pygame.mixer.Sound(self.file_name)

    def unload(self):
        self.sound = None


class Music(object):
    pass


class Channel(object):
    pass

    # volume
    # priority
    # ducking
    # queue


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
