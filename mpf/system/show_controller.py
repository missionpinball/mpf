"""Manages the show effects in a pinball machine."""
# show_controller.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
import yaml
import weakref
import time
import os


class ShowController(object):
    """Manages all the shows in a pinball machine.

    'Shows' are coordinated light, flasher, coil, event, audio, and DMD effects.
    The ShowController handles priorities, restores, running and stopping
    Shows, etc. There should be only one per machine.

    Args:
        machine: Parent machine object.

    """
    def __init__(self, machine):
        self.log = logging.getLogger("ShowController")
        self.machine = machine
        self.registered_shows = []
        self.machine.shows = dict()  # Holds english names which map to shows

        self.light_queue = []
        self.led_queue = []
        self.event_queue = set()
        self.coil_queue = set()

        self.light_update_list = []
        self.led_update_list = []

        self.running_shows = []
        self.light_priorities = {}  # dictionary which tracks the priorities of
        # whatever last set each light in the machine
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
        self.active_scripts = []  # list of active scripts that have been
        # converted to Shows. We need this to facilitate removing shows when
        # they're done, since programmers don't use a name for scripts like
        # they do with shows. active_scripts is a list of dictionaries, with
        # the following k/v pairs:
        # lightname - the light the script is applied to
        # priority - what priority the script was running at
        # show - the associated Show object for that script
        self.manual_commands = []  # list that holds the last states of any
        # lights that were set manually. We keep track of this so we can restore
        # lower priority lights when shows end or need to be blended.
        # Each entry is a dictionary with the following k/v pairs:
        # lightname
        # color - the current color *or* fade destination color
        # priority
        # fadeend - (optional) realtime of when the fade should end
        self.current_time = time.time()
        # we use a common system time for the entire light system so that every
        # "current_time" of a single update cycle is the same everywhere. This
        # ensures that multiple shows, scripts, and commands start in-sync
        # regardless of any processing lag.

        # register for events
        self.machine.events.add_handler('timer_tick', self._tick)
        self.machine.events.add_handler('machine_init_phase2',
                                        self._initialize)

    def _initialize(self):
        for light in self.machine.lights:
            self.light_priorities[light.name] = 0
        self.initialized = True

        # Load all the shows in the machine folder
        if self.machine.config['MPF']['auto_load_shows']:
            self.load_shows(os.path.join(
                self.machine.options['machinepath'],
                self.machine.config['MPF']['paths']['shows']))

    def _run_show(self, show):
        # Internal method which starts a Show
        show.running = True
        show.ending = False
        show.current_repeat_step = 0
        show.last_action_time = self.current_time
        # or in the advance loop?
        self.running_shows.append(show)  # should this be a set?
        self.running_shows.sort(key=lambda x: x.priority)

    def _end_show(self, show, reset=True):
        # Internal method which ends a running Show

        running_shows_copy = list(self.running_shows)

        if show in running_shows_copy:
            self.running_shows.remove(show)
            show.running = False
             # Restore the lights not "holding" the final states
            if not show.hold:
                for light in show.light_states:
                    if light.cache['priority'] < show.priority:
                        light.restore()
                for led in show.led_states:
                    if led.cache['priority'] < show.priority:
                        led.restore()

        # todo need to make the restore so it checks other lower priority shows

        if reset:
            show.current_location = 0

        # if this show that's ending was from a script, remove it from the
        # active_scripts list

        # Make a copy of the active scripts object since we're potentially
        # deleting from it while we're also iterating through it.
        active_scripts_copy = list(self.active_scripts)

        for entry in active_scripts_copy:
            if entry['show'] == show:
                self.active_scripts.remove(entry)

        if show.callback:
            show.callback()

    def _tick(self):
        """Runs once per machine loop and services any light updates that are
        needed. This checks several places:

        1. Running Shows
        2. The ShowController queue for any future commands that should be
        processed now.

        """
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
                show._advance()

                if not show.running:
                    # if we hit the end of the show, we can stop
                    break

        # Check to see if we need to service any items from our queue. This can
        # be single commands or playlists

        # Make a copy of the queue since we might delete items as we iterate
        # through it
        queue_copy = list(self.queue)

        for item in queue_copy:
            if item['action_time'] <= self.current_time:
                # If the queue is for a fade, we ignore the current color
                if item.get('fadeend', None):
                    self._add_to_update_list({'lightname': item['lightname'],
                                             'priority': item['priority'],
                                             'blend': item.get('blend', None),
                                             'fadeend': item.get('fadeend', None),
                                             'dest_color': item.get('dest_color',
                                                                    None)})
                elif item.get('color', None):
                    self._add_to_update_list({'lightname': item['lightname'],
                                             'priority': item['priority'],
                                             'color': item.get('color', None)})
                elif item.get('playlist', None):
                    item['playlist']._advance()

                # We have to check again since one of these advances could have
                # removed it already
                if item in self.queue:
                    self.queue.remove(item)

        self._do_update()

    def _add_to_light_update_list(self, light, brightness, priority, blend):
        # Adds an update to our update list, with intelligence that if the list
        # already contains an update for this lightname & priority combination,
        # it deletes it first. This is done so if the machine loop is running
        # slower than our updates are coming in, we only keep the most recent
        # entry.
        for item in self.light_update_list:
            if item['light'] == light and item['priority'] == priority:
                self.light_update_list.remove(item)
        self.light_update_list.append({'light': light,
                                       'brightness': brightness,
                                       'priority': priority,
                                       'blend': blend})  # remove blend?

    def _add_to_led_update_list(self, led, color, fade_ms, priority, blend):
        # See comment from above method
        for item in self.led_update_list:
            if item['led'] == led and item['priority'] == priority:
                self.led_update_list.remove(item)
        self.led_update_list.append({'led': led,
                                     'color': color,
                                     'fade_ms': fade_ms,
                                     'priority': priority,
                                     'blend': blend})

    def _add_to_event_queue(self, event):
        # Since events don't blend, this is easy
        self.event_queue.add(event)

    def _add_to_coil_queue(self, coil, action):
        # Same goes for coils
        self.coil_queue.add((coil, action))
        print "add to coil queue", coil, action

    def _do_update(self):
        if self.light_update_list:
            self._update_lights()
        if self.led_update_list:
            self._update_leds()
        if self.coil_queue:
            self._fire_coils()
        if self.event_queue:
            self._fire_events()

    def _fire_coils(self):
        for coil in self.coil_queue:
            if coil[1] == 'pulse':
                coil[0].pulse()
        self.coil_queue = set()

    def _fire_events(self):
        for event in self.event_queue:
            self.machine.events.post(event)
        self.event_queue = set()

    def _update_lights(self):
        # Updates all the lights in the machine with whatever's in
        # self.light_update_list. Updates with priority, so if the light is
        # doing something at a higher priority, it won't have an effect

        for item in self.light_update_list:
            item['light'].on(brightness=item['brightness'],
                             priority=item['priority'],
                             cache=False)

        self.light_update_list = []

    def _update_leds(self):
        # Updates the LEDs in the machine with whatever's in the update_list.

        # The update_list is a list of dictionaries w/the following k/v pairs:
        #   led
        #   color
        #   fade_ms
        #   priority
        #   blend

        for item in self.led_update_list:
            # Only perform the update if the priority is higher than whatever
            # touched that led last.
            if item['priority'] >= item['led'].state['priority']:

                # Now we're doing the actual update.

                item['led'].color(item['color'], item['fade_ms'],
                                  item['priority'], item['blend'])

        self.led_update_list = []

    def run_script(self, lightname, script, priority=0, repeat=True,
                   blend=False, tps=1000, num_repeats=0, callback=None):
        """Runs a light script. Scripts are similar to Shows, except they
        only apply to single lights and you can "attach" any script to any
        light. Scripts are used anytime you want an light to have more than one
        action. A simple example would be a flash an light. You would make a
        script that turned it on (with your color), then off, repeating
        forever.

        Scripts could be more complex, like cycling through multiple colors,
        blinking out secret messages in Morse code, etc.

        Interally we actually just take a script and dynamically convert it
        into a Show (that just happens to only be for a single light), so
        we can have all the other Show-like features, including playback
        speed, repeats, blends, callbacks, etc.

        Args:
            lightname: The name of the light for this script to control.
            script: A list of dictionaries of script commands. (See below)
                priority': The priority the light in this script should operate
                at.
            repeat (bool): Whether the script repeats (loops).
            blend (bool): Whether the script should blend the light colors with
                lower prioirty things. todo
            tps (int): Tocks per second. todo
            num_repeats (int): How many times this script should repeat before
                ending. A value of 0 indicates it will repeat forever. Also
                requires *repeat=True*. 'callback': A callback function that is
                called when the script is stopped. todo update

        Returns:
            :class:`Show` object. Since running a script just sets up and
            runs a regular Show, run_script returns the Show object.
            In most cases you won't need this, but it's nice if you want to
            know exactly which Show was created by this script so you can
            stop it later. (See the examples below for usage.)

        The script is a list of dictionaries, with each list item being a
        sequential instruction, and the dictionary defining what you want to
        do at that step. Dictionary items for each step are:

            color: The hex color for the light
            time: How long (in ms) you want the light to be at that color
            fade: True/False. Whether you want that light to fade to the color
                (using the *time* above), or whether you want it to switch to
                that color instantly.

        Example usage:

        Here's how you would use the script to flash an RGB light between red
        and off:

            self.flash_red = []
            self.flash_red.append({"color": "ff0000", "time": 100})
            self.flash_red.append({"color": "000000", "time": 100})
            self.machine.show_controller.run_script("light1", self.flash_red,
                                                     "4", blend=True)

        Once the "flash_red" script is defined as self.flash_red, you can use
        it anytime for any light. So if you want to flash two lights red, it
        would be:

            self.machine.show_controller.run_script("light1", self.flash_red,
                                                     "4", blend=True)
            self.machine.show_controller.run_script("light2", self.flash_red,
                                                     "4", blend=True)

        Most likely you would define your scripts once when the game loads and
        then call them as needed.

        You can also make more complex scripts. For example, here's a script
        which smoothly cycles an RGB light through all colors of the rainbow:

            self.rainbow = []
            self.rainbow.append({'color': 'ff0000', 'time': 400, 'fade': True})
            self.rainbow.append({'color': 'ff7700', 'time': 400, 'fade': True})
            self.rainbow.append({'color': 'ffcc00', 'time': 400, 'fade': True})
            self.rainbow.append({'color': '00ff00', 'time': 400, 'fade': True})
            self.rainbow.append({'color': '0000ff', 'time': 400, 'fade': True})
            self.rainbow.append({'color': 'ff00ff', 'time': 400, 'fade': True})

        If you have single color lights, your *color* entries in your script
        would only contain a single hex value for the intensity of that light.
        For example, a script to flash a single-color light on-and-off (which
        you can apply to any light):

            self.flash = []
            self.flash.append({"color": "ff", "time": 100})
            self.flash.append({"color": "00", "time": 100})

        If you'd like to save a reference to the :class:`Show` that's
        created by this script, call it like this:

            self.blah = self.machine.show_controller.run_script("light2",
                                                        self.flash_red, "4")
        """

        # convert the steps from the script list that was passed into the
        # format that's used in an Show

        show_actions = []

        for step in script:
            if step.get('fade', None):
                color = str(step['color']) + "-f" + str(step['time'])
            else:
                color = str(step['color'])

            color_dic = {lightname: color}
            current_action = {'tocks': step['time'],
                              'lights': color_dic}
            show_actions.append(current_action)
        show = None
        show = Show(self.machine, actions=show_actions)
        show_obj = show.play(repeat=repeat, tocks_per_sec=tps,
                             priority=priority, blend=blend,
                             num_repeats=num_repeats, callback=callback)

        self.active_scripts.append({'lightname': lightname,
                                    'priority': priority,
                                    'show': show})

        return show_obj

    def stop_script(self, lightname=None, priority=0, show=None):
        """Stops and remove an light script.

        Rarameters:

            'lightname': The light(s) with the script you want to stop.
            'priority': The priority of the script(s) you want to stop.
            'show': The show object associated with a script you want to stop.

        In a practical sense there are several ways you can use this
        stop_script method:

            - Specify *lightname* only to stop (and remove) all active
              Shows created from scripts for that lightname, regardless of
              priority.
            - Specify *priority* only to stop (and remove) all active
              Shows based on scripts running at that priority for all
              lights.
            - Specify *lightname* and *priority* to stop (and remove) all
              active Shows for that lightname at the specific priority you
              passed.
            - Specify a *show* object to stop and remove that specific show.
            - If you call stop_script() without passing it anything, it will
            remove all the lightsshows started from all scripts. This is useful
            for things like end of ball or tilt where you just want to kill
            everything.
        """

        # Make a copy of the active scripts object since we're potentially
        # deleting from it while we're also iterating through it. We have to
        # use list() here since if we just write a=b then they would both
        # point to the same place and that wouldn't solve the problem.
        active_scripts_copy = list(self.active_scripts)

        if show:
            for entry in active_scripts_copy:
                if entry['show'] == show:
                    self._end_show(show)
        elif lightname and priority:
            for entry in active_scripts_copy:
                if (entry['lightname'] == lightname and
                        entry['priority'] == priority):
                    self._end_show(entry['show'])
        elif lightname:
            for entry in active_scripts_copy:
                if entry['lightname'] == lightname:
                    self._end_show(entry['show'])
        elif priority:
            for entry in active_scripts_copy:
                if entry['priority'] == priority:
                    self._end_show(entry['show'])
        else:
            for entry in active_scripts_copy:
                self._end_show(entry['show'])

        # todo callback?

    def enable(self, lightname, priority=0, color=None, dest_color=None,
               fade=0, blend=True):
        """This is a single one-time command to enable an light.

        Args:
            lightname: the light you're enabling
            priority (int): The priority this light will be enablight at. This
                is used when determining what other enables, scripts, and
                Shows will play over or under it). If you enable an light
                with the same priority that was previously used to enable it,
                it will overwrite the old color with the new one.

            color (str): A hex string (like "ff00aa") for what color you want to
                enable this light to be. Note if you have a single color (i.e.
                one element) light, then just pass it "ff" to enable it on full
                brightness, or "80" for 50%, etc.

            dest_color (str): If you want to fade the light to your color instead
                of enabling it instantly, pass *dest_color* instead of *color*.

            fade (int): If you want to fade the light on, use *fade* to specify the
                fade on time (in ms). Note this also requires *dest_color*
                above instead of *color*.

            blend (bool): If *True* and if you're using a fade, it will fade
                from whatever color the light currently is to your
                *dest_color*. If False it will turn the light off first before
                fading.

        Note that since you enable lights with priorities, you can actually
        "enable" the light multiple times at different priorties. Then if you
        disable the light via a higher priority, the lower priority will still
        be there. This means that in your game, each mode can do whatever it
        wants with lights and you don't have to worry about a higher priority
        mode clearing out an light and messing up the lower priority mode's
        status.

        The ability for this enable method to also keep track of the priority
        that a light is enablight is the reason you'd want to use this method
        versus calling :meth:`lights.color` directly. If you do use
        :meth:`lights.color` to enable an light directly,
        :class:`ShowController` won't know about it, and your light could be
        overwritten the next time a Show, script, or enable command is
        used. """

        # Add / update this latest info in our manual_commands dictionary
        params = {'lightname': lightname,
                  'color': color,
                  'priority': priority}
        #fadeend = None

        if fade:
            fadestart = self.current_time
            fadeend = fadestart + (fade / 1000)
            if dest_color and not color:  # received dest_color but not color
                dest_color = dest_color
                color = "000000"
            elif dest_color and color:  # received dest_color and color
                dest_color = dest_color
                color = color
            else:  # received color but not dest_color
                dest_color = color
                color = None
            prevcolor = color

            params.update({'fadeend': fadeend, 'blend': blend,
                           'fadestart': fadestart, 'dest_color': dest_color,
                           'color': color, 'prevcolor': prevcolor})

        # check to see if we already have an entry for this lightname /
        # priority pair. If so, remove it.
        for entry in self.manual_commands:
            if entry['lightname'] == lightname and entry['priority'] == priority:
                self.manual_commands.remove(entry)

        # now add our new command to the list
        self.manual_commands.append(params)

        # Add this command to our update_list so it gets serviced along with
        # all the other updates
        if fade:  # if we have a fade
            self._add_to_update_list({'lightname': lightname,
                                     'priority': priority,
                                     'dest_color': dest_color,
                                     'fadeend': fadeend,
                                     'blend': blend,
                                     'fadestart': fadestart,
                                     'prevcolor': prevcolor})
        else:  # no fade
            self._add_to_update_list({'lightname': lightname,
                                     'priority': priority,
                                     'color': color})

    def disable(self, lightname, priority=0, clear_all=True):
        """Command to disable an light

        Args:
            lightname (str): The name of the light you're disabling
            priority (int): Which priority you're clearing (disabling) the
                light at. (See *clear_all* below for details.) If you don't
                pass a priority, then it will disable the light and remove
                *all* entries from the manual commands list. i.e. In that case
                it disables/removes all the previously issued manual commands
            clear_all (bool): If True, it will clear all the commands from the
                priority you passed and from any lower priority commands. If
                False then it only clears out the command from the priority
                that was passed.

        Once cleared, :class:`ShowController` restore the light's state from
        any commands or shows running at a lower priority.

        Note that this method does not affect running :class:`Show` shows,
        so if you clear the :meth:`enable` commands but you have a running
        Show which enables that light, then the light will be enablight.
        If you want to absolutely disable the light regardless of whatever
        Show is running, then use :meth:`enable` with *color=000000*,
        *blend=False*, and a *priority* that's higher than any running show.
        """

        priority_to_restore = priority

        # check to see if we have an entry for this light in our manual
        # commands dictionary

        if clear_all:
            if priority:  # clear all, with priority specified
                for entry in self.manual_commands:
                    if entry['lightname'] == lightname and \
                            entry['priority'] <= priority:
                        self.manual_commands.remove(entry)
                        priority_to_restore = priority
                        self.restore_light_state(lightname, priority_to_restore)
            else:  # clear all, no priority specified
                for entry in self.manual_commands:
                    if entry['lightname'] == lightname:
                        self.manual_commands.remove(entry)
                        self.restore_light_state(lightname, priority_to_restore)

        else:  # just remove any commands of the priority passed
            for entry in self.manual_commands:
                if entry['lightname'] == lightname and \
                        entry['priority'] == priority:
                    self.manual_commands.remove(entry)
                    priority_to_restore = 0
                    self.restore_light_state(lightname, priority_to_restore)

            # if we get to here, we didn't find any commands to restore, so
            # don't do anything

    def load_shows(self, path):
        """Automatically loads all the light shows in a path.

        Light shows are added to the dictionary self.shows with they key
        set to the value of the file name.

        For example, the light show 'sweep.yaml' will be loaded as
        self.shows['sweep']

        This method will also loop through sub-directories, allowing the game
        programmer to organize the light show files into folders as needed.

        Args:
            path: A string of the relative path to the folder, based from the
                root from where the mpf.py file is running.
        """

        self.log.info("Loading shows from: %s", path)
        for root, path, files in os.walk(path, followlinks=True):
            for f in files:
                fullpath = os.path.join(root, f)
                self.machine.shows[str(os.path.splitext(f)[0])] = \
                    Show(self.machine, fullpath)

    @staticmethod
    def hexstring_to_list(input_string, output_length=3):
        """Takes a string input of hex numbers and returns a list of integers.

        This always groups the hex string in twos, so an input of ffff00 will
        be returned as [255, 255, 0]

        Args:
            input_string: A string of incoming hex colors, like ffff00.
            output_length: Integer value of the number of items you'd like in
                your returned list. Default is 3. This method will ignore
                extra characters if the input_string is too long, and it will
                pad with zeros if the input string is too short.

        Returns:
            List of integers, like [255, 255, 0]
        """
        output = []
        input_string = str(input_string).zfill(output_length*2)

        for i in xrange(0, len(input_string), 2):  # step through every 2 chars
            output.append(int(input_string[i:i+2], 16))

        return output[0:output_length:]

    @staticmethod
    def hexstring_to_int(inputstring, maxvalue=255):

        return_int = int(inputstring, 16)

        if return_int > maxvalue:
            return_int = maxvalue

        return return_int


class Show(object):
    """Represents a Show which is a sequential list of lights, colors, and
    timings that can be played back. Individual shows can be started, stopped,
    reset, etc. Shows can be played at any speed, sped up, slowed down, etc.

    Args:
        machine: The main machine object.
        filename: File (and path) of the Show's yaml file
        actions (list): List of Show actions which are passed directly
            instead of read from a yaml file

    If you pass *filename*, it will process the actions based on that file.
    Otherwise it will look for the actions from the list passed via *actions*.
    Either *filename* or *actions* is required.

    """

    def __init__(self, machine, filename=None, actions=None):
        super(Show, self).__init__()
        self.log = logging.getLogger("Show")
        self.machine = machine
        self.tocks_per_sec = 30  # how many steps per second this show runs at
        # you can safely read this value to determine the current playback rate
        # But don't update it directly to change the speed of a running show.
        # Use the change_speed() method instead.
        self.secs_per_tock = 0  # calculated based on tocks_per_sec
        self.repeat = False  # whether this show repeats when finished
        self.num_repeats = 0  # if self.repeat=True, how many times it repeats
        # self.num_repeats = 0 means it repeats indefinitely until stopped
        self.current_repeat_step = 0  # tracks which repeat we're on, used with
        # num_repeats above
        self.hold = False  # hold the item states when the show ends.
        self.priority = 0  # relative priority of this show
        self.ending = False  # show will end after the current tock ends
        self.running = False  # is this show running currently?
        self.blend = False  # when an light is off in this show, should it allow
        # lower priority lights to show through?
        self.show_actions = list()  # show commands from the show yaml file
        self.current_location = 0  # index of which step (tock) a running show is
        self.last_action_time = 0.0  # when the last action happened
        self.total_locations = 0  # total number of action locations
        self.current_tock = 0  # index of which tock a running show is in
        self.next_action_time = 0  # time of when the next action happens
        self.callback = None  # if the show should call something when it ends
        # naturally. (Not invoked if show is manually stopped)

        self.light_states = {}
        self.led_states = {}

        if filename:
            self._load(filename)
        elif actions:
            self._process(actions)
        else:
            self.log.warning("Couldn't set up Show as we didn't receive a file "
                             "or action list as input!")
            return False  # todo make sure we process this for auto loaded shows

    def _load(self, filename):
        # Loads a Show yaml file from disk
        self.log.debug("Loading Show: %s", filename)

        try:
            show_actions = yaml.load(open(filename, 'r'))
        except:
            self.log.error("Error loading show: %s", filename)
        else:
            self._process(show_actions)

    def _process(self, show_actions):
        # Process a new show's actions. This is a separate method from
        # load so we can also use it to process new shows that we load in
        # ways other than from show files from disk. (e.g. from scripts.)

        self.log.debug("Parsing...")

        # add this show to show contoller's list of registered shows
        # use a weakref so garbage collection will del it if we delete the show
        self.machine.show_controller.registered_shows.append(weakref.proxy(self))

        # count how many total locations are in the show. We need this later
        # so we can know when we're at the end of a show
        self.total_locations = len(show_actions)

        #todo913 go through and convert item strings to the format we can use
        # them in. example color hexes to lists, device names to objects
        # we do all this crazy processing up front when the show loads so we
        # don't have to do it for each item at each step when the show is playing

        for step_num in range(len(show_actions)):
            step_actions = dict()

            step_actions['tocks'] = show_actions[step_num]['tocks']

            # Lights
            if ('lights' in show_actions[step_num] and
                    show_actions[step_num]['lights']):

                light_actions = dict()

                for light in show_actions[step_num]['lights']:

                    try:
                        this_light = self.machine.lights[light]
                    except:
                        # this light name is invalid
                        self.log.warning("WARNING: Found invalid light name"
                                         " '%s' in show. Skipping...",
                                         light)
                        break

                    value = show_actions[step_num]['lights'][light]

                    # convert / ensure lights are single ints
                    if type(value) is str:
                        value = ShowController.hexstring_to_int(
                            show_actions[step_num]['lights'][light])

                    if type(value) is int and value > 255:
                        value = 255

                    #show_actions[step_num]['lights'][light] = value
                    light_actions[this_light] = value

                    # make sure this light is in self.light_states
                    if this_light not in self.light_states:
                        self.light_states[this_light] = 0

                step_actions['lights'] = light_actions

            # Events
            # make sure events is a list of strings
            if ('events' in show_actions[step_num] and
                    show_actions[step_num]['events']):

                event_list = (self.machine.string_to_list(
                    show_actions[step_num]['events']))

                step_actions['events'] = event_list

            #Coils
            if ('coils' in show_actions[step_num] and
                    show_actions[step_num]['coils']):

                coil_actions = dict()

                for coil in show_actions[step_num]['coils']:

                    try:
                        this_coil = self.machine.coils[coil]
                    except:
                        # this coil name is invalid
                        self.log.warning("WARNING: Found invalid coil name"
                                         " '%s' in show. Skipping...",
                                         coil)
                        break

                    value = show_actions[step_num]['coils'][coil]
                    # todo any more processing here?
                    coil_actions[this_coil] = value

                step_actions['coils'] = coil_actions

            # LEDs
            if ('leds' in show_actions[step_num] and
                    show_actions[step_num]['leds']):

                led_actions = dict()

                for led in show_actions[step_num]['leds']:

                    try:
                        this_led = self.machine.leds[led]
                    except:
                        # this light name is invalid
                        self.log.warning("WARNING: Found invalid led name"
                                         " '%s' in show. Skipping...",
                                         led)
                        break

                    value = show_actions[step_num]['leds'][led]

                    # ensure led is list is of 4 ints: [r, g, b, fade_tocks]
                    if type(value) is list:
                        # ensure our list is exactly 4 items
                        if len(value) < 4:
                            # pad to 4 with zeros
                            value.extend([0] * (4 - len(value)))
                        elif len(value) > 4:
                            value = value[0:4]

                    if type(value) is str:
                        if '-f' in value:
                            fade = value.split('-f')
                        else:
                            fade = 0

                    # convert our color of hexes to a list of ints
                    value = ShowController.hexstring_to_list(value)
                    value.append(fade)

                    led_actions[this_led] = value

                    # make sure this led is in self.led_states
                    if this_led not in self.led_states:
                        self.led_states[this_led] = {
                            'current_color': [0, 0, 0],
                            'destination_color': [0, 0, 0],
                            'start_color': [0, 0, 0],
                            'fade_start': 0,
                            'fade_end': 0}

                step_actions['leds'] = led_actions

            self.show_actions.append(step_actions)

    def play(self, repeat=False, priority=0, blend=False, hold=False,
             tocks_per_sec=32, start_location=-1, callback=None,
             num_repeats=0):
        """Plays a Show. There are many parameters you can use here which
        affect how the show is played. This includes things like the playback
        speed, priority, whether this show blends with others, etc. These are
        all set when the show plays. (For example, you could have a Show
        file which lights a bunch of lights sequentially in a circle pattern,
        but you can have that circle "spin" as fast as you want depending on
        how you play the show.)

        :param boolean repeat: True/False, whether the show repeats when it's
        done.

        :param integer priority: The relative priority of this show. If there's
        ever a situation where multiple shows want to
        control the same item, the one with the higher priority will win.
        ("Higher" means a bigger number, so a show with priority 2 will
        override a priority 1.)

        :param boolean blend: Controls whether this show "blends" with lower
        priority shows and scripts. For example, if this show turns a light
        off, but a lower priority show has that light set to blue, then the
        light will "show through" as blue while it's off here. If you don't
        want that behavior, set blend to be False. Then off here will be off
        for sure (unless there's a higher priority show or command that turns
        the light on). Note that not all item types blend. (You can't blend a
        coil or event, for example.)

        :param boolean hold: If True, then when this Show ends, all the
        items that are on at that time will remain on. If False, it turns them
        all off when the show ends

        :param integer tocks_per_sec: This is how fast your show runs.
        ("Playback speed," in other words.) Your Show files specify action
        times in terms of 'tocks', like "make this light red for 3 tocks, then
        off for 4 tocks, then a different light on for 6 tocks. When you play a
        show, you specify how many tocks per second you want it to play.
        Default is 32, but you might even want tocks_per_sec of only 1 or 2 if
        your show doesn't need to move than fast. Note this does not affect
        fade rates. So you can have tocks_per_sec of 1 but still have lights
        fade on and off at whatever rate you want. Also the term "tocks" was
        chosen so as not to confuse it with "ticks" which is used by the
        machine run loop.

        :param integer start_location: Which position in the show file the show
        should start in. Usually this is 0 but it's nice to start part way
        through. Also used for restarting shows that you paused.

        :param object callback: A callback function that is invoked when the
        show is stopped.

        :param integer num_repeats: How many times you want this show to repeat
        before stopping. A value of 0 means that it repeats indefinitely. Note
        this only works if you also have repeat=True.

        Example usage from a game mode:

        Load the show (typically done once when the machine is booting up)
            self.show1 = lights.Show(self.machine,
            "Shows\\show1.yaml")

        Play the show:
            self.show1.play(repeat=True, tocks_per_sec=10, priority=3)

        Stop the show:
            self.show1.stop()

        Play the show again, but twice as fast as before
            self.show1.play(repeat=True, tocks_per_sec=20, priority=3)

        Play the show so it only repeats twice and then stops itself
            self.show1.play(repeat=True, tocks_per_sec=20, priority=3,
                            num_repeats=True)

        Play two shows at once:
            self.show1.play(repeat=True, tocks_per_sec=20, priority=3)
            self.show2.play(repeat=True, tocks_per_sec=5, priority=3)

        Play two shows at once, but have one be a higher priority meaning it
        will "win" if both shows want to control the same light at the same
        time:
            self.show1.play(repeat=True, tocks_per_sec=20, priority=4)
            self.show2.play(repeat=True, tocks_per_sec=5, priority=3)

        etc.
        """
        self.repeat = repeat
        self.priority = int(priority)
        self.blend = blend
        self.hold = hold
        self.tocks_per_sec = tocks_per_sec  # also referred to as 'tps'
        self.secs_per_tock = 1/float(tocks_per_sec)
        self.callback = callback
        self.num_repeats = num_repeats
        if start_location >= 0:
            # if you don't specify a start location, it will start where it
            # left off (if you stopped it with reset=False). If the show has
            # never been run, it will start at 0 per the initialization
            self.current_location = start_location
        self.machine.show_controller._run_show(self)

    def stop(self, reset=True, hold=False):
        """Stops a Show.

        :param boolean reset: True means it resets the show to the beginning.
        False it keeps it where it is so the show can pick up where it left off

        :param boolean hold: Lets you specify that the lights will be held in
        their current state after the show ends. Note that if you have a show
        that's set to hold but you pass hold=False here, it won't work. In that
        case you'd have to set <show>.hold=False and then call this method to
        stop the show. """

        if hold:
            self.hold = True

        self.machine.show_controller._end_show(self, reset)

    def change_speed(self, tocks_per_sec=1):
        """Changes the playback speed of a running Show.

        :param integer tocks_per_sec: The new tocks_per_second play rate.

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

    def _advance(self):
        if self.ending:
            self.machine.show_controller._end_show(self)
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

            if item_type == 'lights':

                for light_obj, brightness in item_dict.iteritems():

                    self.machine.show_controller._add_to_light_update_list(
                        light=light_obj,
                        brightness=brightness,
                        priority=self.priority,
                        blend=self.blend)

                    # update the current state
                    self.light_states[light_obj] = brightness

            elif item_type == 'leds':

                current_time = time.time()

                for led_obj, led_dict in item_dict.iteritems():

                    self.machine.show_controller._add_to_led_update_list(
                        led=led_obj,
                        color=[led_dict[0], led_dict[1], led_dict[2]],
                        fade_ms=led_dict[3] * self.tocks_per_sec,
                        priority=self.priority,
                        blend=self.blend)

                    # update the current state

                    # grab the old current color
                    prev_color = [led_dict[0], led_dict[1], led_dict[2]]

                    self.led_states[led_obj] = {
                            'current_color': prev_color,
                            # todo need to calculate this for a restore
                            'destination_color': [led_dict[0], led_dict[1],
                                                  led_dict[2]],
                            'start_color': prev_color,
                            'fade_start': current_time,
                            'fade_end': current_time + (led_dict[3] *
                                                        self.tocks_per_sec)}

            elif item_type == 'events':

                for event in item_dict:  # item_dict is actually a list here
                    self.machine.show_controller._add_to_event_queue(event)

            elif item_type == 'coils':

                for coil_obj, coil_action in item_dict.iteritems():
                    self.machine.show_controller._add_to_coil_queue(
                        coil = coil_obj,
                        action = coil_action)

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


class Playlist(object):
    """A list of :class:`Show` objects which are then played sequentially.
    Playlists are useful for things like attract mode where you play one show
    for a few seconds, then another, etc.

    Parameters:

        'machine': Parent machine object

    Each step in a playlist can contain more than one :class:`Show`. This
    is useful if you have a lot of little shows for different areas of the
    playfield that you want run at the same time. For example, you might have
    one show that only controls a group of rollover lane lights, and another
    which blinks the lights in the center of the playfield. You can run them at
    the by putting them in the same step in your playlist. (Note you don't need
    to use a playlist if you simply want to run two Shows at the same
    time. In that case you could just call :meth:`Show.play` twice to play
    both shows.

    For each "step" in the playlist, you can specify the number of seconds it
    runs those shows before moving on, or you can specify that one of the shows
    in that step plays a certain number of times and then the playlist moves
    to the next step from there.

    You create a show by creating an instance :class:`Playlist`. Then you
    add Shows to it via :meth:`add_show`. Finally, you specify the
    settings for each step (like how it knows when to move on) via :meth:
    `step_settings`.

    When you start a playlist (via :meth:`start`, you can specify
    settings like what priority the show runs at, whether it repeats, etc.)

    Example usage from a game mode:
    (This example assumes we have self.show1, self.show2, and self.show3
    already loaded.)

    Setup the playlist::

        self.my_playlist = lights.Playlist(self.machine)
        self.my_playlist.add_show(step_num=1, show=self.show1, tocks_per_sec=10)
        self.my_playlist.add_show(step_num=2, show=self.show2, tocks_per_sec=5)
        self.my_playlist.add_show(step_num=3, show=self.show3, tocks_per_sec=32)
        self.my_playlist.step_settings(step=1, time=5)
        self.my_playlist.step_settings(step=2, time=5)
        self.my_playlist.step_settings(step=3, time=5)

    Run the playlist::

        self.my_playlist.start(priority=100, repeat=True)

    Stop the playlist:

        ``self.my_playlist.stop()``
    """
    def __init__(self, machine):
        super(Playlist, self).__init__()
        self.log = logging.getLogger("Playlist")
        self.machine = machine
        self.step_settings_dic = {}  # dictionary with step_num as the key. Values:
                                 # time - sec this entry runs
                                 # trigger_show
        self.step_actions = []  # The actions for the steps in the playlist
        # step_num
        # show
        # num_repeats
        # tocks_per_sec
        # blend
        self.steps = []  # list of values of steps, like [1,2,3,5,10]
        self.current_step_position = 0
        self.repeat = False
        self.repeat_count = 0
        self.current_repeat_loop = 0
        self.running = False
        self.priority = 0
        self.starting = False  # used to know if we're on our first step
        self.stopping = False  # used to tell the playlist it should stop on
        # the next advance

    def add_show(self, step_num, show, num_repeats=0, tocks_per_sec=32,
                 blend=False, repeat=True):
        """Adds a Show to this playlist. You have to add at least one show
        before you start playing the playlist.

        :param integer step_num:
        Which step number you're adding this show to.
        You have to specify this since it's possible to add multiple shows to
        the same step (in cases where you want them both to play at the same
        time during that step). If you want the same show to play in multiple
        steps, then add it multiple times (once to each step). The show plays
        starting with the lowest number step and then moving on. Ideally they'd
        be 1, 2, 3... but it doesn't matter. If you have step numbers of 1, 2,
        5... then the player will figure it out.

        :param object show: The Show object that you're adding to this
        step.

        :param integer num_repeats: How many times you want this show to repeat
        within this step. Note this does not affect when the playlist advances
        to the next step. (That is controlled via :meth:`step_settings`.)
        Rather, this is just how many loops this show plays. A value of 0
        means it repeats indefinitely. (Well, until the playlist advances to
        the next step.) Note that you also have to have repeat=True for it to
        repeat here.

        :param integer tocks_per_sec: How fast you want this show to play. See
        :meth:`Show.play` for details.

        :param boolean blend: Whether you want this show to blend with lower
        priority shows below it. See :meth:`Show.play` for details.

        :param boolean repeat: Causes the show to keep repeating until the
        playlist moves on to the next step.
        """

        # Make a temp copy of our steps since we might have to remove one while
        # iterating through it
        temp_steps = list(self.step_actions)
        # If the show we're adding is already in the step we're adding it to,
        # remove it.
        for step in temp_steps:
            if step['step_num'] == step_num and step['show'] == show:
                self.step_actions.remove(step)
        self.step_actions.append({'step_num': step_num,
                                  'show': show,
                                  'num_repeats': num_repeats,
                                  'tocks_per_sec': tocks_per_sec,
                                  'repeat': repeat,
                                  'blend': blend})

        # Add this number to our list of step numbers
        # We do all this here when we add a show to a playlist so we don't have
        # to deal with it later.
        self.steps.append(step_num)
        # Remove duplicates
        self.steps = list(set(self.steps))
        # Reorder the list from smallest to biggest
        self.steps.sort()

    def step_settings(self, step, time=0, trigger_show=None):
        """Used to configure the settings for a step in a :class:`Playlist`.
        This configuration is required for each step. The main thing you use
        this for is to specify how the playlist knows to move on to the next
        step.

        :param integer step: Which step number you're configuring

        :param float time: The time in seconds that you want this step to run
        before moving on to the next one.

        :param object trigger_show: If you want to move to the next step after
        one of the Shows in this step is done playing, specify that
        Show here. This is required because if there are multiple
        Shows in this step of the playlist which all end at different
        times, we wouldn't know which one to watch in order to know when to
        move on.

        Note that you can have repeats with a trigger show, but in that case
        you also need to have the num_repeats specified. Otherwise if you have
        your trigger show repeating forever then the playlist will never move
        on. (In that case use the *time* parameter to move on based on time.)
        """
        settings = {'time': time,
                    'trigger_show': trigger_show}
        self.step_settings_dic.update({step: settings})

    def start(self, priority, repeat=True, repeat_count=0, reset=True):
        """Starts playing a playlist. You can only use this after you've added
        at least one show via :meth:`add_show` and configured the settings for
        each step via :meth:`step_settings`.

        :param integer priority: What priority you want the :class:`Show`
        shows in this playlist to play at. These shows will play "on top" of
        lower priority stuff, but "under" higher priority things.

        :param boolean repeat: - Controls whether this playlist to repeats when
        it's finished.

        :param integer repeat_count: How many times you want this playlist to
        repeat before it stops itself. (Must be used with *repeat=True* above.)
        A value of 0 here means that this playlist repeats forever until you
        manually stop it. (This is ideal for attract mode.)

        :param boolean reset: - Controls whether you want this playlist to
        start at the begining (True) or you want it to pick up where it left
        off (False). You can also use *reset* to restart a playlist that's
        currently running.
        """
        if not self.running:
            if reset:
                self.current_step_position = 0
                self.current_repeat_loop = 0
            self.running = True
            self.starting = True
            self.stopping = False
            self.repeat = repeat
            self.repeat_count = repeat_count
            self.priority = int(priority)
            self._advance()

        else:
            # we got a command to start a playlist, but the playlist is already
            # running? If they also passed a reset parameter, let's restart
            # the playlist from the beginning
            if reset:
                self.stop(reset=True)
                self.start(priority=priority, repeat=repeat,
                           repeat_count=repeat_count)

    def stop(self, reset=True):
        """Stops a playlist. Pretty simple.

        :param boolean reset: If *True*, it resets the playlist tracking
        counter back to the beginning. You can use *False* here if you want to
        stop and then restart a playlist to pick up where it left off.
        """
        for action in self.step_actions:
            if action['step_num'] == self.steps[self.current_step_position-1]:
                # we have to use the "-1" above because the playlist current
                # position represents the *next* step of shows to play. So when
                # we stop the current show, we have to come back one.
                action['show'].stop()
        self.running = False
        for item in self.machine.show_controller.queue:
            if item['playlist'] == self:
                self.machine.show_controller.queue.remove(item)
        if reset:
            self.current_step_position = 0
            self.current_repeat_loop = 0

    def _advance(self):
        #Runs the Show(s) at the current step of the plylist and advances
        # the pointer to the next step

        # Creating a local variable for this just to keep the code easier to
        # read. We track this because it's possible the game programmer will
        # skip numbers in the steps in the playlist, like [1, 2, 5]
        current_step_value = self.steps[self.current_step_position]

        prev_step = self.steps[self.current_step_position-1]

        # Stop the previous step's shows
        # Don't do anything if this playlist hasn't started yet
        if not self.starting:
            for action in self.step_actions:
                if action['step_num'] == prev_step:
                    # We have to make sure the show is running before we try to
                    # stop it, because if this show was a trigger show then it
                    # stopped itself already
                    if action['show'].running:
                        action['show'].stop()
        self.starting = False

        # If this playlist is marked to stop, then stop here
        if self.stopping:
            return

        # Now do the actions in our current step

        # Pull in the stuff we need for this current step
        step_time = self.step_settings_dic[current_step_value]['time']
        step_trigger_show = (self.step_settings_dic[current_step_value]
                                                   ['trigger_show'])

        # Now step through all the actions for this step and schedule the
        # Shows to play
        for action in self.step_actions:
            if action['step_num'] == current_step_value:
                show = action['show']
                num_repeats = action['num_repeats']
                tocks_per_sec = action['tocks_per_sec']
                blend = action['blend']
                repeat = action['repeat']

                if show == step_trigger_show:
                    # This show finishing will be used to trigger the advancement
                    # to the next step.
                    callback = self._advance

                    if num_repeats == 0:  # Hmm.. we're using this show as the
                        # trigger, but it's set to repeat indefinitely?!?
                        # That won't work. Resetting repeat to 1 and raising
                        # a warning
                        num_repeats = 1
                        # todo warning

                else:
                    callback = None

                show.play(repeat=repeat, priority=self.priority, blend=blend,
                          tocks_per_sec=tocks_per_sec, num_repeats=num_repeats,
                          callback=callback)

        # if we don't have a trigger_show but we have a time value for this
        # step, set up the time to move on
        if step_time and not step_trigger_show:
            self.machine.show_controller.queue.append({'playlist': self,
                'action_time': (self.machine.show_controller.current_time +
                                step_time)})

        # Advance our current_step_position counter
        if self.current_step_position == len(self.steps)-1:
            # We're at the end of our playlist. So now what?
            self.current_step_position = 0

            # Are we repeating?
            if self.repeat:
                # Are we repeating forever, or x number of times?
                if self.repeat_count:  # we're repeating x number of times
                    if self.current_repeat_loop < self.repeat_count-1:
                        self.current_repeat_loop += 1
                    else:
                        self.stopping = True
                        return
                else:  # we're repeating forever
                    pass
            else:  # there's no repeat
                self.stopping = True
                return
        else:
            self.current_step_position += 1


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
