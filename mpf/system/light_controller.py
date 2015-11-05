"""Manages the light shows in a pinball machine."""
# light_controller.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/mpf


import logging
import time
from Queue import Queue

from mpf.system.assets import Asset, AssetManager
from mpf.system.config import Config, CaseInsensitiveDict
from mpf.system.file_manager import FileManager
from mpf.system.timing import Timing
from mpf.system.utility_functions import Util


class LightController(object):
    """Manages all the light shows in a pinball machine.

    'light shows' are coordinated light, flasher, coil, and event effects.
    The LightController handles priorities, restores, running and stopping
    Shows, etc. There should be only one per machine.

    Args:
        machine: Parent machine object.
    """

    def __init__(self, machine):
        self.log = logging.getLogger("LightController")
        self.machine = machine

        self.light_queue = []
        self.led_queue = []
        self.event_queue = set()
        self.coil_queue = set()
        self.gi_queue = set()
        self.flasher_queue = set()

        self.registered_light_scripts = CaseInsensitiveDict()

        self.light_update_list = []
        self.led_update_list = []

        self.running_shows = []
        self.registered_tick_handlers = set()

        self.external_show_connected = False
        self.external_show_command_queue = Queue()
        """A thread-safe queue that receives BCP external show commands in the BCP worker
        thread. The light controller reads and proecesses these commands in the main
        thread via a tick handler.
        """
        self.running_external_show_keys = {}
        """Dict of active external light shows that were created via BCP commands. This is
        useful for stopping shows later. Keys are based on the 'name' parameter specified
        when an external show was started, values are references to the external show object.
        """

        self.initialized = False

        self.queue = []
        """A list of dicts which contains things that need to be serviced in the
        future, including: (ot all are always used)
            * lightname
            * priority
            * blend
            * fadeend
            * dest_color
            * color
            * playlist
            * action_time
        """

        self.running_show_keys = dict()
        """Dict of active light shows that were created from scripts. This is
        useful for stopping shows later. Keys are based on the 'key' parameter
        specified when a script was run, values are references to the show
        object.
        """

        self.current_time = time.time()
        """
        The light controller uses a common system time for the entire show system so that every
        "current_time" of a single update cycle is the same everywhere. This
        ensures that multiple shows, scripts, and commands start in-sync
        regardless of any processing lag.
        """

        # register for events
        self.machine.events.add_handler('timer_tick', self._tick)
        self.machine.events.add_handler('init_phase_5',
                                        self._initialize)

        # Tell the mode controller that it should look for light_player items in
        # modes.
        self.machine.mode_controller.register_start_method(self.process_light_player,
                                                 'light_player')

        # Create scripts from config
        self.machine.mode_controller.register_start_method(self.process_light_scripts,
                                                 'light_scripts')

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

        if 'light_scripts' in self.machine.config:
            self.process_light_scripts(self.machine.config['light_scripts'])

        if 'light_player' in self.machine.config:
            self.process_light_player(self.machine.config['light_player'])

    def play_show(self, show, priority=0, **kwargs):
        """Plays a light show.

        Args:
            show: Either the string name of a registered show or a direct
                reference to the show object you want to play.
            priority: The priority this show will play at.
            **kwargs: Contains the parameters and settings to control the
                playing of the show. See Show.play() for options and details.
        """

        try:
            priority += kwargs.pop('show_priority')
        except KeyError:
            pass

        if show in self.machine.shows:
            self.machine.shows[show].play(priority=priority, **kwargs)
        else:  # assume it's a show object?
            show.play(priority=priority, **kwargs)

        try:
            self.running_show_keys[kwargs['key']] = show
        except KeyError:
            pass

    def stop_show(self, show=None, key=None, **kwargs):

        try:
            show.stop(reset=kwargs.get('reset', False),
                      hold=kwargs.get('hold', False))
        except AttributeError:
            if show in self.machine.shows:
                self.machine.shows[show].stop(**kwargs)

        if key:
            self.stop_script(key, **kwargs)

    def stop_shows_by_key(self, key):
        try:
            self.running_show_keys[key].stop()
        except KeyError:
            pass

    def stop_shows_by_keys(self, keys):
        for key in keys:
            self.stop_shows_by_key(key)

    def process_light_scripts(self, config, mode=None, priority=0):
        # config here is localized to light_scripts:

        for k, v in config.iteritems():
            self.registered_light_scripts[k] = v

    def process_light_player(self, config, mode=None, priority=0):
        # config is localized to 'light_player'
        self.log.debug("Processing light_player configuration. Priority: %s",
                       priority)

        event_keys = set()
        shows = set()

        for event_name, actions in config.iteritems():
            if type(actions) is not list:
                actions = Util.string_to_list(actions)

            for this_action in actions:

                # if we don't have a 'show' entry, assume we have a 'script'
                # entry along with light/led names/tags.

                if 'script' in this_action:
                    this_action['show'] = self.create_show_from_script(
                        script=self.registered_light_scripts[this_action['script']],
                        lights=this_action.get('lights', None),
                        leds=this_action.get('leds', None),
                        light_tags=this_action.get('light_tags', None),
                        led_tags=this_action.get('led_tags', None),
                        key=this_action.get('key', None))

                elif 'show' in this_action:
                    try:
                        this_action['show'] = (
                            self.machine.shows[this_action['show']])
                    except KeyError:
                        # If this mode has been started previously then the show
                        # will already be a Show instance and not a string.
                        pass

                if 'priority' in this_action:
                    this_action['priority'] += priority
                else:
                    this_action['priority'] = priority

                event_keys.add(self.add_light_player_show(event_name,
                                                         this_action))

                try:  # if this entry is to stop a script, there will be no show
                    shows.add(this_action['show'])
                except KeyError:
                    pass

        return self.unload_light_player_shows, (event_keys, shows)

    def create_show_from_script(self, script, lights=None, leds=None,
                                light_tags=None, led_tags=None, key=None):
        """Creates a light show from a script.

        Args:
            script: Python dictionary in MPF light script format
            lights: String or iterable of multiples strings of the matrix lights
                that will be included in this show.
            leds: String or iterable of multiples strings of the LEDs that will
                be included in this show.
            light_tags: String or iterable of multiples strings of tags of
                matrix lights that specify which lights will be in this show.
            led_tags: String or iterable of multiples strings of tags of
                LEDs that specify which lights will be in this show.
            key: Object (typically string) that will be used to stop the show
                created by this list later.

        """

        if type(script) is not list:
            script = Util.string_to_list(script)

        action_list = list()

        for step in script:

            this_step = dict()
            this_step['tocks'] = step['tocks']

            if lights:
                this_step['lights'] = dict()

                for light in Util.string_to_list(lights):
                    this_step['lights'][light] = step['color']

            if leds:
                this_step['leds'] = dict()

                for led in Util.string_to_list(leds):
                    this_step['leds'][led] = step['color']

            if light_tags:

                if 'lights' not in this_step:
                    this_step['lights'] = dict()

                for tag in Util.string_to_lowercase_list(light_tags):
                    this_step['lights']['tag|' + tag] = step['color']

            if led_tags:

                if 'leds' not in this_step:
                    this_step['leds'] = dict()

                for tag in Util.string_to_lowercase_list(led_tags):
                    this_step['leds']['tag|' + tag] = step['color']

            action_list.append(this_step)

        return Show(machine=self.machine, config=None, file_name=None,
                    asset_manager=self.asset_manager, actions=action_list)

    def unload_light_player_shows(self, removal_tuple):
        event_keys, shows = removal_tuple

        self.log.debug("Removing light_player events & stopping shows")
        self.machine.events.remove_handlers_by_keys(event_keys)

        for show in shows:
            show.stop()

    def add_light_player_show(self, event, settings):
        if 'priority' in settings:
            settings['show_priority'] = settings['priority']

        if 'hold' not in settings:
            settings['hold'] = False

        if 'action' in settings and settings['action'] == 'stop':

            if 'script' in settings:

                if 'key' in settings:
                    event_key = self.machine.events.add_handler(event,
                                                                self.stop_script,
                                                                **settings)

                else:
                    self.log.error('Cannot add light show stop action since a '
                                   '"script" value was specified but a "key" '
                                   'value was not. Event name: %s', event)
                    return

            else:  # we have a show name specified
                event_key = self.machine.events.add_handler(event,
                                                            self.stop_show,
                                                            **settings)

        else:  # action = 'play'
            event_key = self.machine.events.add_handler(event, self.play_show,
                                                        **settings)

        return event_key

    def sync_ms_next_tick(self, sync_ms):
        """Figures out the next tick show should start based on the passed
        sync_ms value.

        Args:
            sync_ms: Integer of the sync period in ms.

        Returns:
            Int of a tick number

        """

        tick_interval = Timing.HZ / (1000 / sync_ms)
        next_tick = self.machine.tick_num

        if (sync_ms >= Timing.ms_per_tick and
                self.machine.tick_num % tick_interval):
            next_tick = self.machine.tick_num + tick_interval - (
                self.machine.tick_num % tick_interval)

        self.log.debug("Calculating show sync. Sync_ms: %s, Current tick: %s, "
                       "Show start: %s", sync_ms, self.machine.tick_num,
                       next_tick)

        return next_tick

    def _run_show(self, show):
        # Internal method which starts a Show

        # if the show is already playing, it does not try to play again
        if show in self.running_shows:
            return

        show.ending = False
        show.current_repeat_step = 0
        # or in the advance loop?

        if show.sync_ms:
            show.next_action_tick = self.sync_ms_next_tick(show.sync_ms)

        self.running_shows.append(show)
        self.running_shows.sort(key=lambda x: x.priority)

    def _end_show(self, show, reset=None):
        # Internal method which ends a running Show

        self.running_shows = filter(lambda x: x != show, self.running_shows)

        if not show.hold:
            self.restore_lower_lights(show=show)

        if reset is None:
            this_reset = show.reset
        else:
            this_reset = reset

        if this_reset:
            show.current_location = 0

        # if this show was from a script, remove it from running_show_keys

        keys_to_remove = [key for key, value in self.running_show_keys.iteritems()
                          if value == show]

        for key in keys_to_remove:
            del self.running_show_keys[key]

        if show.callback:
            show.callback()

    def restore_lower_lights(self, show=None, priority=0):
        """Restores the lights and LEDs from lower priority shows under this
        show.

        This is only useful if this show is stopped, because otherwise this show
        will just immediately override these restored settings.

        Args:
            show: The show which will set the priority of the lights you want to
                restore.
            priority: An iteger value of the lights you want to restore.

        In both cases it will only restore lights below the priority you pass,
        skipping ones that are at the same value.
        """

        # set the priority we're working with.
        if show:
            priority = show.priority

        # first force the restore of whatever the lights were manually set to

        for light in show.light_states:

            if light.debug:
                light.log.debug("Found this light in a restore_lower_lights meth "
                                "in show.light_states. Light cache priority: %s,"
                                "ending show priority: %s", light.cache['priority'],
                                priority)

            if light.cache['priority'] <= priority:
                light.restore()

        for led in show.led_states:

            if led.debug:
                led.log.debug("Found this LED in a restore_lower_lights meth "
                              "in show.led_states. LED cache priority: %s,"
                              "ending show priority: %s", led.cache['priority'],
                              priority)

            if led.cache['priority'] <= priority:

                led.restore()

        # now see if there are other shows that have these lights in an active
        # state
        for other_show in self.running_shows:
            if other_show.priority < priority:
                other_show.resync()

        # todo the above code could be better. It could only order the restores
        # for the lights and leds that were in this show that just ended?

    def register_tick_handler(self, handler):
        self.registered_tick_handlers.add(handler)

    def deregister_tick_handler(self, handler):
        if handler in self.registered_tick_handlers:
            self.registered_tick_handlers.remove(handler)

    def _tick(self):
        # Runs once per machine loop and services any light updates that are
        # needed.

        # Check the running Shows
        for show in self.running_shows:
            # we use a while loop so we can catch multiple action blocks
            # if the show tocked more than once since our last update
            while show.next_action_tick <= self.machine.tick_num:

                # add the current location to the list to be serviced
                # show.service_locations.append(show.current_location)
                # advance the show to the current time
                show.advance()

                if show.ending:
                    break

        for handler in self.registered_tick_handlers:
            handler()

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
                    item['playlist'].advance()

                # We have to check again since one of these advances could have
                # removed it already
                if item in self.queue:
                    self.queue.remove(item)

        self._do_update()

    def _add_to_light_update_list(self, light, brightness, priority, blend):
        # Adds an update to our update list, with intelligence that if the list
        # already contains an update for this lightname at the same or lower
        # priority, it deletes that one since there's not sense sending a light
        # command that will be immediately overridden by a higher one.
        for item in self.light_update_list:
            if item['light'] == light and item['priority'] <= priority:
                self.light_update_list.remove(item)
        self.light_update_list.append({'light': light,
                                       'brightness': brightness,
                                       'priority': priority,
                                       'blend': blend})  # remove blend?

    def _add_to_led_update_list(self, led, color, fade_ms, priority, blend):
        # See comment from above method
        for item in self.led_update_list:
            if item['led'] == led and item['priority'] <= priority:
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
        # action is a tuple
        # action[0] is string of instruction (pulse, pwm, etc.)
        # action[1] is details for that instruction:
            # for pulse, it's a power multiplier
        self.coil_queue.add((coil, action))

    def _add_to_gi_queue(self, gi, value):
        self.gi_queue.add((gi, value))

    def _add_to_flasher_queue(self, flasher):
        self.flasher_queue.add(flasher)

    def _do_update(self):
        if self.light_update_list:
            self._update_lights()
        if self.led_update_list:
            self._update_leds()
        if self.coil_queue:
            self._fire_coils()
        if self.event_queue:
            self._fire_events()
        if self.gi_queue:
            self._update_gis()
        if self.flasher_queue:
            self._update_flashers()

    def _fire_coils(self):
        for coil in self.coil_queue:
            if coil[1][0] == 'pulse':
                coil[0].pulse(power=coil[1][1])
        self.coil_queue = set()

    def _fire_events(self):
        for event in self.event_queue:
            self.machine.events.post(event)
        self.event_queue = set()

    def _update_gis(self):
        for gi in self.gi_queue:
            gi[0].enable(brightness=gi[1])
        self.gi_queue = set()

    def _update_flashers(self):
        for flasher in self.flasher_queue:
            flasher.flash()
        self.flasher_queue = set()

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

                if item['led'].debug:
                    item['led'].log.debug("Applying update to LED from the Show "
                                          "Controller")

                item['led'].color(color=item['color'],
                                  fade_ms=item['fade_ms'],
                                  priority=item['priority'],
                                  blend=item['blend'],
                                  cache=False)

            elif item['led'].debug:
                item['led'].log.debug("Show Controller has an update for this "
                                      "LED, but the update is priority %s while "
                                      "the current priority of the LED is %s. "
                                      "The update will not be applied.",
                                      item['priority'],
                                      item['led'].state['priority'])

        self.led_update_list = []

    def run_registered_script(self, script_name, **kwargs):

        return self.run_script(
            script=self.registered_light_scripts[script_name], **kwargs)

    def run_script(self, script, lights=None, leds=None, repeat=True,
                   callback=None, key=None, **kwargs):
        """Runs a light script.

        Args:
            script: A list of dictionaries of script commands. (See below)
            lights: A light name or list of lights this script will be applied
                to.
            leds: An LED name or a list of LEDs this script will be applied to.
            repeat (bool): Whether the script repeats (loops).
            callback: A method that will be called when this script stops.
            key: A key that can be used to later stop the light show this script
                creates. Typically a unique string. If it's not passed, it will
                either be the first light name or the first LED name.
            **kwargs: Since this method just builds a Light Show, you can use
                any other Light Show attribute here as well, such as
                tocks_per_sec, blend, repeat, num_repeats, etc.

        Returns:
            :class:`Show` object. Since running a script just sets up and
            runs a regular Show, run_script returns the Show object.
            In most cases you won't need this, but it's nice if you want to
            know exactly which Show was created by this script so you can
            stop it later. (See the examples below for usage.)

        Scripts are similar to Shows, except they only apply to single lights
        and you can "attach" any script to any light. Scripts are used anytime
        you want an light to have more than one action. A simple example would
        be a flash an light. You would make a script that turned it on (with
        your color), then off, repeating forever.

        Scripts could be more complex, like cycling through multiple colors,
        blinking out secret messages in Morse code, etc.

        Interally we actually just take a script and dynamically convert it
        into a Show (that just happens to only be for a single light), so
        we can have all the other Show-like features, including playback
        speed, repeats, blends, callbacks, etc.

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
            self.flash_red.append({"color": 'ff0000', 'tocks': 1})
            self.flash_red.append({"color": '000000', 'tocks': 1})
            self.machine.show_controller.run_script(script=self.flash_red,
                                                    lights='light1',
                                                    priority=4,
                                                    blend=True)

        Once the "flash_red" script is defined as self.flash_red, you can use
        it anytime for any light or LED. You can also define lights as a list,
        like this:

            self.machine.show_controller.run_script(script=self.flash_red,
                                                    lights=['light1', 'light2'],
                                                    priority=4,
                                                    blend=True)

        Most likely you would define your scripts once when the game loads and
        then call them as needed.

        You can also make more complex scripts. For example, here's a script
        which smoothly cycles an RGB light through all colors of the rainbow:

            self.rainbow = []
            self.rainbow.append({'color': 'ff0000', 'tocks': 1, 'fade': True})
            self.rainbow.append({'color': 'ff7700', 'tocks': 1, 'fade': True})
            self.rainbow.append({'color': 'ffcc00', 'tocks': 1, 'fade': True})
            self.rainbow.append({'color': '00ff00', 'tocks': 1, 'fade': True})
            self.rainbow.append({'color': '0000ff', 'tocks': 1, 'fade': True})
            self.rainbow.append({'color': 'ff00ff', 'tocks': 1, 'fade': True})

        If you have single color lights, your *color* entries in your script
        would only contain a single hex value for the intensity of that light.
        For example, a script to flash a single-color light on-and-off (which
        you can apply to any light):

            self.flash = []
            self.flash.append({"color": "ff", "tocks": 1})
            self.flash.append({"color": "00", "tocks": 1})

        If you'd like to save a reference to the :class:`Show` that's
        created by this script, call it like this:

            self.blah = self.machine.show_controller.run_script("light2",
                                                        self.flash_red, "4",
                                                        tocks_per_sec=2)
         """

        # convert the steps from the script list that was passed into the
        # format that's used in an Show

        show_actions = []

        if type(lights) is str:
            lights = [lights]

        if type(leds) is str:
            leds = [leds]

        if not key:
            try:
                key = lights[0]
            except (TypeError, IndexError):
                try:
                    key = leds[0]
                except (TypeError, IndexError):
                    return False

        for step in script:
            if step.get('fade', None):
                color = str(step['color']) + "-f" + str(step['tocks'])
            else:
                color = str(step['color'])

            current_action = {'tocks': step['tocks']}

            if lights:
                current_action['lights'] = dict()
                for light in Util.string_to_list(lights):
                    current_action['lights'][light] = color

            if leds:
                current_action['leds'] = dict()
                for led in Util.string_to_list(leds):
                    current_action['leds'][led] = color

            show_actions.append(current_action)

        show = Show(machine=self.machine, config=None, file_name=None,
                    asset_manager=self.asset_manager, actions=show_actions)

        show.play(repeat=repeat, callback=callback, **kwargs)

        self.running_show_keys[key] = show

        return show

    def stop_script(self, key, **kwargs):
        """Stops and removes the light show that was created by a light script.

        Args:
            key: The key that was specified in run_script().
            **kwargs: Not used, included in case this method is called via an
                event handler that might contain other random paramters.

        """

        try:
            self.stop_show(show=self.running_show_keys[key], **kwargs)
            del self.running_show_keys[key]
        except KeyError:
            pass

    def add_external_show_start_command_to_queue(self, name, priority=0, blend=True, leds=None,
                            lights=None, flashers=None, gis=None):
        """Called by BCP worker thread when an external show start command is received
        via BCP.  Adds the command to a thread-safe queue where it will be processed
        by the main thread.

        Args:
            name: The name of the external show, used as a key for subsequent show commands.
            priority: Integer value of the relative priority of this show.
            blend: When an light is off in this show, should it allow lower
                priority lights to show through?
            leds: A list of led device names that will be used in this show.
            lights: A list of light device names that will be used in this show.
            flashers: A list of flasher device names that will be used in this show.
            gis: A list of GI device names that will be used in this show.
        """
        if not self.external_show_connected:
            self.register_tick_handler(
                self._update_external_shows)
            self.external_show_connected = True

        self.external_show_command_queue.put((self._process_external_show_start_command,
                                              (name, priority, blend, leds,
                                               lights, flashers, gis)))

    def add_external_show_stop_command_to_queue(self, name):
        """Called by BCP worker thread when an external show stop command is received
        via BCP.  Adds the command to a thread-safe queue where it will be processed
        by the main thread.

        Args:
            name: The name of the external show.
        """
        self.external_show_command_queue.put((self._process_external_show_stop_command, (name,)))

    def add_external_show_frame_command_to_queue(self, name, led_data=None, light_data=None,
                                                 flasher_data=None, gi_data=None):
        """Called by BCP worker thread when an external show frame command is received
        via BCP.  Adds the command to a thread-safe queue where it will be processed
        by the main thread.

        Args:
            name: The name of the external show.
            led_data: A string of concatenated hex color values for the leds in the show.
            light_data: A string of concatenated hex brightness values for the lights in the show.
            flasher_data: A string of concatenated pulse time (ms) values for the flashers in the show.
            gi_data: A string of concatenated hex brightness values for the GI in the show.
        """
        self.external_show_command_queue.put((self._process_external_show_frame_command,
                                              (name, led_data, light_data,
                                               flasher_data, gi_data)))

    def _update_external_shows(self):
        """Processes any pending BCP external show commands.  This function is called
        in the main processing thread and is a tick handler function.
        """
        while not self.external_show_command_queue.empty():
            update_method, args = self.external_show_command_queue.get(False)
            update_method(*args)

    def _process_external_show_start_command(self, name, priority, blend, leds,
                                             lights, flashers, gis):
        """Processes an external show start command.  Runs in the main processing thread.

        Args:
            name: The name of the external show, used as a key for subsequent show commands.
            priority: Integer value of the relative priority of this show.
            blend: When an light is off in this show, should it allow lower
                priority lights to show through?
            leds: A list of led device names that will be used in this show.
            lights: A list of light device names that will be used in this show.
            flashers: A list of flasher device names that will be used in this show.
            gis: A list of GI device names that will be used in this show.
        """
        if name not in self.running_external_show_keys:
            self.running_external_show_keys[name] = ExternalShow(self.machine,
                                                                 name, priority, blend, leds,
                                                                 lights, flashers, gis)

    def _process_external_show_stop_command(self, name):
        """Processes an external show stop command.  Runs in the main processing thread.

        Args:
            name: The name of the external show.
        """
        try:
            self.running_external_show_keys[name].stop()
            del self.running_external_show_keys[name]
        except KeyError:
            pass

        # TODO: Would like to de-register the tick handler for external shows here
        # However, since this function is called from the tick handler while
        # iterating over the set of handlers, the list cannot be modified at
        # this point in time.  Since this function is so quick, it's probably
        # okay to leave it for now rather than figure out a complicated way to
        # remove it.

    def _process_external_show_frame_command(self, name, led_data, light_data,
                                             flasher_data, gi_data):
        """Processes an external show frame command.  Runs in the main processing thread.

        Args:
            name: The name of the external show.
            led_data: A string of concatenated hex color values for the leds in the show.
            light_data: A string of concatenated hex brightness values for the lights in the show.
            flasher_data: A string of concatenated pulse time (ms) values for the flashers in the show.
            gi_data: A string of concatenated hex brightness values for the GI in the show.        """
        if name not in self.running_external_show_keys:
            return

        if led_data:
            self.running_external_show_keys[name].update_leds(led_data)

        if light_data:
            self.running_external_show_keys[name].update_lights(light_data)

        if flasher_data:
            self.running_external_show_keys[name].update_gis(flasher_data)

        if gi_data:
            self.running_external_show_keys[name].update_flashers(gi_data)


class Show(Asset):

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

        self.tocks_per_sec = 1  # how many steps per second this show runs at
        # you can safely read this value to determine the current playback rate
        # But don't update it directly to change the speed of a running show.
        # Use the change_speed() method instead.
        self.ticks_per_tock = 0  # calculated based on tocks_per_sec
        self.repeat = False  # whether this show repeats when finished
        self.num_repeats = 0  # if self.repeat=True, how many times it repeats
        # self.num_repeats = 0 means it repeats indefinitely until stopped
        self.current_repeat_step = 0  # tracks which repeat we're on, used with
        # num_repeats above
        self.hold = False  # hold the item states when the show ends.
        self.reset = True  # reset back to the first step when the show ends
        self.priority = 0  # relative priority of this show
        self.ending = False  # show will end after the current tock ends
        self.blend = False  # when an light is off in this show, should it allow
        # lower priority lights to show through?
        self.debug = False
        self.current_location = 0  # index of which step (tock) a running show is
        self.total_locations = 0  # total number of action locations
        self.current_tock = 0  # index of which tock a running show is in
        self.next_action_tick = 0  # tick number of when the next action happens
        self.callback = None  # if the show should call something when it ends
        # naturally. (Not invoked if show is manually stopped)
        self.sync_ms = 0

        self.light_states = {}
        self.led_states = {}
        self.stop_key = None

        self.loaded = False
        self.notify_when_loaded = set()
        self.loaded_callbacks = list()
        self.show_actions = list()

    def do_load(self, callback, show_actions=None):

        self.show_actions = list()

        self.asset_manager.log.debug("Loading Show %s", self.file_name)

        if not show_actions:
            show_actions = self.load_show_from_disk()

        if type(show_actions) is not list:
            self.asset_manager.log.warning("%s is not a valid YAML file. "
                                           "Skipping show.", self.file_name)
            return False

        for step_num in range(len(show_actions)):
            step_actions = dict()

            step_actions['tocks'] = show_actions[step_num]['tocks']

            # look for empty steps. If we find them we'll just add their tock
            # time to the previous step.

            if len(show_actions[step_num]) == 1:  # 1 because it still has tocks

                show_actions[-1]['tocks'] += step_actions['tocks']
                continue

            # Lights
            if ('lights' in show_actions[step_num] and
                    show_actions[step_num]['lights']):

                light_actions = dict()

                for light in show_actions[step_num]['lights']:

                    if 'tag|' in light:
                        tag = light.split('tag|')[1]
                        light_list = self.machine.lights.items_tagged(tag)
                    else:  # create a single item list of the light object
                        try:
                            light_list = [self.machine.lights[light]]
                        except KeyError:
                            self.asset_manager.log.warning("Found invalid "
                                "light name '%s' in show. Skipping...", light)
                            continue

                    value = show_actions[step_num]['lights'][light]

                    # convert / ensure lights are single ints
                    if type(value) is str:
                        value = Util.hex_string_to_int(
                            show_actions[step_num]['lights'][light])

                    if type(value) is int and value > 255:
                        value = 255

                    for light_ in light_list:
                        light_actions[light_] = value

                        # make sure this light is in self.light_states
                        if light_ not in self.light_states:
                            self.light_states[light_] = 0

                step_actions['lights'] = light_actions

            # Events
            # make sure events is a list of strings
            if ('events' in show_actions[step_num] and
                    show_actions[step_num]['events']):

                event_list = (Util.string_to_list(
                    show_actions[step_num]['events']))

                step_actions['events'] = event_list

            # Coils
            if ('coils' in show_actions[step_num] and
                    show_actions[step_num]['coils']):

                coil_actions = dict()

                for coil in show_actions[step_num]['coils']:

                    try:
                        this_coil = self.machine.coils[coil]
                    except:
                        # this coil name is invalid
                        self.asset_manager.log.warning("WARNING: Found invalid "
                            "coil name '%s' in show. Skipping...", coil)
                        continue

                    value = show_actions[step_num]['coils'][coil]

                    # process the value into a tuple which will be
                    # value[0] = string of action type (pulse, pwm, etc)
                    # value[1] = int / float of pulse value

                    # split the value on '-p' to look for a power setting
                    value = value.split('-p')

                    # if there's no power setting, append 100
                    if len(value) == 1:
                        value.append(100)

                    # convert the 0-100 value to 0.0-1.0 float
                    value[1] = float(value[1]) / 100.0

                    # convert value list into tuple
                    value = (value[0], value[1])

                    coil_actions[this_coil] = value

                step_actions['coils'] = coil_actions

            # Flashers
            if ('flashers' in show_actions[step_num] and
                    show_actions[step_num]['flashers']):

                flasher_set = set()

                for flasher in Util.string_to_list(
                        show_actions[step_num]['flashers']):

                    if 'tag|' in flasher:
                        tag = flasher.split('tag|')[1]
                        flasher_list = self.machine.flashers.items_tagged(tag)
                    else:  # create a single item list of the flasher objects
                        try:
                            flasher_list = [self.machine.flashers[flasher]]
                        except KeyError:
                            self.asset_manager.log.warning("Found invalid "
                                "flasher name '%s' in show. Skipping...",
                                flasher)
                            continue

                    for flasher_ in flasher_list:
                        flasher_set.add(flasher_)

                step_actions['flashers'] = flasher_set

            # GI
            if ('gis' in show_actions[step_num] and
                    show_actions[step_num]['gis']):

                gi_actions = dict()

                for gi in show_actions[step_num]['gis']:

                    if 'tag|' in gi:
                        tag = gi.split('tag|')[1]
                        gi_list = self.machine.gi.items_tagged(tag)
                    else:  # create a single item list of the light object
                        try:
                            gi_list = [self.machine.gi[gi]]
                        except KeyError:
                            self.asset_manager.log.warning("Found invalid "
                                "GI name '%s' in show. Skipping...",
                                gi)
                            continue

                    value = show_actions[step_num]['gis'][gi]

                    # convert / ensure flashers are single ints
                    if type(value) is str:
                        value = Util.hex_string_to_int(value)

                    if type(value) is int and value > 255:
                        value = 255

                    for gi_ in gi_list:
                        gi_actions[gi_] = value

                step_actions['gis'] = gi_actions

            # LEDs
            if ('leds' in show_actions[step_num] and
                    show_actions[step_num]['leds']):

                led_actions = dict()

                for led in show_actions[step_num]['leds']:

                    if 'tag|' in led:
                        tag = led.split('tag|')[1]
                        led_list = self.machine.leds.items_tagged(tag)
                    else:  # create a single item list of the led object
                        try:
                            led_list = [self.machine.leds[led]]
                        except KeyError:
                            self.asset_manager.log.warning("Found invalid "
                                "LED name '%s' in show. Skipping...", led)
                            continue

                    value = show_actions[step_num]['leds'][led]

                    # ensure led is list is of 4 ints: [r, g, b, fade_tocks]
                    if type(value) is list:
                        # ensure our list is exactly 4 items
                        if len(value) < 4:
                            # pad to 4 with zeros
                            value.extend([0] * (4 - len(value)))
                        elif len(value) > 4:
                            value = value[0:4]

                    fade = 0

                    if type(value) is str:
                        if '-f' in value:
                            fade = value.split('-f')

                    # convert our color of hexes to a list of ints
                    value = Util.hex_string_to_list(value)
                    value.append(fade)

                    for led_ in led_list:
                        led_actions[led_] = value

                        # make sure this led is in self.led_states
                        if led_ not in self.led_states:
                            self.led_states[led_] = {
                                'current_color': [0, 0, 0],
                                'destination_color': [0, 0, 0],
                                'start_color': [0, 0, 0],
                                'fade_start': 0,
                                'fade_end': 0}

                step_actions['leds'] = led_actions

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

    def play(self, repeat=False, priority=0, blend=False, hold=None,
             tocks_per_sec=30, start_location=None, callback=None,
             num_repeats=0, sync_ms=0, reset=True, **kwargs):
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
                their final show state when the show ends. Default is None which
                means hold will be False if the show has more than one step, and
                True if there is only one step.
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
                way through. Also used for restarting shows that you paused. A
                negative value will count backwards from the end (-1 is the last
                position, -2 is second to last, etc.).
            callback: A callback function that is invoked when the show is
                stopped.
            num_repeats: Integer of how many times you want this show to repeat
                before stopping. A value of 0 means that it repeats
                indefinitely. Note this only works if you also have repeat=True.
            sync_ms: Number of ms of the show sync cycle. A value of zero means
                this show will also start playing immediately. See the full MPF
                documentation for details on how this works.
            reset: Boolean which controls whether this show will reset to its
                first position once it ends. Default is True.
            **kwargs: Not used, but included in case this method is used as an
                event handler which might include additional kwargs.
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
                                    num_repeats=num_repeats,
                                    sync_ms=sync_ms)
            self.load()
            return False

        if hold is not None:
            self.hold = hold
        elif self.total_locations == 1:
            self.hold = True

        if self.total_locations > 1:
            self.repeat = repeat

        self.priority = int(priority)
        self.blend = blend
        self.tocks_per_sec = tocks_per_sec
        self.ticks_per_tock = Timing.HZ/float(tocks_per_sec)
        self.callback = callback
        self.num_repeats = num_repeats
        self.sync_ms = sync_ms
        self.reset = reset

        if start_location is not None:
            # if you don't specify a start location, it will start where it
            # left off (if you stopped it with reset=False). If the show has
            # never been run, it will start at 0 per the initialization

            if start_location < 0:
                self.current_location = self.total_locations + start_location
            else:
                self.current_location = start_location

        self.machine.light_controller._run_show(self)

    def load_show_from_disk(self):
        return FileManager.load(self.file_name)

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
        """Stops the Light Show.

        Note you can also use this method to clear a stopped show's held lights
        and LEDs by passing hold=False.

        Args:
            reset: Boolean which controls whether the show will reset its
                current position back to zero. Default is True.
            hold: Boolean which controls whether the show will hold its current
                lights and LEDs in whatever state they are now, including their
                priorities. Default is None which will just use whatever the
                show setting was when you played it, but you can force it to
                hold or not with True or False here.
        """

        if hold:
            self.hold = True
        elif hold is False:  # if it's None we don't assume False
            self.hold = False

        self.machine.light_controller._end_show(self, reset)

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
        because we also need to update self.ticks_per_tock.
        """
        self.tocks_per_sec = tocks_per_sec
        self.ticks_per_tock = Timing.HZ/float(tocks_per_sec)

    def advance(self):

        # Internal method which advances the show to the next step
        if self.ending:
            self.machine.light_controller._end_show(self)
            return

        action_loop_count = 0  # Tracks how many loops we've done in this call
        # Used to detect if a show is running too slow

        while (self.next_action_tick <=
               self.machine.tick_num):
            action_loop_count += 1

            # Set the next action time & step to the next location
            self.next_action_tick = ((self.show_actions[self.current_location]
                                     ['tocks'] * self.ticks_per_tock) +
                                     self.machine.tick_num)

            if self.debug:
                print "Current tick", self.machine.tick_num
                print "Next Tick:", self.next_action_tick
                print "current location tocks", self.show_actions[self.current_location]['tocks']
                print "ticks per tock", self.ticks_per_tock

        # create a dictionary of the current items of each type, combined with
        # the show details, that we can throw up to our queue

        for item_type, item_dict in (self.show_actions[self.current_location].
                                     iteritems()):

            if item_type == 'lights':

                for light_obj, brightness in item_dict.iteritems():

                    self.machine.light_controller._add_to_light_update_list(
                        light=light_obj,
                        brightness=brightness,
                        priority=self.priority,
                        blend=self.blend)

                    # update the current state
                    self.light_states[light_obj] = brightness

            elif item_type == 'leds':

                current_time = time.time()

                for led_obj, led_dict in item_dict.iteritems():

                    self.machine.light_controller._add_to_led_update_list(
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
                    self.machine.light_controller._add_to_event_queue(event)

            elif item_type == 'coils':

                for coil_obj, coil_action in item_dict.iteritems():
                    self.machine.light_controller._add_to_coil_queue(
                        coil=coil_obj,
                        action=coil_action)

            elif item_type == 'gis':
                for gi, value in item_dict.iteritems():
                    self.machine.light_controller._add_to_gi_queue(
                        gi=gi,
                        value=value)

            elif item_type == 'flashers':
                for flasher in item_dict:
                    self.machine.light_controller._add_to_flasher_queue(
                        flasher=flasher)

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

    def resync(self):
        """Causes this show to do a one-time update to resync all the LEDs and
        lights in the show with where they should be now. This is used when a
        higher priority show stops so lower priority shows can put all the
        lights back to how they want them.
        """

        for light_obj, brightness in self.light_states.iteritems():
            self.machine.light_controller._add_to_light_update_list(
                light=light_obj,
                brightness=brightness,
                priority=self.priority,
                blend=self.blend)

        for led_obj, led_dict in self.led_states.iteritems():
            self.machine.light_controller._add_to_led_update_list(
                led=led_obj,
                color=led_dict['current_color'],
                fade_ms=0,
                priority=self.priority,
                blend=self.blend)


class Playlist(object):
    """A list of :class:`Show` objects which are then played sequentially.

    Playlists are useful for things like attract mode where you play one show
    for a few seconds, then another, etc.

    Args:
        machine: The main MachineController object

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
        self.step_settings_dic = {}  # dict with step_num as the key. Values:
                                     # time - sec this entry runs
                                     # trigger_show
                                     # hold
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

        Args:

            step_num: Interger of which step number you're adding this show to.
                You have to specify this since it's possible to add multiple
                shows to the same step (in cases where you want them both to
                play at the same time during that step). If you want the same
                show to play in multiple steps, then add it multiple times (once
                to each step). The show plays starting with the lowest number
                step and then moving on. Ideally they'd be 1, 2, 3... but it
                doesn't matter. If you have step numbers of 1, 2, 5... then the
                player will figure it out.
            show: The Show object that you're adding to this step.
            num_repeats: Integer of how many times you want this show to repeat
                within this step. Note this does not affect when the playlist
                advances to the next step. (That is controlled via
                :meth:`step_settings`.) Rather, this is just how many loops this
                show plays. A value of 0 means it repeats indefinitely. (Well,
                until the playlist advances to the next step.) Note that you
                also have to have repeat=True for it to repeat here.
            tocks_per_sec: Integer of how fast you want this show to play. See
                :meth:`Show.play` for details.
            blend: Boolean of whether you want this show to blend with lower
                priority shows below it. See :meth:`Show.play` for details.
            repeat: Boolean which causes the show to keep repeating until the
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

    def step_settings(self, step, time=0, trigger_show=None, hold=False):
        """Used to configure the settings for a step in a :class:`Playlist`.
        This configuration is required for each step. The main thing you use
        this for is to specify how the playlist knows to move on to the next
        step.

        Args:

        step: Integer for which step number you're configuring
        time: Integer of the time in seconds that you want this step to run
            before moving on to the next one.
        trigger_show: If you want to move to the next step after
            one of the Shows in this step is done playing, pass that show's object
            here. This is required because if there are multiple
            Shows in this step of the playlist which all end at different
            times, we wouldn't know which one to watch in order to know when to
            move on.

        Note that you can have repeats with a trigger show, but in that case
        you also need to have the num_repeats specified. Otherwise if you have
        your trigger show repeating forever then the playlist will never move
        on. (In that case use the *time* parameter to move on based on time.)
        """
        settings = {'time': time,
                    'trigger_show': trigger_show,
                    'hold': hold}
        self.step_settings_dic.update({step: settings})

    def start(self, priority=0, repeat=True, repeat_count=0, reset=True):
        """Starts playing a playlist. You can only use this after you've added
        at least one show via :meth:`add_show` and configured the settings for
        each step via :meth:`step_settings`.

        Args

        priority: Integer of what priority you want the :class:`Show` shows in
            this playlist to play at. These shows will play "on top" of
            lower priority stuff, but "under" higher priority things.
        repeat: Controls whether this playlist to repeats when it's finished.
        repeat_count: How many times you want this playlist to
            repeat before it stops itself. (Must be used with *repeat=True* above.)
            A value of 0 here means that this playlist repeats forever until you
            manually stop it. (This is ideal for attract mode.)
        reset: Boolean which controls whether you want this playlist to
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

    def stop(self, reset=True, hold=None):
        """Stops a playlist. Pretty simple.

        Args:
            reset: If *True*, it resets the playlist tracking counter back to
                the beginning. You can use *False* here if you want to stop and
                then restart a playlist to pick up where it left off.
            hold: Boolean which specifies whether this playlist should should
                hold the lights and LEDs in their current states. Default is
                None which means it inherits whatever the shows or playlist
                settings were, but you can force it True or False if you want
                here.
        """
        self.running = False

        for action in self.step_actions:
            if action['step_num'] == self.steps[self.current_step_position-1]:
                # we have to use the "-1" above because the playlist current
                # position represents the *next* step of shows to play. So when
                # we stop the current show, we have to come back one.
                action['show'].stop(hold=hold)

        for item in self.machine.light_controller.queue:
            if item['playlist'] == self:
                self.machine.light_controller.queue.remove(item)
        if reset:
            self.current_step_position = 0
            self.current_repeat_loop = 0

    def _advance(self):
        # Runs the Show(s) at the current step of the plylist and advances
        # the pointer to the next step

        # If we stop at a step with a trigger show, the stopping of the trigger
        # show will call advance(), so we just return here so this last step
        # doesn't play.
        if not self.running:
            return

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
                    if action['show'] in (
                            self.machine.light_controller.running_shows):
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
        # shows to play
        for action in self.step_actions:
            if action['step_num'] == current_step_value:
                show = action['show']
                num_repeats = action['num_repeats']
                tocks_per_sec = action['tocks_per_sec']
                blend = action['blend']
                repeat = action['repeat']

                if show == step_trigger_show:
                    # This show finishing will be used to trigger the
                    # advancement to the next step.
                    callback = self._advance

                    if num_repeats == 0:
                        self.log.warning("Found a trigger show that was set to"
                                         " repeat indefinitely. Changing repeat"
                                         " to 1.")
                        num_repeats = 1

                else:
                    callback = None

                show.play(repeat=repeat, priority=self.priority, blend=blend,
                          tocks_per_sec=tocks_per_sec, num_repeats=num_repeats,
                          callback=callback,
                          hold=self.step_settings_dic[current_step_value]['hold'])

        # if we don't have a trigger_show but we have a time value for this
        # step, set up the time to move on
        if step_time and not step_trigger_show:
            self.machine.light_controller.queue.append({'playlist': self,
                'action_time': (self.machine.light_controller.current_time +
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


class ExternalShow(object):

    def __init__(self, machine, name, priority=0, blend=True, leds=None,
                 lights=None, flashers=None, gis=None):

        self.machine = machine
        self.name = name
        self.priority = priority
        self.blend = blend
        self.name = None
        self.leds = list()
        self.lights = list()
        self.flashers = list()
        self.gis = list()

        if leds:
            self.leds = Util.string_to_list(leds)
            self.leds = [self.machine.leds[x] for x in self.leds]

        if lights:
            self.lights = Util.string_to_list(lights)
            self.lights = [self.machine.lights[x] for x in self.lights]

        if flashers:
            self.flashers = Util.string_to_list(flashers)
            self.flashers = [self.machine.flashers[x] for x in self.flashers]

        if gis:
            self.gis = Util.string_to_list(gis)
            self.gis = [self.machine.gis[x] for x in self.gis]

    def update_leds(self, data):
        for led, color in zip(self.leds, Util.chunker(data, 6)):
            self.machine.light_controller._add_to_led_update_list(
                led, Util.hex_string_to_list(color), 0, self.priority,
                self.blend)

    def update_lights(self, data):
        for light, brightness in zip(self.lights, Util.chunker(data, 2)):
            self.machine.light_controller._add_to_light_update_list(
                light, Util.hex_string_to_int(brightness), self.priority, self.blend)

    def update_gis(self, data):
        for gi, brightness in zip(self.lights, Util.chunker(data, 2)):
            self.machine.light_controller._add_to_gi_queue(
                gi, Util.hex_string_to_int(brightness))

    def update_flashers(self, data):
        for flasher, flash in zip(self.flashers, data):
            if flash:
                self.machine.light_controller._add_to_flasher_queue(flasher)

    def stop(self):
        for led in self.leds:
            if led.cache['priority'] <= self.priority:
                led.restore()

        for light in self.lights:
            if light.cache['priority'] <= self.priority:
                light.restore()

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
