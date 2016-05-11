import inspect
from mpf.core.machine import MachineController
from mpf.tests.MpfTestCase import MpfTestCase


class MpfMachineTestCase(MpfTestCase):

    def __init__(self, methodName='runTest'):
        super().__init__(methodName)

        # only disable bcp. everything else should run
        self.machine_config_patches = dict()
        self.machine_config_patches['bcp'] = []

        # increase test expected duration
        self.expected_duration = 5.0

    @staticmethod
    def _load_mc_players(cls):
        mc_players = {
            "sound_player": "mpfmc.config_players.sound_player",
            "widget_player": "mpfmc.config_players.widget_player",
            "slide_player": "mpfmc.config_players.slide_player"
        }

        for name, module in mc_players.items():
            imported_module = inspect.importlib.import_module(module)
            setattr(cls, '{}_player'.format(name),
                    imported_module.player_cls(cls))

    def setUp(self):
        MachineController._register_plugin_config_players = self._load_mc_players
        super().setUp()

    def get_enable_plugins(self):
        return True

    def getConfigFile(self):
        return "config.yaml"

    def getMachinePath(self):
        return ""

    def getAbsoluteMachinePath(self):
        # do not use path relative to MPF folder
        return self.getMachinePath()

    def get_platform(self):
        return 'smart_virtual'
