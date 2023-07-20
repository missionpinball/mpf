import logging
import os
import re
import tempfile

import shutil
import shlex

from mpf.tests.MpfGameTestCase import MpfGameTestCase

from mpf.file_interfaces.yaml_roundtrip import YamlRoundtrip

from mpf.file_interfaces.yaml_interface import YamlInterface

from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase
from mpf.tests.MpfMachineTestCase import MockConfigPlayers


class MpfDocTestCaseBase(MockConfigPlayers, MpfGameTestCase):
    def __init__(self, config_string, base_dir = None, simulation=True, methodName='test_config_parsing'):
        super().__init__(methodName)
        self._config_string = config_string
        self._base_dir = base_dir
        self._simulation = simulation
        self.log = logging.getLogger("TEST")

    def setUp(self):
        machine_config, extra_configs, mode_configs, show_configs, assets, code, self.tests = \
            self.prepare_config(self._config_string)
        self.config_dir = tempfile.mkdtemp()
        # cleanup at the end
        self.addCleanup(self._delete_tmp_dir, self.config_dir)

        # create machine config
        os.mkdir(os.path.join(self.config_dir, "config"))
        self.verify_yaml(machine_config, "config/config.yaml")
        with open(os.path.join(self.config_dir, "config/", "config.yaml"), "w") as f:
            f.write(machine_config)

        # create shows
        os.mkdir(os.path.join(self.config_dir, "shows"))
        for show_name, show_config in show_configs.items():
            self.verify_yaml(show_config, "shows/" + show_name + ".yaml", show_file=True)
            with open(os.path.join(self.config_dir, "shows", show_name + ".yaml"), "w") as f:
                f.write(show_config)

        # create modes
        os.mkdir(os.path.join(self.config_dir, "modes"))
        for mode_name, mode_config in mode_configs.items():
            self.verify_yaml(mode_config, "modes/" + mode_name + "/config/" + mode_name + ".yaml")
            os.mkdir(os.path.join(self.config_dir, "modes", mode_name))
            os.mkdir(os.path.join(self.config_dir, "modes", mode_name, "config"))
            with open(os.path.join(self.config_dir, "modes", mode_name, "config", mode_name + ".yaml"), "w") as f:
                f.write(mode_config)

        # create code files
        for file_path, file_content in code:
            os.mkdir(os.path.join(self.config_dir, *file_path[:-1]))
            with open(os.path.join(self.config_dir, *file_path), "w") as f:
                f.write(file_content)

        # create extra configs
        for config_name, extra_config in extra_configs.items():
            self.verify_yaml(extra_config, config_name + ".yaml")
            with open(os.path.join(self.config_dir, config_name + ".yaml"), "w") as f:
                f.write(extra_config)

        # link assets
        for asset_path, asset_source in assets.items():
            if not self._base_dir:
                raise AssertionError("You need to set base_dir to use assets.")
            path_elements = asset_path.split("/")
            source_elements = asset_source.split("/")
            full_source_path = os.path.join(self._base_dir, *source_elements)
            try:
                os.mkdir(os.path.join(self.config_dir, *path_elements[:-1]))
            except FileExistsError:
                pass
            self.get_absolute_machine_path()
            if not os.path.isfile(full_source_path):
                raise AssertionError('Could not find asset "{}" on disk'.format(full_source_path))
            os.symlink(full_source_path, os.path.join(self.config_dir, *path_elements))

        super().setUp()

    @staticmethod
    def unidiff_output(expected, actual):
        """
        Helper function. Returns a string containing the unified diff of two multiline strings.
        """

        import difflib
        expected = expected.splitlines(1)
        actual = actual.splitlines(1)

        diff = difflib.unified_diff(expected, actual)

        return ''.join(diff)

    def verify_yaml(self, yaml_string, config_name, show_file=False):
        formatted_yaml = YamlRoundtrip.reformat_yaml(yaml_string, show_file=show_file)
        if formatted_yaml == "null\n...\n":
            # special case: empty config
            return
        if yaml_string.strip() != formatted_yaml.strip():
            #self.maxDiff = None
            #self.assertEqual(yaml_string, formatted_yaml)
            diff = self.unidiff_output(yaml_string.strip() + "\n", formatted_yaml.strip() + "\n")
            self.fail("Config {} unformatted. Diff:\n{}".format(
              config_name, diff))

    def get_enable_plugins(self):
        return True

    def get_options(self):
        options = super().get_options()
        # no cache since we are in a tmp folder anyway
        options['no_load_cache'] = True,
        options['create_config_cache'] = False
        return options

    @staticmethod
    def prepare_config(config_string, fixup_config=True):
        # inline invisible comments from documentation
        if fixup_config:
            config_string = re.sub(r'^#! ([^\n]+)', '\\1', config_string, flags=re.MULTILINE)

        # first find sections
        configs = re.split(r'^##! (config: [^\n]+|test|show: \w+|mode: \w+|asset: [^\n]+|code: [^\n]+)\n', config_string,
                           flags=re.MULTILINE)
        machine_config = configs.pop(0)

        # add config_version if missing
        if fixup_config and not machine_config.startswith("#config_version=6"):
            machine_config = "#config_version=6\n" + machine_config

        modes = {}
        shows = {}
        tests = []
        assets = {}
        extra_configs = {}
        game_code = []
        while configs:
            section_type = configs.pop(0)
            section_config = configs.pop(0)
            if section_type.startswith("test"):
                # unit test
                tests = section_config.splitlines()
            elif section_type.startswith("config:"):
                # extra config file
                _, file_name = section_type.split(": ", 2)
                if fixup_config and not section_config.startswith("#config_version=6"):
                    section_config = "#config_version=6\n" + section_config
                extra_configs[file_name] = section_config
            elif section_type.startswith("mode:"):
                # normal mode
                _, mode_name = section_type.split(": ", 2)
                if fixup_config and not section_config.startswith("#config_version=6"):
                    section_config = "#config_version=6\n" + section_config
                modes[mode_name] = section_config
            elif section_type.startswith("show:"):
                # show
                _, show_name = section_type.split(": ", 2)
                if fixup_config and not section_config.startswith("#show_version=6"):
                    section_config = "#show_version=6\n" + section_config
                shows[show_name] = section_config
            elif section_type.startswith("asset:"):
                # asset
                _, asset_desc = section_type.split(": ", 2)
                asset_path, asset_source = asset_desc.split("=", 2)
                assets[asset_path] = asset_source
            elif section_type.startswith("code:"):
                # asset
                _, file_location = section_type.split(": ", 2)
                game_code.append((file_location.split("/"), section_config))
            else:
                raise AssertionError("Invalid section: {}".format(section_type))

        # load all modes
        if fixup_config and modes and "modes:" not in machine_config:
            machine_config += "\nmodes:\n"
            for mode in modes.keys():
                machine_config += "  - " + mode + "\n"

        return machine_config, extra_configs, modes, shows, assets, game_code, tests

    def get_config_file(self):
        return "config.yaml"

    def get_platform(self):
        if self._simulation:
            return "smart_virtual"
        else:
            return "virtual"

    def get_machine_path(self):
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
            self.log.info("%s", line)
            try:
                method(*parts)
            except AssertionError as e:
                raise AssertionError("Error in assertion {} (Num: {}) of your tests.".format(command, line_no)) from e

    def command_add_player(self):
        self.add_player()

    def command_stop_game(self, stop_time=1):
        self.stop_game(float(stop_time))

    def command_start_two_player_game(self):
        self.start_two_player_game()

    def command_drain_all_balls(self):
        self.drain_all_balls()

    def command_drain_one_ball(self):
        self.drain_one_ball()

    def command_add_ball_to_device(self, device_name):
        if device_name not in self.machine.ball_devices:
            raise AssertionError("Invalid ball device {}".format(device_name))
        self.machine.default_platform.add_ball_to_device(self.machine.ball_devices[device_name])

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
        if name in self.machine.variables.machine_vars and isinstance(
                self.machine.variables.machine_vars[name]["value"], (int, float)):
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

    def command_assert_available_balls_on_playfield(self, balls):
        self.assertAvailableBallsOnPlayfield(int(balls))

    def command_assert_balls_in_play(self, balls):
        self.assertBallsInPlay(int(balls))

    def command_assert_str_condition(self, expected, condition):
        expected_str = str(expected)
        self.assertPlaceholderEvaluates(expected_str, condition)

    def command_assert_bool_condition(self, expected, condition):
        expected_bool = expected == "True"
        self.assertPlaceholderEvaluates(expected_bool, condition)

    def command_assert_int_condition(self, expected, condition):
        expected_int = int(expected)
        self.assertPlaceholderEvaluates(expected_int, condition)

    def command_assert_float_condition(self, expected, condition):
        expected_float = float(expected)
        self.assertPlaceholderEvaluates(expected_float, condition)


class MpfDocTestCaseNoFakeGame(MpfDocTestCaseBase):

    """Test case with real game."""

    def command_start_game(self):
        self.start_game()


class MpfDocTestCase(MpfDocTestCaseBase, MpfFakeGameTestCase):

    """Test case with fake game."""

    def command_start_game(self, num_balls_known=3):
        self.start_game(num_balls_known=int(num_balls_known))
