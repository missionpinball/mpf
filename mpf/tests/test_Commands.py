from unittest import TestCase
from unittest.mock import patch, MagicMock, call

from mpf.commands import game


class TestCommands(TestCase):

    def setUp(self) -> None:
        modules = {
            'asciimatics': MagicMock(),
        }

        self.module_patcher = patch.dict('sys.modules', modules)
        self.module_patcher.start()
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()
        self.module_patcher.stop()

    def test_game(self):
        loader_mock = MagicMock()

        with patch("mpf.commands.game.signal"):
            with patch("mpf.commands.game.logging"):
                with patch("mpf.commands.game.os"):
                    with patch("mpf.commands.game.sys") as sys:
                        with patch("mpf.commands.game.MachineController") as controller:
                            with patch("mpf.commands.game.YamlMultifileConfigLoader", return_value=loader_mock):
                                with patch("asciimatics.screen.Screen.open"):
                                    game.Command("test", "machine", "")
                                    loader_mock.load_mpf_config.assert_called_once_with()
                                    self.assertEqual(loader_mock.load_mpf_config(), controller.call_args[0][1])
                                    sys.exit.assert_called_once_with()
                                    self.assertEqual(call(), sys.exit.call_args)
