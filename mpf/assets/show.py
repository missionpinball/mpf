import re
from mpf.core.assets import Asset, AssetPool
from mpf.core.config_player import ConfigPlayer
from mpf.core.file_manager import FileManager
from mpf.core.utility_functions import Util
from mpf.file_interfaces.yaml_interface import YamlInterface
from mpf._version import __show_version__, __version__


class ShowPool(AssetPool):
    def __repr__(self):
        return '<ShowPool: {}>'.format(self.name)

    @property
    def show(self):
        return self.asset


# pylint: disable-msg=too-many-instance-attributes
class Show(Asset):
    attribute = 'shows'
    path_string = 'shows'
    config_section = 'shows'
    disk_asset_section = 'file_shows'
    extensions = 'yaml'
    class_priority = 100
    pool_config_section = 'show_pools'
    asset_group_class = ShowPool

    next_id = 0

    @classmethod
    def get_id(cls):
        Show.next_id += 1
        return Show.next_id

    # pylint: disable-msg=too-many-arguments
    def __init__(self, machine, name, file=None, config=None, data=None):
        super().__init__(machine, name, file, config)

        self._autoplay_settings = dict()

        self._initialize_asset()

        self.tokens = set()
        self.token_values = dict()
        self.token_keys = dict()

        self.token_finder = re.compile('(?<=\\()(.*?)(?=\\))')

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
        return id(self) < id(other)

    def _initialize_asset(self):
        self.loaded = False
        self.show_steps = list()
        self.mode = None

    def do_load(self):
        self._do_load_show(None)

    def _do_load_show(self, data):
        self.show_steps = list()

        self.machine.show_controller.log.debug("Loading Show %s", self.file)
        if not data and self.file:
            data = self.load_show_from_disk()

        # Pylint complains about the change from dict to list. This is intended and fine.
        # pylint: disable-msg=redefined-variable-type
        if isinstance(data, dict):
            data = list(data)
        elif not isinstance(data, list):
            raise ValueError("Show {} does not appear to be a valid show "
                             "config".format(self.file))

        if not data:
            self._show_validation_error("Cannot load empty show")

        total_step_time = 0

        # add empty first step if show does not start right away
        if 'time' in data[0] and data[0]['time'] != 0:
            self.show_steps.append({'duration': data[0]['time']})
            total_step_time = data[0]['time']

        # Loop over all steps in the show file
        total_steps_num = len(data)
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
            if 'duration' not in step:
                if step_num == total_steps_num - 1:
                    # special case with an empty last step (but longer than 1 step)
                    if 'time' in step and len(step) == 1 and step_num != 0:
                        break
                    else:
                        #self._show_validation_error("Last step has 0 duration")
                        step['duration'] = 1
                elif 'time' in data[step_num + 1]:
                    next_step_time = data[step_num + 1]['time']
                    if str(next_step_time)[0] == "+":
                        step['duration'] = Util.string_to_secs(next_step_time)
                    else:
                        if total_step_time < 0:
                            self._show_validation_error("Absolute timing in step {} not possible because "
                                                        "there was a duration of -1 before".format(step_num))
                        step['duration'] = Util.string_to_secs(next_step_time) - total_step_time
                else:
                    step['duration'] = 1

            if step['duration'] == 0:
                self._show_validation_error("Step {} has 0 duration".format(step_num))

            # internally we only use duration
            if 'time' in step:
                del step['time']

            # Calculate the time since previous step
            actions['duration'] = step['duration']

            if step['duration'] > 0 and total_step_time >= 0:
                total_step_time += step['duration']
            else:
                total_step_time = -1

            # Now process show step actions
            self._process_step_actions(step, actions)

            self.show_steps.append(actions)

        # Count how many total steps are in the show. We need this later
        # so we can know when we're at the end of a show
        self.total_steps = len(self.show_steps)
        if self.total_steps == 0:
            self._show_validation_error("Show is empty")

        self._get_tokens()

    def _show_validation_error(self, msg):
        if self.file:
            identifier = self.file
        else:
            identifier = self.name

        raise AssertionError("Show {}: {}".format(identifier, msg))

    def _process_step_actions(self, step, actions):
        for key, value in step.items():

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

            elif key != 'duration':
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

    # pylint: disable-msg=too-many-arguments
    def play(self, priority=0, speed=1.0, start_step=1, callback=None,
             loops=-1, sync_ms=0, reset=True, mode=None,
             manual_advance=False, key=None, show_tokens=None):
        """Plays a Show. There are many parameters you can use here which
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
            reset: Boolean which controls whether this show will reset to its
                first position once it ends. Default is True.
            mode: A reference to the Mode instance that's playing this show.
                The show's priority will be based on this mode, and the show
                will automatically stop when this mode ends. Default is None.
            manual_advance: Boolean that controls whether this show should be
                advanced manually (e.g. time values are ignored and the show
                doesn't move to the next step until it's told to.) Default is
                False.
            key: String name of a key you can use to reference the running
                instance of this show. Useful when you have a show with tokens
                where you'll have multiple instances running and you need a way
                to idenify a specific instance.
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

        if not set(show_tokens.keys()).issubset(self.tokens):
            raise ValueError('Token mismatch while playing show "{}". Tokens '
                             'expected: {}. Tokens submitted: {}'.
                             format(self.name, self.tokens, set(show_tokens.keys())))

        if not self.loaded:
            self._autoplay_settings = dict(priority=priority,
                                           speed=speed,
                                           start_step=start_step,
                                           callback=callback,
                                           loops=loops,
                                           sync_ms=sync_ms,
                                           reset=reset,
                                           mode=mode,
                                           manual_advance=manual_advance,
                                           key=key,
                                           show_tokens=show_tokens
                                           )

            self.load(callback=self._autoplay, priority=priority)
            return False

        return RunningShow(machine=self.machine,
                           show=self,
                           show_steps=self.get_show_steps(),
                           priority=int(priority),
                           speed=float(speed),
                           start_step=int(start_step),
                           callback=callback,
                           loops=int(loops),
                           sync_ms=int(sync_ms),
                           reset=bool(reset),
                           mode=mode,
                           manual_advance=manual_advance,
                           key=key,
                           show_tokens=show_tokens)

    def _autoplay(self, *args, **kwargs):
        del args
        del kwargs
        self.play(**self._autoplay_settings)

    def load_show_from_disk(self):

        show_version = YamlInterface.get_show_file_version(self.file)

        if show_version != int(__show_version__):
            raise ValueError("Show file {} cannot be loaded. MPF v{} requires "
                             "#show_version={}".format(self.file,
                                                       __version__,
                                                       __show_version__))

        return FileManager.load(self.file)


# This class is more or less a container
# pylint: disable-msg=too-many-instance-attributes
class RunningShow(object):
    # pylint: disable-msg=too-many-arguments
    # pylint: disable-msg=too-many-locals
    def __init__(self, machine, show, show_steps, priority,
                 speed, start_step, callback, loops,
                 sync_ms, reset, mode, manual_advance, key,
                 show_tokens):
        self.machine = machine
        self.show = show
        self.show_steps = show_steps
        self.priority = priority
        self.speed = speed
        self.callback = callback
        self.loops = loops
        self.reset = reset
        # self.mode = mode
        self.show_tokens = show_tokens

        del mode
        # TODO: remove mode from __init__
        self.manual_advance = manual_advance

        self.name = show.name

        if not key:
            self.key = '{}.{}'.format(self.name, Show.get_id())
        else:
            self.key = key

        # if show_tokens:
        #     self.show_tokens = show_tokens
        # else:
        #     self.show_tokens = dict()

        self.debug = False
        self._stopped = False

        self._total_steps = len(show_steps)

        if start_step > 0:
            self.next_step_index = start_step - 1
        elif start_step < 0:
            self.next_step_index = self._total_steps + start_step
        else:
            self.next_step_index = 0

        if show_tokens and show.tokens:
            self._replace_tokens(**show_tokens)

        show.running.add(self)
        self.machine.show_controller.notify_show_starting(self)

        # Figure out the show start time
        self.next_step_time = self.machine.clock.get_time()

        if sync_ms:
            delay_secs = (sync_ms / 1000.0) - (self.next_step_time % (sync_ms /
                                               1000.0))
            self.next_step_time += delay_secs
            self.machine.clock.schedule_once(self._run_next_step,
                                             delay_secs)
        else:  # run now
            self._run_next_step()

    def __repr__(self):
        return 'Running Show Instance: "{}"'.format(self.name)

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

                    target[replacement] = target.pop(key_name)
                    keys_replaced[key_name] = replacement

    def stop(self):
        if self._stopped:
            return

        self._stopped = True
        # todo I think there's a potential memory leak here as shows stop but
        # some things still hold references to them. (Shots, for example).
        # need to investigate more

        self.machine.show_controller.notify_show_stopping(self)
        self.show.running.remove(self)
        self.machine.clock.unschedule(self._run_next_step, True)

        # todo this could be smarter, to only clear players that were
        # actually used in this show instead of all of them

        self.machine.events.post('clear', key=self.key)
        # description for this event is in the mode module

        if self.callback and callable(self.callback):
            self.callback()

    def pause(self):
        self.machine.clock.unschedule(self._run_next_step, True)

    def resume(self):
        # todo this needs work
        self._run_next_step()

    def update(self, **kwargs):
        # todo
        raise NotImplementedError("Show update is not implemented yet. It's "
                                  "coming though...")

    def advance(self, steps=1, show_step=None):
        """Manually advances this show to the next step."""

        if isinstance(show_step, int) and show_step < 0:
            raise ValueError('Cannot advance {} to step "{}" as that is'
                             'not a valid step number.'.format(self, show_step))

        self.machine.clock.unschedule(self._run_next_step, True)
        steps_to_advance = steps - 1  # since current_step is really next step

        # todo should this end the show if there are more steps than in the
        # show and it's not set to loop?

        if steps_to_advance:
            self.next_step_index = self._total_steps % steps_to_advance
        elif show_step is not None:
            self.next_step_index = show_step - 1

        self._run_next_step()
        return self.next_step_index - 1  # current step is actually the next
        #  step

    def _run_next_step(self, dt=None):
        del dt

        # todo dunno why we have to do this. It's needed with unit tests
        if self.machine.clock.get_time() < self.next_step_time:
            return

        # if we're at the end of the show
        if self.next_step_index == self._total_steps:

            if self.loops > 0:
                self.loops -= 1
                self.next_step_index = 0
            elif self.loops < 0:
                self.next_step_index = 0
            else:
                self.stop()
                return False

        current_step_index = self.next_step_index

        for item_type, item_dict in (
                iter(self.show_steps[current_step_index].items())):

            if item_type == 'duration':
                continue

            elif item_type in ConfigPlayer.show_players:
                if item_type in item_dict:
                    item_dict = item_dict[item_type]

                ConfigPlayer.show_players[item_type].show_play_callback(
                    settings=item_dict,
                    key=self.key,
                    priority=self.priority,
                    show_tokens=self.show_tokens)

        self.next_step_index += 1

        time_to_next_step = self.show_steps[current_step_index]['duration'] / self.speed
        if not self.manual_advance and time_to_next_step > 0:
            self.next_step_time = self.machine.clock.get_time() + time_to_next_step
            self.machine.clock.schedule_once(self._run_next_step,
                                             time_to_next_step)

            return time_to_next_step
