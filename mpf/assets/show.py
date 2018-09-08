"""Contains show related classes."""
import tempfile
import hashlib
import os
import re
from collections import namedtuple

from mpf.core.assets import Asset, AssetPool
from mpf.core.config_validator import RuntimeToken
from mpf.core.utility_functions import Util

__api__ = ['Show', 'RunningShow', 'ShowPool']

ShowConfig = namedtuple("ShowConfig", ["name", "priority", "speed", "loops", "sync_ms", "manual_advance", "show_tokens",
                                       "events_when_played", "events_when_stopped", "events_when_looped",
                                       "events_when_paused", "events_when_resumed", "events_when_advanced",
                                       "events_when_stepped_back", "events_when_updated", "events_when_completed"])


class ShowPool(AssetPool):

    """A pool of shows."""

    __slots__ = []

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
    extensions = tuple('yaml')
    class_priority = 100
    pool_config_section = 'show_pools'
    asset_group_class = ShowPool

    __slots__ = ["_autoplay_settings", "tokens", "token_values", "token_keys", "name", "total_steps", "show_steps",
                 "loaded", "mode"]

    # pylint: disable-msg=too-many-arguments
    def __init__(self, machine, name, file=None, config=None, data=None):
        """Initialise show."""
        super().__init__(machine, name, file, config)

        self._autoplay_settings = dict()

        self._initialize_asset()

        self.tokens = set()
        self.token_values = dict()
        self.token_keys = dict()

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

            elif key not in ('duration', 'time'):   # pragma: no cover
                self._show_validation_error('Invalid section "{}:" found in show {}'.format(key, self.name))

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

        return data

    def _check_token(self, path, data, token_type):
        if isinstance(data, RuntimeToken):
            self._add_token(data, data.token, path, token_type)
            return
        if not isinstance(data, str):
            return

        results = re.findall(r"\(([^)]+)\)", data)
        if results:
            for result in results:
                self._add_token(data, result, path, token_type)

    def _add_token(self, placeholder, token, path, token_type):

        if token not in self.tokens:
            self.tokens.add(token)

        if token_type == 'key':
            if token not in self.token_keys:
                self.token_keys[token] = list()
            self.token_keys[token].append(path + [placeholder])

        elif token_type == 'value':
            if token not in self.token_values:
                self.token_values[token] = list()
            self.token_values[token].append(path)

    def play_with_config(self, show_config: ShowConfig, start_time=None, start_callback=None, stop_callback=None,
                         start_step=None) -> "RunningShow":
        """Play this show with config."""
        if self.loaded:
            show_steps = self.get_show_steps()
        else:
            show_steps = False

        if not start_time:
            start_time = self.machine.clock.get_time()

        running_show = RunningShow(machine=self.machine,
                                   show=self,
                                   show_steps=show_steps,
                                   start_time=start_time,
                                   start_step=int(start_step),
                                   callback=stop_callback,
                                   start_callback=start_callback,
                                   show_config=show_config)

        if not self.loaded:
            self.load(callback=running_show.show_loaded, priority=show_config.priority)

        return running_show

    # pylint: disable-msg=too-many-arguments
    # pylint: disable-msg=too-many-locals
    def play(self, priority=0, speed=1.0, start_step=1, callback=None,
             loops=-1, sync_ms=None, manual_advance=False, show_tokens=None,
             events_when_played=None, events_when_stopped=None,
             events_when_looped=None, events_when_paused=None,
             events_when_resumed=None, events_when_advanced=None,
             events_when_stepped_back=None, events_when_updated=None,
             events_when_completed=None, start_time=None, start_callback=None) -> "RunningShow":
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
                this show will also start playing immediately. A value of None
                means the mpf:default_show_sync_ms will be used.
            manual_advance: Boolean that controls whether this show should be
                advanced manually (e.g. time values are ignored and the show
                doesn't move to the next step until it's told to.) Default is
                False.
            show_tokens: Replacement tokens for the show

        Returns:
            The RunningShow() instance if this show plays now, or False if
            the show is not loaded. (In this case the show will be loaded and
            will automatically play once its loaded.)
        """
        if not show_tokens:
            show_tokens = dict()

        # todo if we want to enforce that show_tokens match the tokens in the
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

        show_config = self.machine.show_controller.create_show_config(
            self.name, priority, speed, loops, sync_ms, manual_advance, show_tokens, events_when_played,
            events_when_stopped, events_when_looped, events_when_paused, events_when_resumed, events_when_advanced,
            events_when_stepped_back, events_when_updated, events_when_completed)

        return self.play_with_config(show_config, start_time, start_callback, callback, start_step)

    @staticmethod
    def _get_mpfcache_file_name(file_name):
        cache_dir = tempfile.gettempdir()
        path_hash = str(hashlib.md5(bytes(file_name, 'UTF-8')).hexdigest())     # nosec
        result = os.path.join(cache_dir, path_hash)
        return result + ".mpf_cache"

    def load_show_from_disk(self):
        """Load show from disk."""
        return self.machine.config_processor.load_config_files_with_cache(
            [self.file], "show", load_from_cache=not self.machine.options['no_load_cache'],
            store_to_cache=self.machine.options['create_config_cache'])


# This class is more or less a container
# pylint: disable-msg=too-many-instance-attributes
class RunningShow:

    """A running instance of a show."""

    __slots__ = ["machine", "show", "show_steps", "show_config", "callback", "start_step", "start_callback",
                 "_delay_handler", "next_step_index", "current_step_index", "next_step_time", "name", "loops",
                 "id", "_players", "debug", "_stopped", "_show_loaded", "_total_steps", "context"]

    # pylint: disable-msg=too-many-arguments
    # pylint: disable-msg=too-many-locals
    def __init__(self, machine, show, show_steps, start_step, callback, start_time, start_callback, show_config):
        """Initialise an instance of a show."""
        self.machine = machine
        self.show = show
        self.show_steps = show_steps
        self.show_config = show_config
        self.callback = callback
        self.start_step = start_step
        self.start_callback = start_callback
        self._delay_handler = None
        self.next_step_index = None
        self.current_step_index = None
        self.next_step_time = start_time
        self.name = show.name
        self.loops = self.show_config.loops

        self.id = self.machine.show_controller.get_next_show_id()
        self.context = "show_{}".format(self.id)
        self._players = set()

        # if show_tokens:
        #     self.show_tokens = show_tokens
        # else:
        #     self.show_tokens = dict()
        self.debug = False
        self._stopped = False
        self._total_steps = None

        if show_steps:
            self._show_loaded = True
            self._start_play()
        else:
            self._show_loaded = False

    def show_loaded(self, show):
        """Handle that a deferred show was loaded.

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

        if self.show_config.show_tokens and self.show.tokens:
            self._replace_token_values(**self.show_config.show_tokens)
            self._replace_token_keys(**self.show_config.show_tokens)

        # Figure out the show start time
        if self.show_config.sync_ms:
            # calculate next step based on synchronized start time
            self.next_step_time += (self.show_config.sync_ms / 1000.0) - (self.next_step_time %
                                                                          (self.show_config.sync_ms / 1000.0))
            # but wait relative to real time
            delay_secs = self.next_step_time - self.machine.clock.get_time()
            self._delay_handler = self.machine.clock.schedule_once(
                self._start_now, delay_secs)
        else:  # run now
            self._start_now()

    def _post_events(self, actions):
        for action in actions:
            events = getattr(self.show_config, "events_when_{}".format(action), None)
            if events:
                for event in events:
                    self.machine.events.post(event)

    def __repr__(self):
        """Return str representation."""
        return 'Running Show Instance: "{}" {} {}'.format(self.name, self.show_config.show_tokens, self.next_step_index)

    def _replace_token_values(self, **kwargs):

        for token, replacement in kwargs.items():
            if token in self.show.token_values:
                for token_path in self.show.token_values[token]:
                    target = self.show_steps
                    for x in token_path[:-1]:
                        target = target[x]

                    if isinstance(target[token_path[-1]], RuntimeToken):
                        target[token_path[-1]] = target[token_path[-1]].validator_function(replacement, None)
                    elif target[token_path[-1]] == "(" + token + ")":
                        target[token_path[-1]] = replacement
                    else:
                        target[token_path[-1]] = target[token_path[-1]].replace("(" + token + ")", replacement)

    def _replace_token_keys(self, **kwargs):
        keys_replaced = dict()
        # pylint: disable-msg=too-many-nested-blocks
        for token, replacement in kwargs.items():
            if token in self.show.token_keys:
                key_name = '({})'.format(token)
                for token_path in self.show.token_keys[token]:
                    target = self.show_steps
                    token_str = ""
                    for x in token_path[:-1]:
                        if token_str in keys_replaced:
                            x = keys_replaced[token_str + str(x) + "-"]
                        token_str += str(x) + "-"

                        target = target[x]
                    use_string_replace = bool(token_path[-1] != "(" + token + ")")

                    final_key = token_path[-1]
                    # check if key has been replaced before
                    final_key = keys_replaced.get(final_key, final_key)

                    if use_string_replace:
                        replaced_key = final_key.replace("(" + token + ")", replacement)
                    else:
                        replaced_key = replacement

                    if final_key in target:
                        target[replaced_key] = target.pop(final_key)
                    else:
                        raise KeyError("Could not find token {} ({}) in {}".format(final_key, key_name, target))

                    keys_replaced[token_str] = replaced_key

    @property
    def stopped(self):
        """Return if stopped."""
        return self._stopped

    def stop(self):
        """Stop show."""
        if self._stopped:
            return

        self._stopped = True

        # if the start callback has never been called then call it now
        if self.start_callback:
            self.start_callback()
            self.start_callback = None

        self._remove_delay_handler()

        # clear context in used players
        for player in self._players:
            self.machine.show_controller.show_players[player].show_stop_callback(self.context)

        self._players = set()

        if self.callback and callable(self.callback):
            self.callback()

        self._post_events(['stopped'])

    def _remove_delay_handler(self):
        if self._delay_handler:
            self.machine.clock.unschedule(self._delay_handler)
            self._delay_handler = None

    def pause(self):
        """Pause show."""
        self._remove_delay_handler()
        self._post_events(['paused'])

    def resume(self):
        """Resume paused show."""
        if not self._show_loaded:
            return
        self.next_step_time = self.machine.clock.get_time()
        self._run_next_step(post_events='resumed')

    def update(self, **kwargs):
        """Update show.

        Not implemented yet.
        """
        # todo
        raise NotImplementedError("Show update is not implemented yet. It's "
                                  "coming though...")

        # don't forget this when we implement this feature
        # self._post_events(['updated'])

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
            self._run_next_step(post_events='advanced')

    def step_back(self, steps=1):
        """Manually step back this show to a previous step."""
        self._remove_delay_handler()

        self.next_step_index -= steps + 1

        if self._show_loaded:
            self._run_next_step(post_events='stepped_back')

    def _start_now(self) -> None:
        """Start playing the show."""
        if self.start_callback:
            self.start_callback()
            self.start_callback = None
        self._run_next_step(post_events='played')

    def _run_next_step(self, post_events=None) -> None:
        """Run the next show step."""
        events = []
        if post_events:
            events.append(post_events)

        if self.next_step_index < 0:
            self.next_step_index %= self._total_steps

        # if we're at the end of the show
        if self.next_step_index >= self._total_steps:

            if self.loops > 0:
                self.loops -= 1
                self.next_step_index = 0
                events.append('looped')
            elif self.loops < 0:
                self.next_step_index = 0
                events.append('looped')
            else:
                self.stop()
                events.append("completed")
                self._post_events(events)
                return

        self.current_step_index = self.next_step_index

        for item_type, item_dict in self.show_steps[self.current_step_index].items():

            if item_type == 'duration':
                continue

            player = self.machine.show_controller.show_players.get(item_type, None)

            if not player:
                raise ValueError("Invalid entry in show: {}".format(item_type))

            player.show_play_callback(
                settings=item_dict,
                context=self.context,
                calling_context=self.current_step_index,
                priority=self.show_config.priority,
                show_tokens=self.show_config.show_tokens,
                start_time=self.next_step_time)

            self._players.add(item_type)

        self._post_events(events)

        self.next_step_index += 1

        time_to_next_step = self.show_steps[self.current_step_index]['duration'] / self.show_config.speed
        if not self.show_config.manual_advance and time_to_next_step > 0:
            self.next_step_time += time_to_next_step
            self._delay_handler = self.machine.clock.schedule_once(self._run_next_step,
                                                                   self.next_step_time - self.machine.clock.get_time())
