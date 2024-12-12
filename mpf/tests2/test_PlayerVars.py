from mpf.tests.MpfGameTestCase import MpfGameTestCase


class TestPlayerVars(MpfGameTestCase):

    def get_config_file(self):
        return 'player_vars.yaml'

    def get_machine_path(self):
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

        self.machine.game.player.test = 7
        self.assertEqual(7, self.machine.game.player.test)
        self.assertEqual(7, self.machine.game.player.vars["test"])

        self.assertEqual(4, self.machine.variables.get_machine_var("test1"))
        self.assertEqual('5', self.machine.variables.get_machine_var("test2"))

    def test_event_kwargs(self):
        self.fill_troughs()
        self.start_game()
        self.assertEqual(self.machine.game.player.some_var, 4)

        self.mock_event('player_some_var')
        self.machine.game.player.add_with_kwargs('some_var', 6, foo='bar')
        self.advance_time_and_run()
        self.assertEventCalledWith('player_some_var',
                                    value=10,
                                    prev_value=4,
                                    change=6,
                                    player_num=1,
                                    foo='bar')

        self.machine.game.player.set_with_kwargs('some_var', 1, bar='foo')
        self.advance_time_and_run()
        self.assertEventCalledWith('player_some_var',
                                    value=1,
                                    prev_value=10,
                                    change=-9,
                                    player_num=1,
                                    bar='foo')
