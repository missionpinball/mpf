import os
import re
import tempfile

import shutil
import shlex

from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase
from mpf.tests.MpfMachineTestCase import MockConfigPlayers


class MpfDocTestCase(MockConfigPlayers, MpfFakeGameTestCase):

    def __init__(self, config_string, methodName='test_config_parsing'):
        super().__init__(methodName)
        machine_config, mode_configs, show_configs, self.tests = self.prepare_config(config_string)
        self.config_dir = tempfile.mkdtemp()

        # create machine config
        os.mkdir(os.path.join(self.config_dir, "config"))
        with open(os.path.join(self.config_dir, "config", "config.yaml"), "w") as f:
            f.write(machine_config)

        # create shows
        os.mkdir(os.path.join(self.config_dir, "shows"))
        for show_name, show_config in show_configs.items():
            with open(os.path.join(self.config_dir, "shows", show_name + ".yaml"), "w") as f:
                f.write(show_config)

        # create modes
        os.mkdir(os.path.join(self.config_dir, "modes"))
        for mode_name, mode_config in mode_configs.items():
            os.mkdir(os.path.join(self.config_dir, "modes", mode_name))
            os.mkdir(os.path.join(self.config_dir, "modes", mode_name, "config"))
            with open(os.path.join(self.config_dir, "modes", mode_name, "config", mode_name + ".yaml"), "w") as f:
                f.write(mode_config)

        # cleanup at the end
        self.addCleanup(self._delete_tmp_dir, self.config_dir)

    def get_enable_plugins(self):
        return True

    def getOptions(self):
        options = super().getOptions()
        # no cache since we are in a tmp folder anyway
        options['no_load_cache'] = True,
        options['create_config_cache'] = False
        return options

    def prepare_config(self, config_string):
        # inline invisible comments from documentation
        config_string = re.sub(r'^#! ([^\n]+)', '\\1', config_string, flags=re.MULTILINE)

        # first find sections
        configs = re.split(r'^##! (config: \w+|test|show: \w+|mode: \w+)\n', config_string, flags=re.MULTILINE)
        machine_config = configs.pop(0)

        # add config_version if missing
        if not machine_config.startswith("#config_version=5"):
            machine_config = "#config_version=5\n" + machine_config

        modes = {}
        shows = {}
        tests = []
        while configs:
            section_type = configs.pop(0)
            section_config = configs.pop(0)
            if section_type.startswith("test"):
                # unit test
                tests = section_config.splitlines()
            elif section_type.startswith("mode:") or section_type.startswith("config:"):
                # normal mode
                _, mode_name = section_type.split(": ", 2)
                if not section_config.startswith("#config_version=5"):
                    section_config = "#config_version=5\n" + section_config
                modes[mode_name] = section_config
            elif section_type.startswith("show:"):
                # show
                _, show_name = section_type.split(": ", 2)
                if not section_config.startswith("#show_version=5"):
                    section_config = "#show_version=5\n" + section_config
                shows[show_name] = section_config

        # load all modes
        if modes and "modes:" not in machine_config:
            machine_config += "\nmodes:\n"
            for mode in modes.keys():
                machine_config += " - " + mode + "\n"

        return machine_config, modes, shows, tests

    def getConfigFile(self):
        return "config.yaml"

    def get_platform(self):
        return "smart_virtual"

    def getMachinePath(self):
        return self.config_dir

    def _delete_tmp_dir(self, config_dir):
        shutil.rmtree(config_dir)

    def test_config_parsing(self):
        line_no = 0
        for line in self.tests:
            line_no += 1
            if not line or line.startswith("#"):
                continue

            parts = shlex.split(line)
            command = parts.pop(0)
            method = getattr(self, "command_" + command)
            if not method:
                raise AssertionError("Unknown command {} in line {}".format(command, line_no))
            try:
                method(*parts)
            except AssertionError as e:
                raise AssertionError("Error in line {}".format(line_no), e)

    def command_start_game(self, num_balls_known=3):
        self.start_game(num_balls_known=int(num_balls_known))

    def command_stop_game(self, stop_time=1):
        self.stop_game(float(stop_time))

    def command_drain_all_balls(self):
        self.drain_all_balls()

    def command_drain_one_ball(self):
        self.drain_one_ball()

    def command_start_mode(self, mode):
        self.machine.modes[mode].start()
        self.machine_run()
        self.assertModeRunning(mode)

    def command_stop_mode(self, mode):
        self.machine.modes[mode].stop()
        self.machine_run()
        self.assertModeNotRunning(mode)

    def command_assert_mode_running(self, mode):
        self.assertModeRunning(mode)

    def command_assert_mode_not_running(self, mode):
        self.assertModeNotRunning(mode)

    def command_post(self, event_name, *args):
        kwargs = {}
        for arg in args:
            key, value = arg.split("=", 2)
            kwargs[key] = value
        self.post_event_with_params(event_name, **kwargs)

    def command_hit_and_release_switch(self, switch_name):
        self.hit_and_release_switch(switch_name)

    def command_hit_and_release_switches_simultaneously(self, switch_name1, switch_name2):
        self.hit_and_release_switches_simultaneously([switch_name1, switch_name2])

    def command_hit_switch(self, switch_name):
        self.hit_switch_and_run(switch_name, 0)

    def command_release_switch(self, switch_name):
        self.release_switch_and_run(switch_name, 0)

    def command_advance_time_and_run(self, delta):
        self.advance_time_and_run(float(delta))

    def command_assert_player_variable(self, value, player_var):
        if isinstance(self.machine.game.player[player_var], (int, float)):
            value = float(value)
        self.assertPlayerVarEqual(value, player_var=player_var)

    def command_assert_player_count(self, count):
        self.assertPlayerCount(int(count))

    def command_assert_machine_variable(self, value, name):
        if name in self.machine.machine_vars and isinstance(self.machine.machine_vars[name]["value"], (int, float)):
            value = float(value)
        self.assertMachineVarEqual(value, name)

    def command_assert_light_color(self, light, color):
        self.assertLightColor(light, color)

    def command_assert_light_flashing(self, light, color, secs=1, delta=.1):
        self.assertLightFlashing(light, color, float(secs), float(delta))

    def command_mock_event(self, name):
        self.mock_event(name)

    def command_assert_event_called(self, name, times=1):
        self.assertEventCalled(name, int(times))

    def command_assert_event_not_called(self, name):
        self.assertEventNotCalled(name)

    def command_assert_balls_on_playfield(self, balls):
        self.assertBallsOnPlayfield(int(balls))

    def command_assert_balls_in_play(self, balls):
        self.assertBallsInPlay(int(balls))

    def command_assert_bool_condition(self, expected, condition):
        expected_bool = expected == "True"
        self.assertPlaceholderEvaluates(expected_bool, condition)

    def command_assert_int_condition(self, expected, condition):
        expected_int = int(expected)
        self.assertPlaceholderEvaluates(expected_int, condition)

    def command_assert_float_condition(self, expected, condition):
        expected_float = float(expected)
        self.assertPlaceholderEvaluates(expected_float, condition)
