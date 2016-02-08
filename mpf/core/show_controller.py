"""Manages the shows (lights, LEDs, flashers, coils, etc.) in a
pinball machine."""

import logging
from queue import Queue

from mpf.core.rgb_color import RGBColor
from mpf.core.utility_functions import Util
from mpf.assets.show import Show


class ShowController(object):
    """Manages all the shows in a pinball machine.

    'hardware shows' are coordinated light, flasher, coil, and event effects.
    The ShowController handles priorities, restores, running and stopping
    Shows, etc. There should be only one per machine.

    Args:
        machine: Parent machine object.
    """

    def __init__(self, machine):
        self.log = logging.getLogger("ShowController")
        self.machine = machine

        self.light_queue = []
        self.led_queue = []
        self.event_queue = set()
        self.coil_queue = set()
        self.gi_queue = set()
        self.flasher_queue = set()
        self.trigger_queue = []

        self.light_update_list = []
        self.led_update_list = []

        self.running_shows = []
        self.registered_tick_handlers = set()
        self.current_tick_time = 0

        self.external_show_connected = False
        self.external_show_command_queue = Queue()
        """A thread-safe queue that receives BCP external show commands in
        the BCP worker
        thread. The light controller reads and processes these commands in
        the main
        thread via a tick handler.
        """
        self.running_external_show_keys = {}
        """Dict of active external light shows that were created via BCP
        commands. This is
        useful for stopping shows later. Keys are based on the 'name'
        parameter specified
        when an external show was started, values are references to the
        external show object.
        """

        self.initialized = False

        self.queue = []
        """A list of dicts which contains things that need to be serviced in
        the
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
        """Dict of active shows that were created from scripts. This is
        useful for stopping shows later. Keys are based on the 'key' parameter
        specified when a script was run, values are references to the show
        object.
        """

        # Setup the callback schedule (every frame)
        self.machine.clock.schedule_interval(self._tick, 0)

        # Registers Show with the asset manager
        Show.initialize(self.machine)

    def play_show(self, show, priority=0, **kwargs):
        """Plays a show.

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
        elif isinstance(show, Show):
            show.play(priority=priority, **kwargs)
        else:
            raise ValueError("Can't play show '{}' since it's not a valid "
                             "show name or show object".format(show))

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
            self.machine.light_scripts.stop_light_script(key, **kwargs)

    def stop_shows_by_key(self, key):
        try:
            self.running_show_keys[key].stop()
        except KeyError:
            pass

    def stop_shows_by_keys(self, keys):
        for key in keys:
            self.stop_shows_by_key(key)

    def unload_show_player_shows(self, removal_tuple):
        event_keys, shows = removal_tuple

        self.log.debug("Removing show_player events & stopping shows")
        self.machine.events.remove_handlers_by_keys(event_keys)

        for show in shows:
            try:
                show.stop()
            except AttributeError:
                pass

    def add_show_player_show(self, event, settings):
        if 'priority' in settings:
            settings['show_priority'] = settings['priority']

        if 'hold' not in settings:
            settings['hold'] = False

        if 'action' in settings and settings['action'] == 'stop':

            if 'script' in settings:

                if 'key' in settings:
                    event_key = self.machine.events.add_handler(event,
                        self.machine.light_scripts.stop_light_script,
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

    def _run_show(self, show):
        # Internal method which starts a Show

        # if the show is already playing, it does not try to play again
        if show in self.running_shows:
            return

        show.ending = False
        show.running = True
        show.current_loop_number = 0
        # or in the advance loop?

        # Set the Show to begin immediately
        show.next_step_time = self.current_tick_time
        if show.sync_ms:
            show.next_step_time += show.sync_ms / 1000.0

        self.running_shows.append(show)
        self.running_shows.sort(key=lambda x: x.priority)

    def _end_show(self, show, reset=None):
        # Internal method which ends a running Show

        self.running_shows = [x for x in self.running_shows if x != show]

        if not show.hold:
            self.restore_lower_lights(show=show)

        if reset is None:
            this_reset = show.reset
        else:
            this_reset = reset

        if this_reset:
            show.current_step = 0

        show.running = False

        # if this show was from a script, remove it from running_show_keys

        keys_to_remove = [key for key, value in self.running_show_keys.items()
                          if value == show]

        for key in keys_to_remove:
            del self.running_show_keys[key]

        if show.callback:
            show.callback()

    def get_next_show_step(self):
        next_show_step_time = False
        for show in self.running_shows:
            if not next_show_step_time or show.next_step_time < \
                    next_show_step_time:
                next_show_step_time = show.next_step_time

        return next_show_step_time

    def restore_lower_lights(self, show=None, priority=0):
        """Restores the lights and LEDs from lower priority shows under this
        show.

        This is only useful if this show is stopped, because otherwise this
        show
        will just immediately override these restored settings.

        Args:
            show: The show which will set the priority of the lights you
            want to
                restore.
            priority: An integer value of the lights you want to restore.

        In both cases it will only restore lights below the priority you pass,
        skipping ones that are at the same value.
        """

        # set the priority we're working with.
        if show:
            priority = show.priority

        # first force the restore of whatever the lights were manually set to

        for light in show.light_states:

            if light.debug:
                light.log.debug(
                    "Found this light in a restore_lower_lights meth "
                    "in show.light_states. Light cache priority: %s,"
                    "ending show priority: %s", light.cache['priority'],
                    priority)

            if light.cache['priority'] <= priority:
                light.restore()

        for led in show.led_states:

            if led.debug:
                led.log.debug("Found this LED in a restore_lower_lights meth "
                              "in show.led_states. LED cache priority: %s,"
                              "ending show priority: %s",
                              led.cache['priority'],
                              priority)

            if led.cache['priority'] <= priority:
                led.restore()

        # now see if there are other shows that have these lights in an active
        # state
        for other_show in self.running_shows:
            if other_show.priority < priority:
                other_show.resync()

                # todo the above code could be better. It could only order
                # the restores
                # for the lights and leds that were in this show that just
                # ended?

    def register_tick_handler(self, handler):
        self.registered_tick_handlers.add(handler)

    def deregister_tick_handler(self, handler):
        if handler in self.registered_tick_handlers:
            self.registered_tick_handlers.remove(handler)

    def _tick(self, dt):
        # Runs once per machine loop.  Calls the tick processing function
        # for any running shows
        # and processes any device updates and/or show actions that are needed.
        self.current_tick_time = self.machine.clock.get_time()

        # Process the running Shows
        for show in self.running_shows:
            show.tick(self.current_tick_time)

        for handler in self.registered_tick_handlers:
            handler()

            # Check to see if we need to service any items from our queue.
            # This can
            # be single commands or playlists
            # TODO: Implement playlist processing

            # Make a copy of the queue since we might delete items as we
            # iterate
            # through it
            # queue_copy = list(self.queue)

            # for item in queue_copy:
            #    if item['action_time'] <= self.current_time:
            #        if item.get('playlist', None):
            #            item['playlist'].advance()

            # We have to check again since one of these advances could have
            # removed it already
        #        if item in self.queue:
        #            self.queue.remove(item)

        # Process any device changes or actions made by the running shows
        self._do_update()

    def add_to_light_update_list(self, light, brightness, fade_ms, priority,
                                 blend):
        # Adds an update to our update list, with intelligence that if the list
        # already contains an update for this lightname at the same or lower
        # priority, it deletes that one since there's not sense sending a light
        # command that will be immediately overridden by a higher one.
        for item in self.light_update_list:
            if item['light'] == light and item['priority'] <= priority:
                self.light_update_list.remove(item)
        self.light_update_list.append({'light': light,
                                       'brightness': brightness,
                                       'fade_ms': fade_ms,
                                       'priority': priority,
                                       'blend': blend})  # remove blend?

    def add_to_led_update_list(self, led, color, fade_ms, priority, blend):
        # See comment from above method
        for item in self.led_update_list:
            if item['led'] == led and item['priority'] <= priority:
                self.led_update_list.remove(item)
        self.led_update_list.append({'led': led,
                                     'color': color,
                                     'fade_ms': fade_ms,
                                     'priority': priority,
                                     'blend': blend})

    def add_to_event_queue(self, event):
        # Since events don't blend, this is easy
        self.event_queue.add(event)

    def add_to_coil_queue(self, coil, action=('pulse', 1.0)):
        # action is a tuple
        # action[0] is string of instruction (pulse, pwm, etc.)
        # action[1] is details for that instruction:
        # for pulse, it's a power multiplier
        self.coil_queue.add((coil, action))

    def add_to_gi_queue(self, gi, value):
        self.gi_queue.add((gi, value))

    def add_to_flasher_queue(self, flasher):
        self.flasher_queue.add(flasher)

    def add_to_trigger_queue(self, trigger):
        self.trigger_queue.append(trigger)

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
        if self.trigger_queue:
            self._fire_triggers()

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

    def _fire_triggers(self):
        for trigger in self.trigger_queue:
            self.machine.bcp.bcp_trigger(trigger[0], **trigger[1])
        self.trigger_queue = []

    def _update_lights(self):
        # Updates all the lights in the machine with whatever's in
        # self.light_update_list. Updates with priority, so if the light is
        # doing something at a higher priority, it won't have an effect

        for item in self.light_update_list:
            item['light'].on(brightness=item['brightness'],
                             fade_ms=item['fade_ms'],
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
                    item['led'].log.debug(
                        "Applying update to LED from the Show "
                        "Controller")

                item['led'].color(color=item['color'],
                                  fade_ms=item['fade_ms'],
                                  priority=item['priority'],
                                  blend=item['blend'],
                                  cache=False)

            elif item['led'].debug:
                item['led'].log.debug("Show Controller has an update for this "
                                      "LED, but the update is priority %s "
                                      "while "
                                      "the current priority of the LED is %s. "
                                      "The update will not be applied.",
                                      item['priority'],
                                      item['led'].state['priority'])

        self.led_update_list = []


    def add_external_show_start_command_to_queue(self, name, priority=0,
                                                 blend=True, leds=None,
                                                 lights=None, flashers=None,
                                                 gis=None, coils=None):
        """Called by BCP worker thread when an external show start command
        is received
        via BCP.  Adds the command to a thread-safe queue where it will be
        processed
        by the main thread.

        Args:
            name: The name of the external show, used as a key for
            subsequent show commands.
            priority: Integer value of the relative priority of this show.
            blend: When an light is off in this show, should it allow lower
                priority lights to show through?
            leds: A list of led device names that will be used in this show.
            lights: A list of light device names that will be used in this
            show.
            flashers: A list of flasher device names that will be used in
            this show.
            gis: A list of GI device names that will be used in this show.
            coils: A list of coil device names that will be used in this show.
        """
        if not self.external_show_connected:
            self.register_tick_handler(
                self._update_external_shows)
            self.external_show_connected = True

        self.external_show_command_queue.put(
            (self._process_external_show_start_command,
             (name, priority, blend, leds,
              lights, flashers, gis, coils)))

    def add_external_show_stop_command_to_queue(self, name):
        """Called by BCP worker thread when an external show stop command is
        received
        via BCP.  Adds the command to a thread-safe queue where it will be
        processed
        by the main thread.

        Args:
            name: The name of the external show.
        """
        self.external_show_command_queue.put(
            (self._process_external_show_stop_command, (name,)))

    def add_external_show_frame_command_to_queue(self, name, led_data=None,
                                                 light_data=None,
                                                 flasher_data=None,
                                                 gi_data=None,
                                                 coil_data=None, events=None):
        """Called by BCP worker thread when an external show frame command
        is received
        via BCP.  Adds the command to a thread-safe queue where it will be
        processed
        by the main thread.

        Args:
            name: The name of the external show.
            led_data: A string of concatenated hex color values for the leds
            in the show.
            light_data: A string of concatenated hex brightness values for
            the lights in the show.
            flasher_data: A string of concatenated pulse time (ms) values
            for the flashers in the show.
            gi_data: A string of concatenated hex brightness values for the
            GI in the show.
            coil_data: A string of concatenated coil values
            events: A comma-separated list of events to fire
        """
        self.external_show_command_queue.put(
            (self._process_external_show_frame_command,
             (name, led_data, light_data,
              flasher_data, gi_data, coil_data, events)))

    def _update_external_shows(self):
        """Processes any pending BCP external show commands.  This function
        is called
        in the main processing thread and is a tick handler function.
        """
        while not self.external_show_command_queue.empty():
            update_method, args = self.external_show_command_queue.get(False)
            update_method(*args)

    def _process_external_show_start_command(self, name, priority, blend, leds,
                                             lights, flashers, gis, coils):
        """Processes an external show start command.  Runs in the main
        processing thread.

        Args:
            name: The name of the external show, used as a key for
            subsequent show commands.
            priority: Integer value of the relative priority of this show.
            blend: When an light is off in this show, should it allow lower
                priority lights to show through?
            leds: A list of led device names that will be used in this show.
            lights: A list of light device names that will be used in this
            show.
            flashers: A list of flasher device names that will be used in
            this show.
            gis: A list of GI device names that will be used in this show.
        """
        if name not in self.running_external_show_keys:
            self.running_external_show_keys[name] = ExternalShow(self.machine,
                                                                 name,
                                                                 priority,
                                                                 blend, leds,
                                                                 lights,
                                                                 flashers, gis,
                                                                 coils)

    def _process_external_show_stop_command(self, name):
        """Processes an external show stop command.  Runs in the main
        processing thread.

        Args:
            name: The name of the external show.
        """
        try:
            self.running_external_show_keys[name].stop()
            del self.running_external_show_keys[name]
        except KeyError:
            pass

            # TODO: Would like to de-register the tick handler for external
            # shows here
            # However, since this function is called from the tick handler
            # while
            # iterating over the set of handlers, the list cannot be
            # modified at
            # this point in time.  Since this function is so quick,
            # it's probably
            # okay to leave it for now rather than figure out a complicated
            # way to
            # remove it.

    def _process_external_show_frame_command(self, name, led_data, light_data,
                                             flasher_data, gi_data, coil_data,
                                             events):
        """Processes an external show frame command.  Runs in the main
        processing thread.

        Args:
            name: The name of the external show.
            led_data: A string of concatenated hex color values for the leds
            in the show.
            light_data: A string of concatenated hex brightness values for
            the lights in the show.
            flasher_data: A string of concatenated pulse time (ms) values
            for the flashers in the show.
            gi_data: A string of concatenated hex brightness values for the
            GI in the show.
            coil_data: A string of concatenated coil values ????
            events: A comma-separated list of event names to fire immediately.
        """
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

        if coil_data:
            self.running_external_show_keys[name].update_coils(coil_data)

        if events:
            for event in events.split(","):
                self.machine.show_controller._add_to_event_queue(event)


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
        self.my_playlist.add_show(step_num=1, show=self.show1,
        tocks_per_sec=10)
        self.my_playlist.add_show(step_num=2, show=self.show2, tocks_per_sec=5)
        self.my_playlist.add_show(step_num=3, show=self.show3,
        tocks_per_sec=32)
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
        # loops
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

    def add_show(self, step_num, show, loops=0, tocks_per_sec=32,
                 blend=False, repeat=True):
        """Adds a Show to this playlist. You have to add at least one show
        before you start playing the playlist.

        Args:

            step_num: Interger of which step number you're adding this show to.
                You have to specify this since it's possible to add multiple
                shows to the same step (in cases where you want them both to
                play at the same time during that step). If you want the same
                show to play in multiple steps, then add it multiple times (
                once
                to each step). The show plays starting with the lowest number
                step and then moving on. Ideally they'd be 1, 2, 3... but it
                doesn't matter. If you have step numbers of 1, 2, 5... then the
                player will figure it out.
            show: The Show object that you're adding to this step.
            loops: Integer of how many times you want this show to repeat
                within this step. Note this does not affect when the playlist
                advances to the next step. (That is controlled via
                :meth:`step_settings`.) Rather, this is just how many loops
                this
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
                                  'loops': loops,
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
            one of the Shows in this step is done playing, pass that show's
            object
            here. This is required because if there are multiple
            Shows in this step of the playlist which all end at different
            times, we wouldn't know which one to watch in order to know when to
            move on.

        Note that you can have repeats with a trigger show, but in that case
        you also need to have the loops specified. Otherwise if you have
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
            repeat before it stops itself. (Must be used with *repeat=True*
            above.)
            A value of 0 here means that this playlist repeats forever until
            you
            manually stop it. (This is ideal for attract mode.)
        reset: Boolean which controls whether you want this playlist to
            start at the begining (True) or you want it to pick up where it
            left
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
            if action['step_num'] == self.steps[
                        self.current_step_position - 1]:
                # we have to use the "-1" above because the playlist current
                # position represents the *next* step of shows to play. So when
                # we stop the current show, we have to come back one.
                action['show'].stop(hold=hold)

        for item in self.machine.show_controller.queue:
            if item['playlist'] == self:
                self.machine.show_controller.queue.remove(item)
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

        prev_step = self.steps[self.current_step_position - 1]

        # Stop the previous step's shows
        # Don't do anything if this playlist hasn't started yet
        if not self.starting:
            for action in self.step_actions:
                if action['step_num'] == prev_step:
                    # We have to make sure the show is running before we try to
                    # stop it, because if this show was a trigger show then it
                    # stopped itself already
                    if action['show'] in (
                            self.machine.show_controller.running_shows):
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
                loops = action['loops']
                tocks_per_sec = action['tocks_per_sec']
                blend = action['blend']
                repeat = action['repeat']

                if show == step_trigger_show:
                    # This show finishing will be used to trigger the
                    # advancement to the next step.
                    callback = self._advance

                    if loops == 0:
                        self.log.warning("Found a trigger show that was set to"
                                         " repeat indefinitely. Changing "
                                         "repeat"
                                         " to 1.")
                        loops = 1

                else:
                    callback = None

                show.play(repeat=repeat, priority=self.priority, blend=blend,
                          tocks_per_sec=tocks_per_sec, loops=loops,
                          callback=callback,
                          hold=self.step_settings_dic[current_step_value][
                              'hold'])

        # if we don't have a trigger_show but we have a time value for this
        # step, set up the time to move on
        if step_time and not step_trigger_show:
            self.machine.show_controller.queue.append({'playlist': self,
                                                       'action_time': (
                                                       self.machine.show_controller.current_time + step_time)})

        # Advance our current_step_position counter
        if self.current_step_position == len(self.steps) - 1:
            # We're at the end of our playlist. So now what?
            self.current_step_position = 0

            # Are we repeating?
            if self.repeat:
                # Are we repeating forever, or x number of times?
                if self.repeat_count:  # we're repeating x number of times
                    if self.current_repeat_loop < self.repeat_count - 1:
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
                 lights=None, flashers=None, gis=None, coils=None):

        self.machine = machine
        self.name = name
        self.priority = priority
        self.blend = blend
        self.name = None
        self.leds = list()
        self.lights = list()
        self.flashers = list()
        self.gis = list()
        self.coils = list()

        if leds:
            self.leds = [self.machine.leds[x] for x in
                         Util.string_to_list(leds)]

        if lights:
            self.lights = [self.machine.lights[x] for x in
                           Util.string_to_list(lights)]

        if flashers:
            self.flashers = [self.machine.flashers[x] for x in
                             Util.string_to_list(flashers)]

        if gis:
            self.gis = [self.machine.gis[x] for x in Util.string_to_list(gis)]

        if coils:
            self.coils = [self.machine.coils[x] for x in
                          Util.string_to_list(coils)]

    def update_leds(self, data):
        for led, color in zip(self.leds, Util.chunker(data, 6)):
            self.machine.show_controller.add_to_led_update_list(
                led, RGBColor(RGBColor.hex_to_rgb(color)), 0, self.priority,
                self.blend)

    def update_lights(self, data):
        for light, brightness in zip(self.lights, Util.chunker(data, 2)):
            self.machine.show_controller._add_to_light_update_list(
                light, Util.hex_string_to_int(brightness), self.priority,
                self.blend)

    def update_gis(self, data):
        for gi, brightness in zip(self.lights, Util.chunker(data, 2)):
            self.machine.show_controller._add_to_gi_queue(
                gi, Util.hex_string_to_int(brightness))

    def update_flashers(self, data):
        for flasher, flash in zip(self.flashers, data):
            if flash:
                self.machine.show_controller._add_to_flasher_queue(flasher)

    def update_coils(self, data):
        for coil, pulse in zip(self.coils, data):
            if pulse:
                self.machine.show_controller._add_to_coil_queue(coil)

    def stop(self):
        for led in self.leds:
            if led.cache['priority'] <= self.priority:
                led.restore()

        for light in self.lights:
            if light.cache['priority'] <= self.priority:
                light.restore()
