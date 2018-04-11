from unittest import TestCase
from unittest.mock import patch


from mpf.commands import game, migrate, both


class TestCommands(TestCase):

    def test_game(self):
        with patch("mpf.commands.game.signal"):
            with patch("mpf.commands.game.logging"):
                with patch("mpf.commands.game.os"):
                    with patch("mpf.commands.game.sys") as sys:
                        with patch("mpf.commands.game.MachineController") as controller:
                            with patch("asciimatics.screen.Screen.open"):
                                game.Command("test", "machine", "")
                                self.assertEqual("test", controller.call_args[0][0])
                                self.assertEqual("machine", controller.call_args[0][1])
                                sys.exit.assert_called_once_with()

    def test_migrate(self):
        with patch("mpf.commands.migrate.logging"):
            with patch("mpf.commands.migrate.os"):
                with patch("mpf.commands.migrate.Migrator") as cmd:
                    migrate.Command("test", "machine", "")
                    cmd.assert_called_with("test", "machine")
