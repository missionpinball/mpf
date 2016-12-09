from mpf.tests.MpfGameTestCase import MpfGameTestCase


class TestPlayerVars(MpfGameTestCase):

    def getConfigFile(self):
        return 'player_vars.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/player_vars/'

    def test_initial_values(self):
        self.fill_troughs()
        self.start_two_player_game()

        for x in range(2):

            self.assertEqual(self.machine.game.player_list[x].some_var, 4)
            self.assertEqual(type(self.machine.game.player_list[x].some_var), int)

            self.assertEqual(self.machine.game.player_list[x].some_float, 4.0)
            self.assertEqual(type(self.machine.game.player_list[x].some_float), float)

            self.assertEqual(self.machine.game.player_list[x].some_string, '4')
            self.assertEqual(type(self.machine.game.player_list[x].some_string), str)

            self.assertEqual(self.machine.game.player_list[x].some_other_string, 'hello')
            self.assertEqual(type(self.machine.game.player_list[x].some_other_string), str)
