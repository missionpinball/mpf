import re
from copy import deepcopy, copy

from mpf.core.assets import Asset, AssetPool
from mpf.core.config_player import ConfigPlayer
from mpf.core.file_manager import FileManager
from mpf.core.utility_functions import Util


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
    disk_asset_section = 'file_shows'
    extensions = 'yaml'
    class_priority = 100
    pool_config_section = 'show_pools'
    asset_group_class = ShowPool

    def __init__(self, machine, name, file=None, config=None, data=None):
        super().__init__(machine, name, file, config)

        self._initialize_asset()

        self.tokens = set()
        self.token_values = dict()
        self.token_keys = dict()

        self.token_finder = re.compile('(?<=\()(.*?)(?=\))')

        self.running = set()
        self.name = name

        if data:
            self.do_load_show(data=data)

    def __lt__(self, other):
        return id(self) < id(other)

    def _initialize_asset(self):
        self._autoplay_settings = dict()
        self.loaded = False
        self.notify_when_loaded = set()
        self.loaded_callbacks = list()
        self.show_steps = list()
        self.mode = None

    def do_load(self):
        self.do_load_show(None)

    def do_load_show(self, data):
        self.show_steps = list()

        self.machine.show_controller.log.debug("Loading Show %s",
                                               self.file)
        if not data and self.file:
            data = self.load_show_from_disk()

        if isinstance(data, dict):
            data = list(data)
        elif not isinstance(data, list):
            raise ValueError("Show %s does not appear to be a valid show "
                             "config", self.file)

        # Loop over all steps in the show file
        total_step_time = 0
        for step_num in range(len(data)):
            actions = dict()

            # Note: all times are stored/calculated in seconds.

            # Step time can be specified as either an absolute time elapsed
            # (from the beginning of the show) or a relative time (time elapsed
            # since the previous step).  Time strings starting with a plus sign
            # (+) are treated as relative times.

            # Step times are all converted to relative times internally (time
            # since the previous step).

            # Make sure there is a time entry for each step in the show file.
            if 'time' not in data[step_num]:
                raise ValueError("Show '%s' is missing a 'time:' value in step"
                                 " %s. " % (self.name, step_num))

            step_time = Util.string_to_secs(data[step_num]['time'])

            # If the first step in the show is not at the very beginning of the
            # show (time = 0), automatically add a new empty step at time 0
            if step_num == 0 and step_time > 0:
                self.show_steps.append({'time': 0})

            # Calculate step time based on whether the step uses absolute or
            # relative time
            if str(data[step_num]['time'])[0] == '+':
                # Step time relative to previous step time
                actions['time'] = step_time
            else:
                # Step time relative to start of show

                # Make sure this step time comes after the previous step time
                # todo automatically fix this programmatically
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
            for key, value in data[step_num].items():

                # key: the section of the show, like 'leds'
                # value: dic of express settings or dic of dics w full settings

                # check to see if we know how to process this kind of entry
                if key in ConfigPlayer.show_players.keys():
                        validated_config = dict()

                        # we're now at a dict for this section in the show
                        # key
                        if not isinstance(value, dict):
                            value = {value: dict()}

                        for device, settings in value.items():
                            validated_config.update(
                                ConfigPlayer.show_players[key].validate_show_config(
                                    device, settings))

                        actions[key] = validated_config

                elif key != 'time':
                    actions[key] = data[step_num][key]

            self.show_steps.append(actions)

        # Count how many total steps are in the show. We need this later
        # so we can know when we're at the end of a show
        self.total_steps = len(self.show_steps)

        self._get_tokens()

    def _do_unload(self):
        self.show_steps = None

    def _get_tokens(self):
        self._walk_show(self.show_steps)

    def _walk_show(self, data, path=None, list_index=None):
        # walks a list of dicts, checking tokens
        if not path:
            path = list()

        if type(data) is dict:
            for k, v in data.items():
                self._check_token(path, k, 'key')
                self._walk_show(v, path + [k])

        elif type(data) is list:
            for i in data:
                self._check_token(path, i, 'key')
                if list_index is None:
                    list_index = 0
                else:
                    list_index += 1
                self._walk_show(i, path + [list_index], list_index)

        else:
            self._check_token(path, data, 'value')

    def get_show_steps(self, data='dummy_default!#$'):

        if data == 'dummy_default!#$':
            data = self.show_steps

        if type(data) is dict:
            new_dict = dict()
            for k, v in data.items():
                new_dict[k] = self.get_show_steps(v)
            return new_dict
        elif type(data) is list:
            new_list = list()
            for i in data:
                new_list.append(self.get_show_steps(i))
            return new_list
        else:
            return data

    def _check_token(self, path, data, token_type):
        try:
            token = self.token_finder.findall(data)
        except TypeError:
            return

        if token:
            self._add_token(token[0], path, token_type)

    def _add_token(self, token, path, token_type):

        if token not in self.tokens:
            self.tokens.add(token)

        if token_type == 'key':
            if token not in self.token_keys:
                self.token_keys[token] = list()
            self.token_keys[token].append(path)

        elif token_type == 'value':
            if token not in self.token_values:
                self.token_values[token] = list()
            self.token_values[token].append(path)

    def _replace_tokens(self, **kwargs):
        keys_replaced = dict()
        show = deepcopy(self.show_steps)

        for token, replacement in kwargs.items():
            if token in self.token_values:
                for token_path in self.token_values[token]:
                    target = show
                    for x in token_path[:-1]:
                        target = target[x]

                    target[token_path[-1]] = replacement

        for token, replacement in kwargs.items():
            if token in self.token_keys:
                key_name = '({})'.format(token)
                for token_path in self.token_keys[token]:
                    target = show
                    for x in token_path:
                        if x in keys_replaced:
                            x = keys_replaced[x]

                        target = target[x]

                    target[replacement] = target.pop(key_name)
                    keys_replaced[key_name] = replacement

        return show

    def play(self, priority=0, blend=False, hold=None,
             speed=1.0, start_step=0, callback=None,
             loops=-1, sync_ms=0, reset=True, mode=None,
             manual_advance=False, **kwargs):
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
            speed: Float of how fast your show runs. Your Show files
                specify step times in actual time values.  When you play a
                show,
                you specify a playback rate factor that is applied to the time
                values in the show (divides the relative show times). The
                default value is 1.0 (uses the actual time values in specified
                in the show), but you might want to speed up (speed
                values > 1.0) or slow down (speed values < 1.0) the
                playback rate.  If you want your show to play twice as fast
                (finish in half the time), you want all your time values to be
                half of the specified values in the show so you would use a
                speed value of 2.0.  To make the show take twice as
                long
                to finish, you would a speed value of 0.5.
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
        self.name = '{}.{}'.format(self.name, self.get_id())

        if not self.loaded:
            self._autoplay_settings = dict(
                    priority=priority,
                    blend=blend,
                    hold=hold,
                    speed=speed,
                    start_step=start_step,
                    callback=callback,
                    loops=loops,
                    sync_ms=sync_ms,
                    reset=reset,
                    mode=mode,
                    manual_advance=manual_advance,
                    **kwargs
                   )

            self.load(callback=self._autoplay, priority=priority)
            return False

        if hold is not None:
            hold = hold
        elif self.total_steps == 1:
            hold = True

        if self.total_steps > 1:
            loops = loops
        else:
            loops = 0

        this_show = (RunningShow(machine=self.machine,
                                 show=self,
                                 show_steps=self.get_show_steps(),
                                 priority=int(priority),
                                 blend=bool(blend),
                                 hold=bool(hold),
                                 speed=float(speed),
                                 start_step=int(start_step),
                                 callback=callback,
                                 loops=int(loops),
                                 sync_ms=int(sync_ms),
                                 reset=bool(reset),
                                 mode=mode,
                                 manual_advance=manual_advance,
                                 **kwargs)
                                 )

        self.machine.show_controller.notify_show_starting(this_show)

        return this_show

    def _autoplay(self, *args, **kwargs):
        del args
        del kwargs
        self.play(**self._autoplay_settings)

    def load_show_from_disk(self):
        return FileManager.load(self.file)


class RunningShow(object):
    def __init__(self, machine, show, show_steps, priority, blend,
                 hold, speed, start_step, callback, loops,
                 sync_ms, reset, mode, manual_advance, **kwargs):

        self.machine = machine
        self.show = show
        self.show_steps = show_steps
        self.priority = priority
        self.blend = blend
        self.hold = hold
        self.speed = speed
        self.current_step = start_step
        self.callback = callback
        self.loops = loops
        self.reset = reset
        self.mode = mode
        self.manual_advance = manual_advance
        self.tokens = kwargs
        self.debug = False

        self.name = show.name
        self._total_steps = len(show_steps)

        show.running.add(self)

        # Figure out the show start time
        self.next_step_time = self.machine.clock.get_time()
        self._run_current_step()

        if sync_ms:
            self.next_step_time += show.sync_ms / 1000.0
            self.machine.clock.schedule_once(self._run_current_step,
                                             show.sync_ms / 1000.0)
        else:  # run now
            self._run_current_step()

    def __repr__(self):
        return "Running Show Instance: {}".format(self.name)

    def stop(self):
        self.machine.show_controller.notify_show_stopping(self)
        self.show.running.remove(self)
        self.machine.clock.unschedule(self._run_current_step, True)

        if not self.hold:
            for player in ConfigPlayer.show_players.values():
                player.clear(caller=self, priority=self.priority)

        if self.callback and callable(self.callback):
            self.callback()

    def _run_current_step(self, dt=None):
        del dt

        # todo dunno why we have to do this. It's needed with unit tests
        if self.machine.clock.get_time() < self.next_step_time:
            return

        for item_type, item_dict in (
                iter(self.show_steps[self.current_step].items())):

            if item_type == 'time':
                continue

            elif item_type in ConfigPlayer.show_players:
                if item_type in item_dict:
                    item_dict = item_dict[item_type]

                ConfigPlayer.show_players[item_type].play(settings=item_dict,
                                                          mode=self.mode,
                                                          caller=self,
                                                          priority=self.priority)

        # if we're at the end of the show
        if self.current_step == self._total_steps - 1:

            if self.loops > 0:
                self.loops -= 1
            elif self.loops < 0:
                self.current_step = 0
            else:
                self.stop()
                return False

        else:  # we're in the middle of a show
            self.current_step += 1

        if not self.manual_advance:
            time_to_next_step = (
                self.show_steps[self.current_step]['time'] * self.speed)
            self.next_step_time = (
                self.machine.clock.get_time() + time_to_next_step)

            self.machine.clock.schedule_once(self._run_current_step,
                                             time_to_next_step)

            return time_to_next_step

    def advance(self, steps=1, show_step=None):
        """Manually advances this show to the next step."""

        steps_to_advance = steps - 1  # since current_step is really next step

        # todo should this end the show if there are more steps than in the
        # show and it's not set to loop?

        if steps_to_advance:
            self.current_step = self._total_steps % steps_to_advance
        elif show_step is not None:
            self.current_step = show_step - 1

        self._run_current_step()
        return self.current_step - 1  # current step is actually the next step
