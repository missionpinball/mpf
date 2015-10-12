"""Manages the show effects in a pinball machine."""
# show_controller.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf

import logging
import yaml
import time
import sys

from mpf.system.assets import AssetManager, Asset
from mpf.system.config import Config


class ShowController(object):
    """Manages all the shows in a pinball machine.

    'shows' are coordinated display & event sequences. The ShowController
    handles priorities, restores, running and stopping Shows, etc. There should
    be only one per machine.

    Args:
        machine: Parent machine object.
    """
    def __init__(self, machine):
        self.log = logging.getLogger("ShowController")
        self.machine = machine

        self.event_queue = set()

        self.running_shows = []

        self.initialized = False  # We need to run some stuff once but we can't
        # do it here since this loads before our light machine items are created

        self.queue = []  # contains list of dics for things that need to be
        # serviced in the future, including: (not all are always used)
        # lightname
        # priority
        # blend
        # fadeend
        # dest_color
        # color
        # playlist
        # action_time

        self.current_time = time.time()
        # we use a common system time for the entire show system so that every
        # "current_time" of a single update cycle is the same everywhere. This
        # ensures that multiple shows, scripts, and commands start in-sync
        # regardless of any processing lag.

        # register for events
        self.machine.events.add_handler('timer_tick', self._tick)
        self.machine.events.add_handler('init_phase_5',
                                        self._initialize)

        # Tell the mode controller that it should look for light_player items in
        # modes.
        self.machine.mode_controller.register_start_method(self.process_shows_from_config,
                                                 'show_player')

        # Create the show AssetManager
        self.asset_manager = AssetManager(
                                          machine=self.machine,
                                          config_section='shows',
                                          path_string='shows',
                                          asset_class=Show,
                                          asset_attribute='shows',
                                          file_extensions=('yaml',)
                                          )

    def _initialize(self):
        # Sets up everything that has to be instantiated first

        if 'show_player' in self.machine.config:
            self.process_shows_from_config(self.machine.config['show_player'])

    def play_show(self, show, mode=None, repeat=False, priority=0, blend=False,
                  hold=False, tocks_per_sec=30, start_location=None,
                  num_repeats=0, **kwargs):

        if 'show_priority' in kwargs:
            priority += int(kwargs['show_priority'])

        if show in self.machine.shows:
            if 'stop_key' in kwargs:
                self.machine.shows[show].stop_key = kwargs['stop_key']

            self.log.debug("Playing Show: %s. Priority %s", show, priority)

            self.machine.shows[show].play(repeat=repeat, priority=priority,
                                          blend=blend, hold=hold,
                                          tocks_per_sec=tocks_per_sec,
                                          start_location=start_location,
                                          num_repeats=num_repeats,
                                          mode=mode)

        elif isinstance(show, Show):
            if 'stop_key' in kwargs:
                show.stop_key = kwargs['stop_key']

            self.log.debug("Playing Show: %s. Priority %s", show.file_name,
                           priority)

            show.play(repeat=repeat, priority=priority, blend=blend, hold=hold,
                      tocks_per_sec=tocks_per_sec,
                      start_location=start_location, num_repeats=num_repeats,
                      mode=mode)
        else:  # no show by that name to play
            pass

    def stop_show(self, show, reset=True, hold=False, **kwargs):

        self.log.debug("Stopping Show: %s", show)

        if show in self.machine.shows:
            self.machine.shows[show].stop(reset=reset, hold=hold)

    def stop_shows_by_key(self, key):
        for show in self.running_shows:
            if show.stop_key == key:
                self.log.debug("Stopping Show: %s", show)
                show.stop()

    def process_shows_from_config(self, config, mode=None, priority=0):
        self.log.debug("Processing show_player configuration. Priority: %s",
                       priority)

        key_list = list()

        for event, settings in config.iteritems():
            if type(settings) is dict:
                settings['priority'] = priority
                settings['stop_key'] = mode
                key_list.append(self.add_show_player_show(event, settings,
                                                          mode))
            elif type(settings) is list:
                for entry in settings:
                    entry['priority'] = priority
                    entry['stop_key'] = mode
                    key_list.append(self.add_show_player_show(event, entry,
                                                              mode))

        return self.unload_show_player_shows, (key_list, mode)

    def unload_show_player_shows(self, removal_tuple):

        key_list, show_key = removal_tuple

        self.log.debug("Removing show_player events")
        self.machine.events.remove_handlers_by_keys(key_list)

        if show_key:
            self.stop_shows_by_key(show_key)

    def add_show_player_show(self, event, settings, mode=None):
        if 'priority' in settings:
            settings['show_priority'] = settings['priority']

        if 'show' in settings:
            settings['show'] = settings['show'].lower()

        if 'script' in settings:
            settings['script'] = settings['script'].lower()

        if 'action' in settings and settings['action'] == 'stop':
            key = self.machine.events.add_handler(event, self.stop_show,
                                                  **settings)

        else:  # action = 'play'
            key = self.machine.events.add_handler(event, self.play_show,
                                                  mode=mode, **settings)

        return key

    def _run_show(self, show):
        # Internal method which starts a Show

        # if the show is already playing, it does not try to play again
        if show in self.running_shows:
            return

        show.ending = False
        show.current_repeat_step = 0
        show.last_action_time = self.current_time
        # or in the advance loop?

        self.running_shows.append(show)
        self.running_shows.sort(key=lambda x: x.priority)

    def _end_show(self, show, reset=True):
        # Internal method which ends a running Show

        self.running_shows = filter(lambda x: x != show, self.running_shows)

        if reset:
            show.current_location = 0

        if show.callback:
            show.callback()

    def _tick(self):
        #Runs once per machine loop and services any show updates that are
        #needed.

        self.current_time = time.time()
        # we calculate current_time one per loop because we want every action
        # in this loop to write the same "last action time" so they all stay
        # in sync. Also we truncate to 3 decimals for ease of comparisons later

        # Check the running Shows
        for show in self.running_shows:
            # we use a while loop so we can catch multiple action blocks
            # if the show tocked more than once since our last update
            while show.next_action_time <= self.current_time:

                # add the current location to the list to be serviced
                # show.service_locations.append(show.current_location)
                # advance the show to the current time
                show.advance()

                if show.ending:
                    break

        # Check to see if we need to service any items from our queue. This can
        # be single commands or playlists

        # Make a copy of the queue since we might delete items as we iterate
        # through it
        queue_copy = list(self.queue)

        for item in queue_copy:
            if item['action_time'] <= self.current_time:
                # If the queue is for a fade, we ignore the current color
                if item.get('playlist', None):
                    item['playlist'].advance()

                # We have to check again since one of these advances could have
                # removed it already
                if item in self.queue:
                    self.queue.remove(item)

        self._do_update()

    def _add_to_event_queue(self, event):
        # Since events don't blend, this is easy
        self.event_queue.add(event)

    def _do_update(self):
        if self.event_queue:
            self._fire_events()

    def _fire_events(self):
        for event in self.event_queue:
            #self.machine.events.post(event)
            self.machine.send('trigger', name=event)
        self.event_queue = set()


class Show(Asset):

    load_priority = 50  # lower than default (100) so shows go second

    def __init__(self, machine, config, file_name, asset_manager, actions=None):
        if not actions:
            super(Show, self).__init__(machine, config, file_name,
                                       asset_manager)
        else:
            self.machine = machine
            self.config = config
            self.file_name = file_name
            self.asset_manager = asset_manager

            self._initialize_asset()
            self.do_load(callback=None, show_actions=actions)

    def _initialize_asset(self):

        self.tocks_per_sec = 30  # how many steps per second this show runs at
        # you can safely read this value to determine the current playback rate
        # But don't update it directly to change the speed of a running show.
        # Use the change_speed() method instead.
        self.secs_per_tock = 0  # calculated based on tocks_per_sec
        self.repeat = False  # whether this show repeats when finished
        self.num_repeats = 0  # if self.repeat=True, how many times it repeats
        self.current_repeat_step = 0  # tracks which repeat we're on, used with
        # num_repeats above
        self.hold = False  # hold the item states when the show ends.
        self.priority = 0  # relative priority of this show
        self.ending = False  # show will end after the current tock ends

        self.current_location = 0  # index of which step (tock) a running show is
        self.last_action_time = 0.0  # when the last action happened
        self.total_locations = 0  # total number of action locations
        self.current_tock = 0  # index of which tock a running show is in
        self.next_action_time = 0  # time of when the next action happens
        self.callback = None  # if the show should call something when it ends
        # naturally. (Not invoked if show is manually stopped)

        self.last_slide = None
        self.stop_key = None

        self.loaded = False
        self.notify_when_loaded = set()
        self.loaded_callbacks = list()
        self.show_actions = list()

        self.mode = None

    def do_load(self, callback, show_actions=None):

        self.show_actions = list()

        self.asset_manager.log.debug("Loading Show %s", self.file_name)

        if not show_actions:
            show_actions = self.load_show_from_disk()

        for step_num in range(len(show_actions)):
            step_actions = dict()

            step_actions['tocks'] = show_actions[step_num]['tocks']

            # look for empty steps. If we find them we'll just add their tock
            # time to the previous step.

            if len(show_actions[step_num]) == 1:  # 1 because it still has tocks

                show_actions[-1]['tocks'] += step_actions['tocks']
                continue

            # Events
            # make sure events is a list of strings
            if ('events' in show_actions[step_num] and
                    show_actions[step_num]['events']):

                event_list = (Config.string_to_lowercase_list(
                    show_actions[step_num]['events']))

                step_actions['events'] = event_list

            # slide_player
            if ('display' in show_actions[step_num] and
                    show_actions[step_num]['display']):

                step_actions['display'] = (
                    self.machine.display.slide_builder.preprocess_settings(
                        show_actions[step_num]['display']))

            # Sounds
            if ('sounds' in show_actions[step_num] and
                    show_actions[step_num]['sounds']):

                # make sure we have a list of dicts
                if type(show_actions[step_num]['sounds']) is dict:
                    show_actions[step_num]['sounds'] = (
                        [show_actions[step_num]['sounds']])

                for entry in show_actions[step_num]['sounds']:

                    try:
                        entry['sound'] = self.machine.sounds[entry['sound']]
                    except KeyError:
                        self.asset_manager.log.critical("Invalid sound '%s' "
                                                        "found in show. ",
                                                        entry['sound'])
                        raise

                step_actions['sounds'] = show_actions[step_num]['sounds']

            self.show_actions.append(step_actions)

        # count how many total locations are in the show. We need this later
        # so we can know when we're at the end of a show
        self.total_locations = len(self.show_actions)

        self.loaded = True

        if callback:
            callback()

        self._asset_loaded()
        # why do we need this and the one above?

    def _unload(self):
        self.show_actions = None

    def play(self, repeat=False, priority=0, blend=False, hold=False,
             tocks_per_sec=30, start_location=None, callback=None,
             num_repeats=0, mode=None):
        """Plays a Show. There are many parameters you can use here which
        affect how the show is played. This includes things like the playback
        speed, priority, whether this show blends with others, etc. These are
        all set when the show plays. (For example, you could have a Show
        file which lights a bunch of lights sequentially in a circle pattern,
        but you can have that circle "spin" as fast as you want depending on
        how you play the show.)

        Args:
            repeat: Boolean of whether the show repeats when it's done.
            priority: Integer value of the relative priority of this show. If
                there's ever a situation where multiple shows want to control
                the same item, the one with the higher priority will win.
                ("Higher" means a bigger number, so a show with priority 2 will
                override a priority 1.)
            blend: Boolean which controls whether this show "blends" with lower
                priority shows and scripts. For example, if this show turns a
                light off, but a lower priority show has that light set to blue,
                then the light will "show through" as blue while it's off here.
                If you don't want that behavior, set blend to be False. Then off
                here will be off for sure (unless there's a higher priority show
                or command that turns the light on). Note that not all item
                types blend. (You can't blend a coil or event, for example.)
            hold: Boolean which controls whether the lights or LEDs remain in
                their final show state when the show ends.
            tocks_per_sec: Integer of how fast your show runs ("Playback speed,"
                in other words.) Your Show files specify action times in terms
                of 'tocks', like "make this light red for 3 tocks, then off for
                4 tocks, then a different light on for 6 tocks. When you play a
                show, you specify how many tocks per second you want it to play.
                Default is 30, but you might even want tocks_per_sec of only 1
                or 2 if your show doesn't need to move than fast. Note this does
                not affect fade rates. So you can have tocks_per_sec of 1 but
                still have lights fade on and off at whatever rate you want.
                Also the term "tocks" was chosen so as not to confuse it with
                "ticks" which is used by the machine run loop.
            start_location: Integer of which position in the show file the show
                should start in. Usually this is 0 but it's nice to start part
                way through. Also used for restarting shows that you paused.
            callback: A callback function that is invoked when the show is
                stopped.
            num_repeats: Integer of how many times you want this show to repeat
                before stopping. A value of 0 means that it repeats
                indefinitely. Note this only works if you also have
                repeat=True.

        """
        if not self.loaded:
            self.add_loaded_callback(self.play,
                                     repeat=repeat,
                                     priority=priority,
                                     blend=blend,
                                     hold=hold,
                                     tocks_per_sec=tocks_per_sec,
                                     start_location=start_location,
                                     callback=callback,
                                     num_repeats=num_repeats)
            self.load()
            return False

        self.repeat = repeat
        self.priority = int(priority)
        self.blend = blend
        self.hold = hold
        self.tocks_per_sec = tocks_per_sec
        self.secs_per_tock = 1/float(tocks_per_sec)
        self.callback = callback
        self.num_repeats = num_repeats
        self.mode = mode
        if start_location is not None:
            # if you don't specify a start location, it will start where it
            # left off (if you stopped it with reset=False). If the show has
            # never been run, it will start at 0 per the initialization
            self.current_location = start_location

        self.machine.show_controller._run_show(self)

    def load_show_from_disk(self):

        # todo add exception handling
        # create central yaml loader, or, even better, config loader

        show_actions = yaml.load(open(self.file_name, 'r'))

        return show_actions

    def add_loaded_callback(self, loaded_callback, **kwargs):
        self.asset_manager.log.debug("Adding a loaded callback: %s, %s",
                                     loaded_callback, kwargs)
        for c, k in self.loaded_callbacks:
            if c == loaded_callback and k == kwargs:
                return False

        self.loaded_callbacks.append((loaded_callback, kwargs))
        return True

    def _asset_loaded(self):
        self.asset_manager.log.debug("Show is now loaded. Processing "
                                     "loaded_callbacks... %s",
                                     self.loaded_callbacks)
        for callback, kwargs in self.loaded_callbacks:
            callback(**kwargs)

        self.loaded_callbacks = list()

    def stop(self, reset=True, hold=None):
        """Stops a Show.

        Note you can also use this method to clear a stopped show's held lights
        and LEDs by passing hold=False.

        Args:
            reset: Boolean which controls whether the show will reset its
                current position back to zero. Default is True.
            hold: Boolean which controls whether the current slide will be kept
                in the display's list of slides once the show stops. If None,
                it will use the Show's 'hold' attribute value. (That value
                defaults to False, which is what you want in most cases since
                you typically don't want the show's slide(s) hanging around
                once the show ends.

        """
        self.machine.show_controller._end_show(self, reset)

        if hold is False or (not hold and not self.hold):
            self.clear_display()

    def clear_display(self):
        if self.last_slide:
            self.last_slide.remove()
        self.last_slide = None

    def change_speed(self, tocks_per_sec=1):
        """Changes the playback speed of a running Show.

        Args:
            tocks_per_sec: The new tocks_per_second play rate.

        If you want to change the playback speed by a percentage, you can
        access the current tocks_per_second rate via Show's
        tocks_per_second variable. So if you want to double the playback speed
        of your show, you could do something like:

            self.your_show.change_speed(self.your_show.tocks_per_second*2)

        Note that you can't just update the show's tocks_per_second directly
        because we also need to update self.secs_per_tock.
        """
        self.tocks_per_sec = tocks_per_sec
        self.secs_per_tock = 1/float(tocks_per_sec)

    def advance(self):
        # Internal method which advances the show to the next step
        if self.ending:
            self.stop()
            return

        action_loop_count = 0  # Tracks how many loops we've done here

        while (self.next_action_time <=
               self.machine.show_controller.current_time):
            action_loop_count += 1

            # Set the next action time & step to the next location
            self.next_action_time = ((self.show_actions[self.current_location]
                                     ['tocks'] * self.secs_per_tock) +
                                     self.last_action_time)
            self.last_action_time = self.next_action_time

        # create a dictionary of the current items of each type, combined with
        # the show details, that we can throw up to our queue

        for item_type, item_dict in (self.show_actions[self.current_location].
                                     iteritems()):

            if item_type == 'events':

                for event in item_dict:  # item_dict is actually a list here
                    self.machine.show_controller._add_to_event_queue(event)

            elif item_type == 'display':

                self.last_slide = (
                    self.machine.display.slide_builder.build_slide(item_dict,
                    mode=self.mode,
                    priority=self.priority))

            elif item_type == 'sounds':

                for sound_entry in item_dict:

                    if ('action' in sound_entry and
                            sound_entry['action'].lower() == 'stop'):
                        sound_entry['sound'].stop(**sound_entry)

                    else:
                        sound_entry['sound'].play(**sound_entry)

        # increment this show's current_location pointer and handle repeats

        # if we're at the end of the show
        if self.current_location == self.total_locations-1:

            # if we're repeating with an unlimited number of repeats
            if self.repeat and self.num_repeats == 0:
                self.current_location = 0

            # if we're repeating, but only for a certain number of times
            elif self.repeat and self.num_repeats > 0:
                # if we haven't hit the repeat limit yet
                if self.current_repeat_step < self.num_repeats-1:
                    self.current_location = 0
                    self.current_repeat_step += 1
                else:
                    self.ending = True
            else:
                self.ending = True
                return  # no need to continue if the show's over

        # else, we're in the middle of a show
        else:
            self.current_location += 1

        # If our Show is running so fast that it has done a complete
        # loop, then let's just break out of the loop
        if action_loop_count == self.total_locations:
            return


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
