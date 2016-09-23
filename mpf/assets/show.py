"""Contains show related classes."""
from mpf.core.assets import Asset, AssetPool
from mpf.core.file_manager import FileManager
from mpf.core.utility_functions import Util
from mpf.file_interfaces.yaml_interface import YamlInterface
from mpf._version import __show_version__, __version__


class ShowPool(AssetPool):

    """A pool of shows."""

    def __repr__(self):
        """Return str representation."""
        return '<ShowPool: {}>'.format(self.name)

    @property
    def show(self):
        """Return the next show."""
        # TODO: getters should not modify state #348
        return self.asset


# pylint: disable-msg=too-many-instance-attributes
class Show(Asset):

    """A show which can be instantiated."""

    attribute = 'shows'
    path_string = 'shows'
    config_section = 'shows'
    disk_asset_section = 'file_shows'
    extensions = 'yaml'
    class_priority = 100
    pool_config_section = 'show_pools'
    asset_group_class = ShowPool

    # pylint: disable-msg=too-many-arguments
    def __init__(self, machine, name, file=None, config=None, data=None):
        """Initialise show."""
        super().__init__(machine, name, file, config)

        self._autoplay_settings = dict()

        self._initialize_asset()

        self.tokens = set()
        self.token_values = dict()
        self.token_keys = dict()

        self.running = set()
        '''Set of RunningShow() instances which represents running instances
        of this show.'''
        self.name = name
        self.total_steps = None
        self.show_steps = None

        if data:
            self._do_load_show(data=data)
            self.loaded = True

    def __lt__(self, other):
        """Compare two instances."""
        return id(self) < id(other)

    def _initialize_asset(self):
        self.loaded = False
        self.show_steps = list()
        self.mode = None

    def do_load(self):
        """Load a show from disk."""
        self._do_load_show(None)

    def _get_duration(self, data, step_num, total_step_time):
        total_steps_num = len(data)
        step = data[step_num]
        if 'duration' not in step:
            if step_num == total_steps_num - 1:
                # special case with an empty last step (but longer than 1 step)
                if 'time' in step and len(step) == 1 and step_num != 0:
                    return False
                else:
                    return 1
            elif 'time' in data[step_num + 1]:
                next_step_time = data[step_num + 1]['time']
                if str(next_step_time)[0] == "+":
                    return Util.string_to_secs(next_step_time)
                else:
                    if total_step_time < 0:     # pragma: no cover
                        self._show_validation_error("Absolute timing in step {} not possible because "
                                                    "there was a duration of -1 before".format(step_num))
                    return Util.string_to_secs(next_step_time) - total_step_time
            else:
                return 1
        else:
            if step_num < total_steps_num - 1 and 'time' in data[step_num + 1]:     # pragma: no cover
                self._show_validation_error("Found invalid 'time' entry in step after {} which contains a duration. "
                                            "Remove either of them!".format(step_num))
            return Util.string_to_secs(step['duration'])

    def _do_load_show(self, data):
        # do not use machine or the logger here because it will block
        self.show_steps = list()

        if not data and self.file:
            data = self.load_show_from_disk()

        # Pylint complains about the change from dict to list. This is intended and fine.
        # pylint: disable-msg=redefined-variable-type
        if isinstance(data, dict):
            data = list(data)
        elif not isinstance(data, list):    # pragma: no cover
            raise ValueError("Show {} does not appear to be a valid show "
                             "config".format(self.file))

        if not data:    # pragma: no cover
            self._show_validation_error("Cannot load empty show")

        total_step_time = 0

        # add empty first step if show does not start right away
        if 'time' in data[0] and data[0]['time'] != 0:
            self.show_steps.append({'duration': Util.string_to_secs(data[0]['time'])})
            total_step_time = Util.string_to_secs(data[0]['time'])

        # Loop over all steps in the show file
        for step_num, step in enumerate(data):
            actions = dict()

            # Note: all times are stored/calculated in seconds.

            # Step time can be specified as either an absolute time elapsed
            # (from the beginning of the show) or a relative time (time elapsed
            # since the previous step).  Time strings starting with a plus sign
            # (+) are treated as relative times.

            # Step times are all converted to relative times internally (time
            # since the previous step).

            # Make sure there is a time entry for each step in the show file.
            duration = self._get_duration(data, step_num, total_step_time)

            # special case: empty last step
            if duration is False:
                break
            elif duration == 0:     # pragma: no cover
                self._show_validation_error("Step {} has 0 duration".format(step_num))

            # Calculate the time since previous step
            actions['duration'] = duration

            if duration > 0 and total_step_time >= 0:
                total_step_time += duration
            else:
                total_step_time = -1

            # Now process show step actions
            self._process_step_actions(step, actions)

            self.show_steps.append(actions)

        # Count how many total steps are in the show. We need this later
        # so we can know when we're at the end of a show
        self.total_steps = len(self.show_steps)
        if self.total_steps == 0:   # pragma: no cover
            self._show_validation_error("Show is empty")

        self._get_tokens()

    def _show_validation_error(self, msg):  # pragma: no cover
        if self.file:
            identifier = self.file
        else:
            identifier = self.name

        raise AssertionError("Show {}: {}".format(identifier, msg))

    def _process_step_actions(self, step, actions):
        if not isinstance(step, dict):
            raise AssertionError("Steps in show {} need to be dicts.".format(self.name))
        for key, value in step.items():

            # key: the section of the show, like 'leds'
            # value: dic of express settings or dic of dics w full settings

            # check to see if we know how to process this kind of entry
            if key in self.machine.show_controller.show_players.keys():
                actions[key] = self.machine.show_controller.show_players[key].validate_config_entry(value, self.name)

            elif key != 'duration' and key != 'time':   # pragma: no cover
                self._show_validation_error('Invalid section "{}:" found in show'.format(key))

    def _do_unload(self):
        self.show_steps = None

    def _get_tokens(self):
        self._walk_show(self.show_steps)

    def _walk_show(self, data, path=None, list_index=None):
        # walks a list of dicts, checking tokens
        if not path:
            path = list()

        if isinstance(data, dict):
            for k, v in data.items():
                self._check_token(path, k, 'key')
                self._walk_show(v, path + [k])

        elif isinstance(data, list):
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
        """Return a copy of the show steps."""
        if data == 'dummy_default!#$':
            data = self.show_steps

        if isinstance(data, dict):
            new_dict = dict()
            for k, v in data.items():
                new_dict[k] = self.get_show_steps(v)
            return new_dict
        elif isinstance(data, list):
            new_list = list()
            for i in data:
                new_list.append(self.get_show_steps(i))
            return new_list
        else:
            return data

    def _check_token(self, path, data, token_type):
        if not isinstance(data, str):
            return

        if data[0:1] == "(" and data[-1:] == ")":
            self._add_token(data[1:-1].lower(), path, token_type)

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

    # pylint: disable-msg=too-many-arguments
    def play(self, priority=0, speed=1.0, start_step=1, callback=None,
             loops=-1, sync_ms=0, manual_advance=False, show_tokens=None):
        """Play a Show.

        There are many parameters you can use here which
        affect how the show is played. This includes things like the playback
        speed, priority, etc. These are
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
            start_step: Integer of which step in the show file the show
                should start in. Usually this is 1 (start at the beginning
                of the show) but it's nice to start part way through. Also
                used for restarting shows that you paused. A negative value
                will count backwards from the end (-1 is the last position,
                -2 is second to last, etc.). Note this is the "human readable"
                step, so the first step is 1, not 0.
            callback: A callback function that is invoked when the show is
                stopped.
            loops: Integer of how many times you want this show to repeat
                before stopping. A value of -1 means that it repeats
                indefinitely. If the show only has one step, loops will be set
                to 0, regardless of the actual number of loops
            sync_ms: Number of ms of the show sync cycle. A value of zero means
                this show will also start playing immediately. See the full MPF
                documentation for details on how this works.
            manual_advance: Boolean that controls whether this show should be
                advanced manually (e.g. time values are ignored and the show
                doesn't move to the next step until it's told to.) Default is
                False.
            show_tokens: Replacement tokens for the show

        Returns: The RunningShow() instance if this show plays now, or False if
            the show is not loaded. (In this case the show will be loaded and
            will automatically play once its loaded.)
        """
        # todo bugfix, currently there is only one set of autoplay seetings,
        # so if multiple show instances are played but the show is not loaded,
        # only the last one will play
        if not show_tokens:
            show_tokens = dict()

        # todo if we want to enfore that show_tokens match the tokens in the
        # show exactly, uncomment below and remove the following if.
        # however we don't do this today because of the default 'off' show
        # that's used since it has lights and leds, so we'll have to think
        # about this.

        # if set(show_tokens.keys()) != self.tokens:
        #     raise ValueError('Token mismatch while playing show "{}". Tokens '
        #                      'expected: {}. Tokens submitted: {}'.format(
        #                      self.name, self.tokens, set(show_tokens.keys())))

        if not set(show_tokens.keys()).issubset(self.tokens):   # pragma: no cover
            raise ValueError('Token mismatch while playing show "{}". Tokens '
                             'expected: {}. Tokens submitted: {}'.
                             format(self.name, self.tokens, set(show_tokens.keys())))

        if self.loaded:
            show_steps = self.get_show_steps()
        else:
            show_steps = False

        running_show = RunningShow(machine=self.machine,
                                   show=self,
                                   show_steps=show_steps,
                                   priority=int(priority),
                                   speed=float(speed),
                                   start_step=int(start_step),
                                   callback=callback,
                                   loops=int(loops),
                                   sync_ms=int(sync_ms),
                                   manual_advance=manual_advance,
                                   show_tokens=show_tokens)

        if not self.loaded:
            self.load(callback=running_show.show_loaded, priority=priority)

        return running_show

    def load_show_from_disk(self):
        """Load show from disk."""
        show_version = YamlInterface.get_show_file_version(self.file)

        if show_version != int(__show_version__):   # pragma: no cover
            raise ValueError("Show file {} cannot be loaded. MPF v{} requires "
                             "#show_version={}".format(self.file,
                                                       __version__,
                                                       __show_version__))

        return FileManager.load(self.file)


# This class is more or less a container
# pylint: disable-msg=too-many-instance-attributes
class RunningShow(object):

    """A running instance of a show."""

    # pylint: disable-msg=too-many-arguments
    # pylint: disable-msg=too-many-locals
    def __init__(self, machine, show, show_steps, priority,
                 speed, start_step, callback, loops,
                 sync_ms, manual_advance, show_tokens):
        """Initialise an instance of a show."""
        self.machine = machine
        self.show = show
        self.show_steps = show_steps
        self.priority = priority
        self.speed = speed
        self.callback = callback
        self.loops = loops
        self.start_step = start_step
        self.sync_ms = sync_ms
        # self.mode = mode
        self.show_tokens = show_tokens
        self._delay_handler = None
        self.next_step_index = None
        self.current_step_index = None

        self.next_step_time = self.machine.clock.get_time()

        self.manual_advance = manual_advance

        self.name = show.name

        self.id = self.machine.show_controller.get_next_show_id()
        self._players = list()

        # if show_tokens:
        #     self.show_tokens = show_tokens
        # else:
        #     self.show_tokens = dict()

        self.debug = False
        self._stopped = False

        if show_steps:
            self._show_loaded = True
            self._start_play()
        else:
            self._show_loaded = False

    def show_loaded(self, show):
        """Called when a deferred show was loaded.

        Start playing the show as if it started earlier.
        """
        del show
        self._show_loaded = True
        self.show_steps = self.show.get_show_steps()
        self._start_play()

    def _start_play(self):
        if self._stopped:
            return

        self._total_steps = len(self.show_steps)

        if self.start_step > 0:
            self.next_step_index = self.start_step - 1
        elif self.start_step < 0:
            self.next_step_index = self.start_step % self._total_steps
        else:
            self.next_step_index = 0

        if self.show_tokens and self.show.tokens:
            self._replace_tokens(**self.show_tokens)

        self.show.running.add(self)
        self.machine.show_controller.notify_show_starting(self)

        # Figure out the show start time
        if self.sync_ms:
            delay_secs = (self.sync_ms / 1000.0) - (self.next_step_time % (self.sync_ms / 1000.0))
            self.next_step_time += delay_secs
            self._delay_handler = self.machine.clock.schedule_once(self._run_next_step,
                                                                   delay_secs)
        else:  # run now
            self._run_next_step()

    def __repr__(self):
        """Return str representation."""
        return 'Running Show Instance: "{}" {} {}'.format(self.name, self.show_tokens, self.next_step_index)

    def _replace_tokens(self, **kwargs):
        keys_replaced = dict()

        for token, replacement in kwargs.items():
            if token in self.show.token_values:
                for token_path in self.show.token_values[token]:
                    target = self.show_steps
                    for x in token_path[:-1]:
                        target = target[x]

                    target[token_path[-1]] = replacement

        for token, replacement in kwargs.items():
            if token in self.show.token_keys:
                key_name = '({})'.format(token)
                for token_path in self.show.token_keys[token]:
                    target = self.show_steps
                    for x in token_path:
                        if x in keys_replaced:
                            x = keys_replaced[x]

                        target = target[x]

                    if key_name in target:
                        target[replacement] = target.pop(key_name)
                    else:
                        # Fallback in case the token is no lowercase. Unfortunately, this can happen since every config
                        # player has its own config validator. Additionally, keys in dicts are not properly lowercased.
                        for key in target:
                            if key.lower() == key_name:
                                target[replacement] = target.pop(key)
                                break
                        else:   # pragma: no cover
                            raise KeyError("Could not find token {}".format(key_name))

                    keys_replaced[key_name] = replacement

    def stop(self):
        """Stop show."""
        if self._stopped:
            return

        self._stopped = True

        if not self._show_loaded:
            return

        self.machine.show_controller.notify_show_stopping(self)
        self.show.running.remove(self)
        self._remove_delay_handler()

        # clear context in used players
        for player in self._players:
            self.machine.show_controller.show_players[player].show_stop_callback("show_" + str(self.id))

        if self.callback and callable(self.callback):
            self.callback()

    def _remove_delay_handler(self):
        if self._delay_handler:
            self.machine.clock.unschedule(self._delay_handler)
            self._delay_handler = None

    def pause(self):
        """Pause show."""
        self._remove_delay_handler()

    def resume(self):
        """Resume paused show."""
        if not self._show_loaded:
            return
        self.next_step_time = self.machine.clock.get_time()
        self._run_next_step()

    def update(self, **kwargs):
        """Update show.

        Not implemented yet.
        """
        # todo
        raise NotImplementedError("Show update is not implemented yet. It's "
                                  "coming though...")

    def advance(self, steps=1, show_step=None):
        """Manually advance this show to the next step."""
        self._remove_delay_handler()

        if steps != 1:
            self.next_step_index += steps - 1
        elif show_step is not None:
            if not isinstance(show_step, int) or show_step < 0:
                raise AssertionError('Cannot advance {} to step "{}" as that is'
                                     'not a valid step number.'.format(self, show_step))
            self.next_step_index = show_step - 1

        if self._show_loaded:
            self._run_next_step()

    def step_back(self, steps=1):
        """Manually step back this show to a previous step."""
        self._remove_delay_handler()

        self.next_step_index -= steps + 1

        if self._show_loaded:
            self._run_next_step()

    def _run_next_step(self, dt=None):
        del dt

        if self.next_step_index < 0:
            self.next_step_index %= self._total_steps

        # if we're at the end of the show
        if self.next_step_index >= self._total_steps:

            if self.loops > 0:
                self.loops -= 1
                self.next_step_index = 0
            elif self.loops < 0:
                self.next_step_index = 0
            else:
                self.stop()
                return False

        self.current_step_index = self.next_step_index

        for item_type, item_dict in (
                iter(self.show_steps[self.current_step_index].items())):

            if item_type == 'duration':
                continue

            elif item_type in self.machine.show_controller.show_players:

                self.machine.show_controller.show_players[item_type].show_play_callback(
                    settings=item_dict,
                    context="show_" + str(self.id),
                    priority=self.priority,
                    show_tokens=self.show_tokens)

                if item_type not in self._players:
                    self._players.append(item_type)

        self.next_step_index += 1

        time_to_next_step = self.show_steps[self.current_step_index]['duration'] / self.speed
        if not self.manual_advance and time_to_next_step > 0:
            self.next_step_time += time_to_next_step
            self._delay_handler = self.machine.clock.schedule_once(self._run_next_step,
                                                                   self.next_step_time - self.machine.clock.get_time())

            return time_to_next_step
