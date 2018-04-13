import os
import re
import tempfile

import shutil

from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class MpfDocTestCase(MpfFakeGameTestCase):

    def __init__(self, config_string, methodName='test_config_parsing'):
        super().__init__(methodName)
        machine_config, mode_configs, self.tests = self.prepare_config(config_string)
        self.config_dir = tempfile.mkdtemp()

        # create machine config
        os.mkdir(os.path.join(self.config_dir, "config"))
        with open(os.path.join(self.config_dir, "config", "config.yaml"), "w") as f:
            f.write(machine_config)

        # create modes
        os.mkdir(os.path.join(self.config_dir, "modes"))
        for mode_name, mode_config in mode_configs.items():
            os.mkdir(os.path.join(self.config_dir, "modes", mode_name))
            os.mkdir(os.path.join(self.config_dir, "modes", mode_name, "config"))
            with open(os.path.join(self.config_dir, "modes", mode_name, "config", mode_name + ".yaml"), "w") as f:
                f.write(mode_config)

        # cleanup at the end
        self.addCleanup(self._delete_tmp_dir, self.config_dir)

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
        configs = re.split(r'^##! (?:config: (\w+)|test)\n', config_string, flags=re.MULTILINE)
        machine_config = configs.pop(0)

        # add config_version if missing
        if not machine_config.startswith("#config_version=5"):
            machine_config = "#config_version=5\n" + machine_config

        modes = {}
        tests = []
        while configs:
            mode_name = configs.pop(0)
            mode_config = configs.pop(0)
            if not mode_name:
                # unit test
                tests = mode_config.splitlines()
            else:
                # normal mode
                if not mode_config.startswith("#config_version=5"):
                    mode_config = "#config_version=5\n" + mode_config
                modes[mode_name] = mode_config

        # load all modes
        if modes:
            machine_config += "\nmodes:\n"
            for mode in modes.keys():
                machine_config += " - " + mode + "\n"

        return machine_config, modes, tests

    def getConfigFile(self):
        return "config.yaml"

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

            parts = line.split(" ")
            command = parts.pop(0)
            method = getattr(self, "command_" + command)
            if not method:
                raise AssertionError("Unknown command {} in line {}".format(command, line_no))
            try:
                method(*parts)
            except AssertionError as e:
                raise AssertionError("Error in line {}".format(line_no), e)


    def command_start_game(self):
        self.start_game()

    def command_post(self, event_name):
        self.post_event(event_name)

    def command_assert_player_variable(self, value, player_var):
        if isinstance(self.machine.game.player[player_var], (int, float)):
            value = float(value)
        self.assertPlayerVarEqual(value, player_var=player_var)
