"""Manages the lighting effects in a pinball machine."""
# light_controller.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
import yaml
import weakref
import time
import os


class LightController(object):
    """Manages all the lights in a pinball machine. Handles updates,
    priorities, restores, running and stopping LightShows, etc. There should be
    only one per machine.

    Args:
        machine: Parent machine object.

    """
    def __init__(self, machine):
        self.log = logging.getLogger("LightController")
        self.machine = machine
        self.registered_shows = []
        self.update_list = []
        # self.update_list is a list of dicts:
        # lightname (str)
        # color (str)
        # fade(ms) (int)
        # priority (int)
        # fadeend (float)
        # fadestart (float)
        # dest_color (int) - hex color or list
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
        # converted to LightShows. We need this to facilitate removing shows when
        # they're done, since programmers don't use a name for scripts like
        # they do with shows. active_scripts is a list of dictionaries, with
        # the following k/v pairs:
        # lightname - the light the script is applied to
        # priority - what priority the script was running at
        # show - the associated LightShow object for that script
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
        self.machine.events.add_handler('machine_init_complete',
                                        self._initialize)

    def _initialize(self):
        for light in self.machine.lights:
            self.light_priorities[light.name] = 0
        self.initialized = True

    def _run_show(self, show):
        # Internal method which starts a LightShow
        show.running = True
        show.ending = False
        show.current_repeat_step = 0
        show.last_action_time = self.current_time
        # or in the advance loop?
        self.running_shows.append(show)  # should this be a set?
        self.running_shows.sort(key=lambda x: x.priority)

    def _end_show(self, show, reset=True):
        # Internal method which ends a running LightShow

        running_shows_copy = list(self.running_shows)

        if show in running_shows_copy:
            self.running_shows.remove(show)
            show.running = False
             # Restore the lights not "holding" the final states
            if not show.hold:
                for lightname in show.active_lights:
                    self.restore_light_state(lightname, show.priority)

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

        1. Running LightShows
        2. The LightController queue for any future commands that should be
        processed now.

        """
        self.current_time = time.time()
        # we calculate current_time one per loop because we want every action
        # in this loop to write the same "last action time" so they all stay
        # in sync. Also we truncate to 3 decimals for ease of comparisons later

        # Check the running LightShows
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

        if self.update_list:
            self._do_update()

    def restore_light_state(self, lightname, priority=None, fadeend=None,
                            color=None):
        """Restores a light to whatever state it should be in below the passed
        priority parameter. Similar to :meth:`get_light_state` except it
        actually makes the change rather than only returning values.

        Args:
            lightname (str): The name of the light we want to restore
            priority (int): We will only restore the light to a priority
                lower than this.

        Optional parameters which are used if our current light is fading to
        off and we need to blend it with whatever is below it :param string
        fadeend: Realtime of when the fade will end :param string color: The
        current hex color of the light.
        """

        # If this light was last touched by something with a higher priority
        # than the priority we're restoring below, then we can end here

        if self.light_priorities[lightname] > priority:
            return

        # If there are any pending updates, these can jack up what we're trying
        # to restore here if they're for the same light but with a higher
        # priority, so first flush that out.
        if self.update_list:
            self._do_update()

        restored_state = self.get_light_state(lightname, priority)
        # restored state will be a tuple of either length 2 or 4.
        # if 2, then we have new_color, new_priority and we can restore the
        # light to that and be done. if 4, we have new_color, new_priority,
        # new_fadetime, new_dest_color so we need to restore the color now and
        # then on next tick

        # Since we're restoring this light from something with a lower
        # priority, we need to reset the priority of whatever last touched this
        # light. Otherwise _do_update will ignore this restored setting.
        self.light_priorities[lightname] = 0

        # If there's an incoming blend, we need to calculate the colors and
        # write them into our update
        if fadeend:  # this catches if the light we're restoring FROM is fading
                     # with a blend to whatever's below it
            if len(restored_state) == 3:  # the light we're restoring to is not
                # involved in a fade, so we can just apply the fade of the
                # light we're fading away from to fade to the new light's color
                self._add_to_update_list({'lightname': lightname,
                                         'dest_color': restored_state[0],
                                         'priority': restored_state[1],
                                         'blend': restored_state[2],
                                         'fadeend': fadeend})
            else:  # this means that our light we're restoring *from* has a
                # fade and blend AND the light we're restoring *to* is also in
                # the process of fading. So this is kind of complex because we
                # have to set TWO fades. First we have to fade out our current
                # light to wherever the new light is in its fade. Then we have
                # to set a second fade to pick up the continuation of the
                # original fade from the new light. Phew!

                # Set the first fade from where our current light is now to
                # where the new light will be when our current light is done
                # fading to it

                # Figure out what color our target light will be when our
                # current light fade is done. To do that we have use our old
                # light's fadeend time to calculate the midpoint

                target_color = self.get_midfade_color(fadestart=restored_state[5],
                                                      fadeend=restored_state[3],
                                                      midpoint_time=fadeend,
                                                      orig_color=color,
                                                      dest_color=restored_state[4])

                # Now let's schedule it.
                self._add_to_update_list({'lightname': lightname,
                                         'dest_color': target_color,
                                         'priority': restored_state[1],
                                         'blend': restored_state[2],
                                         'fadeend': fadeend})

                # todo schedule a script that is for this lightname, with a
                # color of 000000, and an endtime of when the fadeend from
                # above is and with blend = True. This will have the effect
                # of restoring whatever lower level whatever is already
                # running

                self.queue.append({'action_time': fadeend,
                                   'lightname': lightname,
                                   'blend': True,
                                   'priority': priority,
                                   'fadeend': restored_state[3],
                                   'dest_color': restored_state[4]})

        # otherwise our light is not involved in a fade, so just restore
        # whatever we got immediately
        else:
            if len(restored_state) == 3:
                self._add_to_update_list({'lightname': lightname,
                                         'color': restored_state[0],
                                         'priority': restored_state[1],
                                         'blend': restored_state[2]})

            else:
                self._add_to_update_list({'lightname': lightname,
                                         'color': restored_state[0],
                                         'priority': restored_state[1],
                                         'blend': restored_state[2],
                                         'fadeend': restored_state[3],
                                         'dest_color': restored_state[4]})

    def get_light_state(self, lightname, priority=0):
        """Looks at all the active shows and returns the current
        details for a given light.

        :param string lightname: The light we're looking for
        :param integer priority: Returns the color from the highest priority
        lower than the priority passed it.

        Returns tuple of:
            'color': The restored color for the light.
            'priority': The priority of that light.
            'blend': If the light we're restoring is blending below itself.
            'fadeend': (optional) If there's a fade, what fade time should be
            used.
            'dest_color': (optional) If there's a fade, what fade color
            should be used.
        """
        new_color = None
        new_prevcolor = None
        new_priority = 0
        new_fadestart = None
        new_fadeend = None
        new_dest_color = None
        new_blend = False

        for show in self.running_shows:
            if lightname in show.active_lights and show.priority < priority:
                if show.priority > new_priority:
                    new_color = show.active_lights[lightname]['color']
                    new_priority = show.priority
                    new_blend = show.blend
                    # if we have a fade, grab those values now
                    # we won't process them now in case a they're overwritten
                    # by a higher priority. No sense don't that math now since
                    # we might not need it

                    if show.active_lights[lightname]['fadeend']:
                        # first check to make sure the fade is still happening
                            if (show.active_lights[lightname]['fadeend'] >
                                    self.current_time):
                                new_prevcolor = (show.active_lights[lightname].
                                                 get('prevcolor', "000000"))
                                new_fadestart = (show.active_lights[lightname]
                                                 ['fadestart'])
                                new_fadeend = (show.active_lights[lightname]
                                               ['fadeend'])
                                new_dest_color = (show.active_lights[lightname]
                                                  ['dest_color'])
                            else:
                                # we had a fade, but it's no longer active
                                new_color = (show.active_lights[lightname]
                                             ['dest_color'])

                    else:  # reset these since the new light we found doesn't
                           # use them
                        new_prevcolor = None
                        new_fadestart = None
                        new_fadeend = None
                        new_dest_color = None

        # Next check to see if there were any manual commands to enable this
        # light. If there are and they're higher than the priority that we
        # found in all the active shows, and higher than the priority that
        # we're restoring to, then we're going to return this color instead.

        for entry in self.manual_commands:
            if entry['lightname'] == lightname and \
                    entry['priority'] > new_priority and \
                    entry['priority'] < priority:
                new_color = entry['color']
                new_priority = entry['priority']
                new_prevcolor = None
                new_fadestart = None
                new_fadeend = None
                new_dest_color = None
                new_blend = None

                if entry.get('fadeend', None):
                    # we have a command that involves a fade
                    if entry['fadeend'] > self.current_time:
                    # the fade is still happening
                        new_fadeend = entry['fadeend']
                        new_dest_color = entry['dest_color']
                        new_fadestart = entry['fadestart']
                        new_prevcolor = entry['prevcolor']
                        new_blend = entry['blend']
                        new_color = "000000"
                    else:
                        # we had a fade, but it's over now, so we just need to
                        # restore this like a static color
                        new_color = entry['dest_color']

        # now that we have the values, we can process them to return them

        if not new_color:
            # If we didn't find a color in any of the running shows or commands
            # then we'll just pass 000000 to turn off the light
            new_color = "000000"

        if new_fadeend:  # the light we found is involved in a fade. We have to
            # figure out where it is now and where it's going

            # new_color is where this light is now
            new_color = self.get_midfade_color(fadestart=new_fadestart,
                                               fadeend=new_fadeend,
                                               midpoint_time=self.current_time,
                                               orig_color=new_prevcolor,
                                               dest_color=new_dest_color)

        # contruct the return based on what we have
        if new_fadeend:
            return new_color, new_priority, new_blend, new_fadeend,\
                new_dest_color, new_fadestart
        else:
            return new_color, new_priority, new_blend

    def get_midfade_color(self, fadestart, fadeend, midpoint_time, orig_color,
                          dest_color):
        """Figures out the new fade values based on a current fade in progress.

        Args:
            fadestart: The realtime time that this fade begin.
            fadeend: The realtime time that this fade ends.
            midpoint_time: The current time "mid point" that we're using for
                our new fade.
            orig_color: The original color in hex.
            dest_color: the final destination color in hex.

        Returns:
            'color': The current color we need to reset the light to in hex
        """

        # figure out where we are in the fade process (in percent)
        current_percent = (midpoint_time - fadestart) / (fadeend - fadestart)

        if type(orig_color) is not list:
            orig_color = self.convert_hex_to_list(orig_color)

        if type(dest_color) is not list:
            dest_color = self.convert_hex_to_list(dest_color)

        # create a new color dictionary that represents where the current color
        # should be at this point in the fade
        color = []

        for i in range(len(dest_color)):
            delta = (dest_color[i] - orig_color[i]) * current_percent
            if delta < 0:  # need to subtract from orig color
                color.append(int(orig_color[i]-delta))
            else:  # need to add to orig color
                color.append(int(orig_color[i]+delta))
        return color

    def _add_to_update_list(self, update):
        # Adds an update to our update list, with intelligence that if the list
        # already contains an update for this lightname & priority combination,
        # it deletes it first. This is done so if the machine loop is running
        # slower than our updates are coming in, we only keep the most recent
        # entry.

        for item in self.update_list:
            if (item['lightname'] == update['lightname'] and
                    item['priority'] == update['priority']):
                self.update_list.remove(item)
        self.update_list.append(update)

    def _do_update(self):
        # Updates the lights in the machine with whatever's in the update_list.

        # The update_list is a list of dictionaries w/the following k/v pairs:
        #    color: 111111
        #    priority: 9
        #    lightname: laneP
        #    fadecolor: list of colors or hex color
        #    fadeend: realtime fade end
        #    blend: True/False

        # First sort the update_list so we only have one of each lightname.
        # If there are multiple entries for one lightname, only keep the one
        # with the highest priority

        filtered = {}
        for di in sorted(self.update_list, key=lambda d: d['priority']):
            filtered[di['lightname']] = di

        self.update_list = filtered.values()

        # Make a copy of the update_list and then clear the original
        # Why? In case any of these updates need to call their own updates
        current_list = self.update_list
        self.update_list = []
        for item in current_list:
            # Only perform the update if the priority is higher than whatever
            # touched that light last.
            if item['priority'] >= self.light_priorities.get(item['lightname']):

                # Now we're doing the actual update. First set our color:

                # If we have an entry for color and it is not None
                if ("color" in item): #and item['color']:
                    if type(item['color']) is not list:
                        #item['color'] = item['color'].zfill(6)
                        pass
                    if item.get('blend', False) and \
                            (item['color'] == '000000' or\
                             item['color'] == [0, 0, 0]):
                        self.restore_light_state(item['lightname'],
                                               item['priority'])
                    else:
                        if type(item['color']) is not list:
                            item['color'] = self.convert_hex_to_list(item
                                                                     ['color'])

                        # Uncomment the comment block below if you want to log
                        # every light action. Warning this will be a crazy
                        # amount of logging!
                        """
                        self.log.info("light Command: %s %s",
                                              item['lightname'], item['color'])
                        """
                        # now do the actual update
                        self.machine.lights[item['lightname']].on(item['color'])
                        # Update our list of lights so we know which priority
                        # last touched it
                        self.light_priorities[item['lightname']] = item['priority']

                # Next, if we have a fade:
                if "fadeend" in item and item.get('fadeend', None):
                    if type(item['dest_color']) is not list:
                        #item['dest_color'] = item['dest_color'].zfill(6)
                        pass
                    if item['blend'] and \
                            (item['dest_color'] == '000000' or\
                             item['dest_color'] == [0, 0, 0]):
                        self.restore_light_state(item['lightname'],
                                               item['priority'],
                                               item['fadeend'])
                    else:
                        if type(item['dest_color']) is not list:
                            item['dest_color'] = self.convert_hex_to_list(
                                item['dest_color'])

                        # Calculate the fade duration:
                        fadems = (item['fadeend'] - self.current_time) * 1000
                        # Uncomment the comment block below if you want to log
                        # every light action. Warning this will be a crazy
                        # amount of logging!
                        """
                        self.log.info("light Command: %s %s, "
                                              "Fade time: %s",
                                              item['lightname'],
                                              item['dest_color'], fadems)
                        """
                        self.machine.lights[item['lightname']].color_with_fade(
                            item['dest_color'],fadems)
                        # Update our list of light priorities so we know which
                        # priority last touched each light. We use this to know
                        # if an update should overwrite the actual light in the
                        # machine.
                        self.light_priorities[item['lightname']] = item['priority']

        current_list=[]

        # If we got any updates while iterating this list, process them now
        if self.update_list:
            self._do_update()

    def convert_hex_to_list(self, inputstring):
        """Takes a string input of hex numbers and returns a list of integers

        Args:
            inputstring (str): incoming hex colors, like ffff00.

        Returns:
            List of colors as integers, like [255, 255, 0]
        """
        output = []
        if not inputstring:
            inputstring = "000000"
        #inputstring = str(inputstring).zfill(6)
        for i in xrange(0, len(inputstring), 2):  # step through every 2 chars
            output.append(int(inputstring[i:i+2], 16))
            # convert from base 16 (hex) to int
        return output

    def run_script(self, lightname, script, priority=0, repeat=True,
                   blend=False, tps=1000, num_repeats=0, callback=None):
        """Runs a light script. Scripts are similar to LightShows, except they
        only apply to single lights and you can "attach" any script to any
        light. Scripts are used anytime you want an light to have more than one
        action. A simple example would be a flash an light. You would make a
        script that turned it on (with your color), then off, repeating
        forever.

        Scripts could be more complex, like cycling through multiple colors,
        blinking out secret messages in Morse code, etc.

        Interally we actually just take a script and dynamically convert it
        into a LightShow (that just happens to only be for a single light), so
        we can have all the other LightShow-like features, including playback
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
            :class:`LightShow` object. Since running a script just sets up and
            runs a regular LightShow, run_script returns the LightShow object.
            In most cases you won't need this, but it's nice if you want to
            know exactly which LightShow was created by this script so you can
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
            self.machine.light_controller.run_script("light1", self.flash_red,
                                                     "4", blend=True)

        Once the "flash_red" script is defined as self.flash_red, you can use
        it anytime for any light. So if you want to flash two lights red, it
        would be:

            self.machine.light_controller.run_script("light1", self.flash_red,
                                                     "4", blend=True)
            self.machine.light_controller.run_script("light2", self.flash_red,
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

        If you'd like to save a reference to the :class:`LightShow` that's
        created by this script, call it like this:

            self.blah = self.machine.light_controller.run_script("light2",
                                                        self.flash_red, "4")
        """

        # convert the steps from the script list that was passed into the
        # format that's used in an LightShow

        LightShow_actions = []

        for step in script:
            if step.get('fade', None):
                color = str(step['color']) + "-f" + str(step['time'])
            else:
                color = str(step['color'])

            color_dic = {lightname: color}
            current_action = {'tocks': step['time'],
                              'lights': color_dic}
            LightShow_actions.append(current_action)
        show = None
        show = LightShow(self.machine, actions=LightShow_actions)
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
              LightShows created from scripts for that lightname, regardless of
              priority.
            - Specify *priority* only to stop (and remove) all active
              LightShows based on scripts running at that priority for all
              lights.
            - Specify *lightname* and *priority* to stop (and remove) all
              active LightShows for that lightname at the specific priority you
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
                LightShows will play over or under it). If you enable an light
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
        :class:`LightController` won't know about it, and your light could be
        overwritten the next time a LightShow, script, or enable command is
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

        Once cleared, :class:`LightController` restore the light's state from
        any commands or shows running at a lower priority.

        Note that this method does not affect running :class:`LightShow` shows,
        so if you clear the :meth:`enable` commands but you have a running
        LightShow which enables that light, then the light will be enablight.
        If you want to absolutely disable the light regardless of whatever
        LightShow is running, then use :meth:`enable` with *color=000000*,
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


class LightShow(object):
    """Represents a LightShow which is a sequential list of lights, colors, and
    timings that can be played back. Individual shows can be started, stopped,
    reset, etc. Shows can be played at any speed, sped up, slowed down, etc.

    Args:
        machine (obj): Parent machine object.
        filename (str): File (and path) of the LightShow yaml file
        actions (list): List of LightShow actions which are passed directly
            instead of read from a yaml file

    If you pass *filename*, it will process the actions based on that file.
    Otherwise it will look for the actions from the list passed via *actions*.
    Either *filename* or *actions* is required.

    """

    def __init__(self, machine, filename=None, actions=None):
        super(LightShow, self).__init__()
        self.log = logging.getLogger("LightShow")
        self.machine = machine
        self.active_lights = {}  # current active lights (and fades) for this show
        # active_lights keys are lightname
        # vals are color, prevcolor, fadestart, fadeend, dest_color
        self.tocks_per_sec = 32  # how many steps per second this show runs at
        # you can safely read this value to determine the current playback rate
        # But don't update it directly to change the speed of a running show.
        # Use the change_speed() method instead.
        self.secs_per_tock = 0  # calculated based on tocks_per_sec
        self.repeat = False  # whether this show repeats when finished
        self.num_repeats = 0  # if self.repeat=True, how many times it repeats
        # self.num_repeats = 0 means it repeats indefinitely until stopped
        self.current_repeat_step = 0  # tracks which repeat we're on, used with
        # num_repeats above
        self.hold = False  # hold the light states when the show ends.
        self.priority = 0  # relative priority of this show
        self.ending = False  # show will end after the current tock ends
        self.running = False  # is this show running currently?
        self.blend = False  # when an light is off in this show, should it allow
        # lower priority lights to show through?
        self.LightShow_actions = None  # show commands from LightShow yaml file
        self.current_location = 0  # index of which command block (tock) a
        # running show is in need to be serviced.
        self.last_action_time = 0.0  # when the last action happened
        self.total_locations = 0  # total number of action locations
        self.current_tock = 0  # index of which tock a running show is in
        self.next_action_time = 0  # time of when the next action happens
        self.callback = None  # if the show should call something when it ends
        # naturally. (Not invoked if show is manually stopped)

        if filename:
            self._load(filename)
        elif actions:
            self._process(actions)
        else:
            self.log.warning("Couldn't set up LightShow as we didn't receive "
                                "a LightShow file or action list as input!")

    def _load(self, filename):
        # Loads a LightShow yaml file from disk
        self.log.debug("Loading light show: %s", filename)

        try:
            LightShow_actions = yaml.load(open(filename, 'r'))
        except:
            self.log.error("Error loading light show: %s", filename)
        else:
            self._process(LightShow_actions)

    def _process(self, LightShow_actions):
        # Process a new LightShow's actions. This is a separate method from
        # load so we can also use it to process new LightShows that we load in
        # ways other than from LightShow files from disk. For example, for light
        # scripts.

        self.log.debug("Processing the LightShow")

        # add this LightShow to lightcontoller's list of registered shows
        # use a weakref so garbage collection will del it if we delete the show
        self.machine.light_controller.registered_shows.append(weakref.proxy(self))

        self.LightShow_actions = LightShow_actions

        # count how many total locations are in the show. We need this later
        # so we can know when we're at the end of a show
        self.total_locations = len(self.LightShow_actions)

        if not self.machine.light_controller.initialized:
            self.machine.light_controller._initialize()

    def play(self, repeat=False, priority=0, blend=False, hold=False,
             tocks_per_sec=32, start_location=-1, callback=None,
             num_repeats=0):
        """Plays a LightShow. There are many parameters you can use here which
        affect how the show is played. This includes things like the playback
        speed, priority, whether this show blends with others, etc. These are
        all set when the show plays. (For example, you could have a LightShow
        file which lights a bunch of lights sequentially in a circle pattern,
        but you can have that circle "spin" as fast as you want depending on
        how you play the show.)

        :param boolean repeat: True/False, whether the show repeats when it's
        done.

        :param integer priority: The relative priority of this show. If there's
        ever a situation where multiple shows (or light commands) want to
        control the same light, the one with the higher priority will win.
        ("Higher" means a bigger number, so a show with priority 2 will
        override a priority 1.)

        :param boolean blend: Controls whether this show "blends" with lower
        priority shows and scripts. For example, if this show turns a light
        off, but a lower priority show has that light set to blue, then the
        light will "show through" as blue while it's off here. If you don't
        want that behavior, set blend to be False. Then off here will be off
        for sure (unless there's a higher priority show or command that turns
        the light on).

        :param boolean hold: If True, then when this LightShow ends, all the
        lights that are on at that time will remain on. If False, it turns them
        all off when the show ends

        :param integer tocks_per_sec: This is how fast your show runs.
        ("Playback speed," in other words. Your LightShow files specify action
        times in terms of 'tocks', like "make this light red for 3 tocks, then
        off for 4 tocks, then a different light on for 6 tocks. When you play a
        show, you specify how many tocks per second you want it to play.
        Default is 32, but you might even want tocks_per_sec of only 1 or 2 if
        your show doesn't need to move than fast. Note this does not affect
        fade rates. So you can have tocks_per_sec of 1 but still have lights
        fade on and off at whatever rate you want. Also the term "tocks" was
        chosen so as not to confuse it with "ticks" which is used by the
        machine loop.

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
            self.show1 = lights.LightShow(self.machine,
            "LightShows\\show1.yaml")

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
        self.machine.light_controller._run_show(self)

    def stop(self, reset=True, hold=False):
        """Stops a LightShow.

        :param boolean reset: True means it resets the show to the beginning.
        False it keeps it where it is so the show can pick up where it left off

        :param boolean hold: Lets you specify that the lights will be held in
        their current state after the show ends. Note that if you have a show
        that's set to hold but you pass hold=False here, it won't work. In that
        case you'd have to set <show>.hold=False and then call this method to
        stop the show. """

        if hold:
            self.hold = True

        self.machine.light_controller._end_show(self, reset)

    def change_speed(self, tocks_per_sec=1):
        """Changes the playback speed of a running LightShow.

        :param integer tocks_per_sec: The new tocks_per_second play rate.

        If you want to change the playback speed by a percentage, you can
        access the current tocks_per_second rate via LightShow's
        tocks_per_second variable. So if you want to double the playback speed
        of your show, you could do something like:

            self.your_show.change_speed(self.your_show.tocks_per_second*2)

        Note that you can't just update the show's tocks_per_second directly
        because we also need to update self.secs_per_tock.
        """
        self.tocks_per_sec = tocks_per_sec
        self.secs_per_tock = 1/float(tocks_per_sec)

    def _advance(self):
        # Advances through the LightShow. This method schedules all the lights
        # that need to be serviced now, tracks the current show's location and
        # handles repeats, and update the show's active_lights list with what
        # they all should be

        # if this show is done and we're just waiting for the final tock
        if self.ending:
            self.machine.light_controller._end_show(self)
            return

        action_loop_count = 0  # Tracks how many loops we've done here
        while self.next_action_time <= self.machine.light_controller.current_time:
            action_loop_count += 1

            # Set the next action time & step to the next location
            self.next_action_time = ((self.LightShow_actions[self.current_location]
                                     ['tocks'] * self.secs_per_tock) +
                                     self.last_action_time)
            self.last_action_time = self.next_action_time

            # create a dictionary of the current actions
            for lightname, color in (self.LightShow_actions[self.current_location]
                                   ['lights'].iteritems()):

                # convert colorwithfade (like 111111-f2) into dictionary of:
                # color:
                # fadestart:
                # fadeend:

                #color = str(color).zfill(6)
                light_dic = {'lightname': lightname, 'color': color,
                             'priority': self.priority, 'blend': self.blend}

                if "-f" in str(color):  # todo save as str from yaml read?
                    color = self._convert_colorwithfades_to_time(color,
                                                            self.secs_per_tock)
                    #light_dic['dest_color'] = str(color['dest_color']).zfill(6)
                    light_dic['dest_color'] = color['dest_color']
                    light_dic['fadestart'] = color['fadestart']
                    light_dic['fadeend'] = color['fadeend']
                    light_dic['color'] = None

                self.machine.light_controller._add_to_update_list(light_dic)

                # If this light is off and not involved in a fade,
                # remove it from the active list
                if lightname in self.active_lights:
                    if (light_dic.get('dest_color', None) == '000000' or \
                            light_dic.get('dest_color', None) is None) \
                            and (light_dic['color'] == '000000'):
                        self.active_lights.pop(lightname)

                else:
                    # Update this show's active lights list with the latest
                    # settings
                    active_lights_dic = {}
                    # loop through current actions
                    if lightname in self.active_lights:
                        # if we have a current entry for this lightname, copy
                        # its color to the prevcolor key. (We need this to
                        # restore fades since we need to know where the fade
                        # started.)
                        active_lights_dic['prevcolor'] = self.active_lights[
                            lightname]['color']

                    active_lights_dic['color'] = light_dic.get('color', None)
                    active_lights_dic['fadestart'] = light_dic.get('fadestart',
                                                                   None)
                    active_lights_dic['fadeend'] = light_dic.get('fadeend', None)
                    active_lights_dic['dest_color'] = light_dic.get('dest_color',
                                                                    None)

                    new_dic = {lightname: active_lights_dic}
                    self.active_lights.update(new_dic)

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

            # If our LightShow is running so fast that it has done a complete
            # loop, then let's just break out of the loop
            if action_loop_count == self.total_locations:
                return

    def _convert_colorwithfades_to_time(self, color, secs_per_tock):
        # Receives the combined color-fade combinations from LightShow files
        # and breaks them out into colors and real time fade targets.

        # Receives inputs of hex colors with fades specified in tocks, like:
        # ff00aa-f2
        # (This is a hex color of #ff00aa with a fade of 2 tocks)

        # Returns a tuple of:
        # color: ff00aa
        # fadestart: time start in real time since epoch, like 123456789012.123
        # fadeend: time target in real time since epoch, like 123456789012.123

        # Look through our dictionary for any "-f" characters indicating fade
        # times that are still in tocks
        colorwithfade = color.split('-f')
        i = {}
        i['dest_color'] = colorwithfade[0]
        i['fadestart'] = self.machine.light_controller.current_time
        i['fadeend'] = ((int(colorwithfade[1]) * secs_per_tock) +
                        self.machine.light_controller.current_time)
        return i
        # todo check to make sure we received a list?


class Playlist(object):
    """A list of :class:`LightShow` objects which are then played sequentially.
    Playlists are useful for things like attract mode where you play one show
    for a few seconds, then another, etc.

    Parameters:

        'machine': Parent machine object

    Each step in a playlist can contain more than one :class:`LightShow`. This
    is useful if you have a lot of little shows for different areas of the
    playfield that you want run at the same time. For example, you might have
    one show that only controls a group of rollover lane lights, and another
    which blinks the lights in the center of the playfield. You can run them at
    the by putting them in the same step in your playlist. (Note you don't need
    to use a playlist if you simply want to run two LightShows at the same
    time. In that case you could just call :meth:`LightShow.play` twice to play
    both shows.

    For each "step" in the playlist, you can specify the number of seconds it
    runs those shows before moving on, or you can specify that one of the shows
    in that step plays a certain number of times and then the playlist moves
    to the next step from there.

    You create a show by creating an instance :class:`Playlist`. Then you
    add LightShows to it via :meth:`add_show`. Finally, you specify the
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
        """Adds a LightShow to this playlist. You have to add at least one show
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

        :param object show: The LightShow object that you're adding to this
        step.

        :param integer num_repeats: How many times you want this show to repeat
        within this step. Note this does not affect when the playlist advances
        to the next step. (That is controlled via :meth:`step_settings`.)
        Rather, this is just how many loops this show plays. A value of 0
        means it repeats indefinitely. (Well, until the playlist advances to
        the next step.) Note that you also have to have repeat=True for it to
        repeat here.

        :param integer tocks_per_sec: How fast you want this show to play. See
        :meth:`LightShow.play` for details.

        :param boolean blend: Whether you want this show to blend with lower
        priority shows below it. See :meth:`LightShow.play` for details.

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
        one of the LightShows in this step is done playing, specify that
        LightShow here. This is required because if there are multiple
        LightShows in this step of the playlist which all end at different
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

        :param integer priority: What priority you want the :class:`LightShow`
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
        for item in self.machine.light_controller.queue:
            if item['playlist'] == self:
                self.machine.light_controller.queue.remove(item)
        if reset:
            self.current_step_position = 0
            self.current_repeat_loop = 0

    def _advance(self):
        #Runs the LightShow(s) at the current step of the plylist and advances
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
        step_trigger_show = self.step_settings_dic[current_step_value]['trigger_show']

        # Now step through all the actions for this step and schedule the
        # LightShows to play
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
            self.machine.light_controller.queue.append({'playlist': self,
                'action_time': (self.machine.light_controller.current_time + step_time)})

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
