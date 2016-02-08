from mpf.core.assets import Asset, AssetPool
from mpf.core.file_manager import FileManager
from mpf.core.utility_functions import Util
from mpf.core.rgb_color import RGBColor

class ShowPool(AssetPool):
    def __repr__(self):
        return '<ShowPool: {}>'.format(self.name)

    @property
    def show(self):
        return self.asset


class Show(Asset):
    attribute = 'shows'
    path_string = 'shows'
    config_section = 'shows'
    extensions = ('yaml')
    class_priority = 100
    pool_config_section = 'show_pools'
    asset_group_class = ShowPool

    def __init__(self, machine, name, file, config=None, steps=None):
        super().__init__(machine, name, file, config)

        self._playback_rate = 1.0
        self.current_tick_time = 0
        self.running = False
        self._initialize_asset()

        if steps:
            self._do_load(steps=steps)

    def __lt__(self, other):
        return id(self) < id(other)

    @property
    def playback_rate(self):
        return self._playback_rate

    @playback_rate.setter
    def playback_rate(self, value):
        """Changes the current playback speed of a running Show.

        Args:
            value: The new playback speed value.

        Note that you can't just update the show's _playback_rate directly
        because some other important calculations that must be made to adjust
        a show that is currently running.
        """
        self._playback_rate = value
        if not self.running:
            return

    def _initialize_asset(self):
        self.loops = -1  # How many times the show will loop before it ends
        # (-1 means indefinitely)
        self.current_loop_number = 0  # tracks which repeat we're on,
        # used with loops above
        self.hold = False  # hold the item states when the show ends.
        self.reset = True  # reset back to the first step when the show ends
        self.priority = 0  # relative priority of this show
        self.ending = False  # show will end after the current tock ends
        self.blend = False  # when an light is off in this show, should it
        # allow
        # lower priority lights to show through?
        self.debug = False
        self.current_step = 0  # index of which step a running show is
        self.total_steps = 0  # total number of steps in the show
        self.current_time = 0  # index of which tock a running show is in
        self.loop_start_time = 0  # Real-world time at which the current
        # loop of this show started
        self.next_step_time = 0  # Real-world time when the next show step
        # occurs
        self.callback = None  # if the show should call something when it ends
        # naturally. (Not invoked if show is manually stopped)
        self.sync_ms = 0
        self._autoplay_settings = dict()
        self.light_states = dict()
        self.led_states = dict()
        self.stop_key = None

        self.loaded = False
        self.notify_when_loaded = set()
        self.loaded_callbacks = list()
        self.show_steps = list()

    def _do_load(self, steps=None):
        self.show_steps = []

        self.machine.show_controller.log.debug("Loading Show %s",
                                               self.file)
        if not steps and self.file:
            steps = self.load_show_from_disk()

        if type(steps) is not list:
            self.machine.show_controller.log.warning(
                "%s is not a valid YAML file. "
                "Skipping show.", self.file)
            return False

        # Loop over all steps in the show file
        total_step_time = 0
        for step_num in range(len(steps)):
            actions = {}

            # Note: all times are stored/calculated in seconds.

            # Step time can be specified as either an absolute time elapsed
            # (from the beginning of the show) or a relative time (time elapsed
            # since the previous step).  Time strings starting with a plus sign
            # (+) are treated as relative times.

            # Step times are all converted to relative times internally (time
            # since the previous step).

            # Make sure there is a time entry for each step in the show file.
            if 'time' not in steps[step_num]:
                self.machine.show_controller.log.warning(
                    "%s is not a valid show file. "
                    "Skipping show.", self.file)
                return False

            step_time = Util.string_to_secs(steps[step_num]['time'])

            # If the first step in the show is not at the very beginning of the
            # show (time = 0), automatically add a new empty step at time 0
            if step_num == 0 and step_time > 0:
                self.show_steps.append({'time': 0})

            # Calculate step time based on whether the step uses absolute or
            #  relative time
            if str(steps[step_num]['time'])[0] == '+':
                # Step time relative to previous step time
                actions['time'] = step_time
            else:
                # Step time relative to start of show

                # Make sure this step time comes after the previous step time
                if step_time < total_step_time:
                    self.machine.show_controller.log.warning(
                        "%s is not a valid show file. Step times are not "
                        "valid "
                        "as they are not all in chronological order. "
                        "Skipping show.",
                        self.file)
                    return False

                # Calculate the time since previous step
                actions['time'] = step_time - total_step_time

            total_step_time += actions['time']

            # Now process show step actions

            # Lights
            if 'lights' in steps[step_num] and steps[step_num]['lights']:

                light_actions = dict()

                for light in steps[step_num]['lights']:

                    if 'tag|' in light:
                        tag = light.split('tag|')[1]
                        light_list = self.machine.lights.items_tagged(tag)
                    else:  # create a single item list of the light object
                        try:
                            light_list = [self.machine.lights[light]]
                        except KeyError:
                            self.machine.show_controller.log.warning(
                                "Found invalid "
                                "light name '%s' in show. Skipping...",
                                light)
                            continue

                    # convert / ensure lights are single ints
                    value = str(steps[step_num]['lights'][light])
                    fade = 0

                    if '-f' in value:
                        composite_value = value.split('-f')
                        value = composite_value[0]
                        fade = Util.string_to_ms(composite_value[1])

                    brightness = max(min(Util.hex_string_to_int(value), 255),
                                     0)

                    for light_ in light_list:
                        light_actions[light_] = {'brightness': brightness,
                                                 'fade': fade}

                        # make sure this light is in self.light_states
                        if light_ not in self.light_states:
                            self.light_states[light_] = {
                                'current_brightness': 0,
                                'destination_brightness': 0,
                                'start_brightness': 0,
                                'fade_start': 0,
                                'fade_end': 0}

                actions['lights'] = light_actions

            # Events
            # make sure events is a list of strings
            if 'events' in steps[step_num] and steps[step_num]['events']:
                event_list = (Util.string_to_list(steps[step_num]['events']))
                actions['events'] = event_list

            # Coils
            if 'coils' in steps[step_num] and steps[step_num]['coils']:

                coil_actions = dict()

                for coil in steps[step_num]['coils']:

                    try:
                        this_coil = self.machine.coils[coil]
                    except:
                        # this coil name is invalid
                        self.machine.show_controller.log.warning(
                            "WARNING: Found invalid "
                            "coil name '%s' in show. Skipping...",
                            coil)
                        continue

                    # Check if a power setting has been specified
                    if isinstance(steps[step_num]['coils'][coil],
                                  dict) and 'power' in \
                            steps[step_num]['coils'][coil]:
                        power = max(
                            min(int(steps[step_num]['coils'][coil]['power']),
                                100), 0)
                    else:
                        power = 100

                    # convert the 0-100 value to 0.0-1.0 float
                    power /= 100.0

                    # convert value list into tuple
                    coil_actions[this_coil] = ('pulse', power)

                actions['coils'] = coil_actions

            # Flashers
            if 'flashers' in steps[step_num] and steps[step_num]['flashers']:

                flasher_set = set()

                for flasher in Util.string_to_list(
                        steps[step_num]['flashers']):

                    if 'tag|' in flasher:
                        tag = flasher.split('tag|')[1]
                        flasher_list = self.machine.flashers.items_tagged(tag)
                    else:  # create a single item list of the flasher objects
                        try:
                            flasher_list = [self.machine.flashers[flasher]]
                        except KeyError:
                            self.machine.show_controller.log.warning(
                                "Found invalid "
                                "flasher name '%s' in show. Skipping...",
                                flasher)
                            continue

                    for flasher_ in flasher_list:
                        flasher_set.add(flasher_)

                actions['flashers'] = flasher_set

            # GI
            if 'gis' in steps[step_num] and steps[step_num]['gis']:

                gi_actions = dict()

                for gi in steps[step_num]['gis']:

                    if 'tag|' in gi:
                        tag = gi.split('tag|')[1]
                        gi_list = self.machine.gi.items_tagged(tag)
                    else:  # create a single item list of the light object
                        try:
                            gi_list = [self.machine.gi[gi]]
                        except KeyError:
                            self.machine.show_controller.log.warning(
                                "Found invalid "
                                "GI name '%s' in show. Skipping...",
                                gi)
                            continue

                    value = str(steps[step_num]['gis'][gi])

                    # convert / ensure flashers are single ints between 0
                    # and 255
                    value = max(min(Util.hex_string_to_int(value), 255), 0)

                    for gi_ in gi_list:
                        gi_actions[gi_] = value

                actions['gis'] = gi_actions

            # LEDs
            if 'leds' in steps[step_num] and steps[step_num]['leds']:

                led_actions = {}

                for led in steps[step_num]['leds']:

                    if 'tag|' in led:
                        tag = led.split('tag|')[1]
                        led_list = self.machine.leds.items_tagged(tag)
                    else:  # create a single item list of the led object
                        try:
                            led_list = [self.machine.leds[led]]
                        except KeyError:
                            self.machine.show_controller.log.warning(
                                "Found invalid "
                                "LED name '%s' in show. Skipping...",
                                led)
                            continue

                    value = str(steps[step_num]['leds'][led])
                    fade = 0

                    if '-f' in value:
                        composite_value = value.split('-f')
                        value = composite_value[0]
                        fade = Util.string_to_ms(composite_value[1])

                    # convert our color of hexes to a list of ints
                    destination_color = RGBColor(RGBColor.string_to_rgb(value))

                    for led_ in led_list:
                        led_actions[led_] = {'color': destination_color,
                                             'fade': fade}

                        # make sure this led is in self.led_states
                        if led_ not in self.led_states:
                            self.led_states[led_] = {
                                'current_color': RGBColor(),
                                'destination_color': RGBColor(),
                                'start_color': RGBColor(),
                                'fade_start': 0,
                                'fade_end': 0}

                actions['leds'] = led_actions

            # Triggers
            if 'triggers' in steps[step_num] and steps[step_num]['triggers']:

                triggers = {}

                for name, args in steps[step_num]['triggers'].items():
                    triggers[name] = args

                actions['triggers'] = triggers

            self.show_steps.append(actions)

        # Count how many total steps are in the show. We need this later
        # so we can know when we're at the end of a show
        self.total_steps = len(self.show_steps)

    def _do_unload(self):
        self.show_steps = None

    def play(self, priority=0, blend=False, hold=None,
             playback_rate=1.0, start_step=None, callback=None,
             loops=-1, sync_ms=0, reset=True, **kwargs):
        """Plays a Show. There are many parameters you can use here which
        affect how the show is played. This includes things like the playback
        speed, priority, whether this show blends with others, etc. These are
        all set when the show plays. (For example, you could have a Show
        file which lights a bunch of lights sequentially in a circle pattern,
        but you can have that circle "spin" as fast as you want depending on
        how you play the show.)

        Args:
            priority: Integer value of the relative priority of this show. If
                there's ever a situation where multiple shows want to control
                the same item, the one with the higher priority will win.
                ("Higher" means a bigger number, so a show with priority 2 will
                override a priority 1.)
            blend: Boolean which controls whether this show "blends" with lower
                priority shows and scripts. For example, if this show turns a
                light off, but a lower priority show has that light set to
                blue,
                then the light will "show through" as blue while it's off here.
                If you don't want that behavior, set blend to be False. Then
                off
                here will be off for sure (unless there's a higher priority
                show
                or command that turns the light on). Note that not all item
                types blend. (You can't blend a coil or event, for example.)
            hold: Boolean which controls whether the lights or LEDs remain in
                their final show state when the show ends. Default is None
                which
                means hold will be False if the show has more than one step,
                and
                True if there is only one step.
            playback_rate: Float of how fast your show runs. Your Show files
                specify step times in actual time values.  When you play a
                show,
                you specify a playback rate factor that is applied to the time
                values in the show (divides the relative show times). The
                default value is 1.0 (uses the actual time values in specified
                in the show), but you might want to speed up (playback_rate
                values > 1.0) or slow down (playback_rate values < 1.0) the
                playback rate.  If you want your show to play twice as fast
                (finish in half the time), you want all your time values to be
                half of the specified values in the show so you would use a
                playback_rate value of 2.0.  To make the show take twice as
                long
                to finish, you would a playback_rate value of 0.5.
            start_step: Integer of which position in the show file the show
                should start in. Usually this is 0 (start at the beginning
                of the show) but it's nice to start part way through. Also
                used for restarting shows that you paused. A negative value
                will count backwards from the end (-1 is the last position,
                -2 is second to last, etc.).
            callback: A callback function that is invoked when the show is
                stopped.
            loops: Integer of how many times you want this show to repeat
                before stopping. A value of -1 means that it repeats
                indefinitely.
            sync_ms: Number of ms of the show sync cycle. A value of zero means
                this show will also start playing immediately. See the full MPF
                documentation for details on how this works.
            reset: Boolean which controls whether this show will reset to its
                first position once it ends. Default is True.
            **kwargs: Not used, but included in case this method is used as an
                event handler which might include additional kwargs.
        """

        if not self.loaded:

            self._autoplay_settings = dict(
                                         priority=priority,
                                         blend=blend,
                                         hold=hold,
                                         playback_rate=playback_rate,
                                         start_step=start_step,
                                         callback=callback,
                                         loops=loops,
                                         sync_ms=sync_ms)
            self.load(callback=self._autoplay, priority=priority)
            return False

        if hold is not None:
            self.hold = hold
        elif self.total_steps == 1:
            self.hold = True

        if self.total_steps > 1:
            self.loops = loops
        else:
            self.loops = 0

        self.priority = int(priority)
        self.blend = blend
        self.playback_rate = playback_rate
        self.callback = callback
        self.sync_ms = sync_ms
        self.reset = reset

        if start_step is not None:
            # if you don't specify a start location, it will start where it
            # left off (if you stopped it with reset=False). If the show has
            # never been run, it will start at 0 per the initialization

            if start_step < 0:
                self.current_step = self.total_steps + start_step
            else:
                self.current_step = start_step

        self.machine.show_controller._run_show(self)

    def _autoplay(self, *args, **kwargs):
        self.play(**self._autoplay_settings)

    def load_show_from_disk(self):
        return FileManager.load(self.file)

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

        self.machine.show_controller._end_show(self, reset)

    def tick(self, current_tick_time):

        if not self.show_steps:
            return

        self.current_tick_time = current_tick_time

        # Internal method which advances the show to the next step
        if self.ending:
            self.machine.show_controller._end_show(self)
            return

        action_loop_count = 0  # Tracks how many loops we've done in this call
        # Used to detect if a show is running too slow

        while self.next_step_time and self.next_step_time <= \
                self.current_tick_time:
            action_loop_count += 1
            self._process_current_step()

            # If our Show is running so fast that it has done a complete
            # loop during this tick, then let's just break out of the loop
            if action_loop_count == self.total_steps:
                return

    def _process_current_step(self):

        current_step_time = self.next_step_time

        if self.debug:
            print("Current step: ", self.current_step)
            print("Current tick time: ", self.current_tick_time)
            print("Next step time: ", self.next_step_time)
            print("Current step time: ", current_step_time)
            print("Playback rate: ", self.playback_rate)

        # create a dictionary of the current items of each type, combined with
        # the show details, that we can throw up to our queue

        for item_type, item_dict in (
                iter(self.show_steps[self.current_step].items())):

            if item_type == 'time':
                continue
            elif item_type == 'lights':

                for light_obj, light_dict in item_dict.items():
                    self.machine.show_controller.add_to_light_update_list(
                        light=light_obj,
                        brightness=light_dict['brightness'],
                        fade_ms=int(light_dict['fade'] / self.playback_rate),
                        priority=self.priority,
                        blend=self.blend)

                    prev_brightness = self.light_states[light_obj][
                        'current_brightness']

                    # update the current state
                    self.light_states[light_obj] = {
                        'current_brightness': prev_brightness,
                        'destination_brightness': light_dict['brightness'],
                        'start_brightness': prev_brightness,
                        'fade_start': current_step_time,
                        'fade_end': current_step_time + int(
                            light_dict['fade']) / self.playback_rate / 1000}


            elif item_type == 'leds':

                for led_obj, led_dict in item_dict.items():
                    self.machine.show_controller.add_to_led_update_list(
                        led=led_obj,
                        color=led_dict['color'],
                        fade_ms=int(led_dict['fade'] / self.playback_rate),
                        priority=self.priority,
                        blend=self.blend)

                    # update the current state

                    # grab the old current color
                    prev_color = self.led_states[led_obj]['current_color']

                    self.led_states[led_obj] = {
                        'current_color': prev_color,
                        # todo need to calculate this for a restore
                        'destination_color': led_dict['color'],
                        'start_color': prev_color,
                        'fade_start': current_step_time,
                        'fade_end': current_step_time + int(
                            led_dict['fade']) / self.playback_rate / 1000}

            elif item_type == 'events':

                for event in item_dict:  # item_dict is actually a list here
                    self.machine.show_controller.add_to_event_queue(event)

            elif item_type == 'coils':

                for coil_obj, coil_action in item_dict.items():
                    self.machine.show_controller.add_to_coil_queue(
                        coil=coil_obj,
                        action=coil_action)

            elif item_type == 'gis':
                for gi, value in item_dict.items():
                    self.machine.show_controller.add_to_gi_queue(
                        gi=gi,
                        value=value)

            elif item_type == 'flashers':
                for flasher in item_dict:
                    self.machine.show_controller.add_to_flasher_queue(
                        flasher=flasher)

            elif item_type == 'triggers':
                for trigger_name, trigger_args in item_dict.items():
                    self.machine.show_controller.add_to_trigger_queue(
                        trigger=(trigger_name, trigger_args))

        # increment this show's current_step pointer and handle repeats

        # if we're at the end of the show
        if self.current_step == self.total_steps - 1:

            # if we're repeating with an unlimited number of repeats
            if self.loops == -1:
                self.current_step = 0

            # if we're repeating, but only for a certain number of times
            elif self.loops > 0:
                # if we haven't hit the repeat limit yet
                if self.current_loop_number < self.loops:
                    self.current_step = 0
                    self.current_loop_number += 1
                else:
                    self.ending = True
            else:
                self.ending = True

        # else, we're in the middle of a show
        else:
            self.current_step += 1

        if self.ending:
            self.next_step_time = False
        else:
            # Set the next action time based on upcoming show step
            self.next_step_time = (current_step_time +
                                   self.show_steps[self.current_step][
                                       'time'] / self.playback_rate)

    def resync(self):
        """Causes this show to do a one-time update to resync all the LEDs and
        lights in the show with where they should be now. This is used when a
        higher priority show stops so lower priority shows can put all the
        lights back to how they want them.
        """

        for light_obj, brightness in self.light_states.items():
            self.machine.show_controller.add_to_light_update_list(
                light=light_obj,
                brightness=brightness,
                fade_ms=0,
                priority=self.priority,
                blend=self.blend)

        for led_obj, led_dict in self.led_states.items():
            self.machine.show_controller.add_to_led_update_list(
                led=led_obj,
                color=led_dict['current_color'],
                fade_ms=0,
                priority=self.priority,
                blend=self.blend)
