import os

from mpf.tests.MpfTestCase import MpfTestCase, test_config, test_config_directory


class TestConfigErrors(MpfTestCase):

    def setUp(self):
        self.save_and_prepare_sys_path()

    def tearDown(self):
        self.restore_sys_path()

    @test_config_directory("tests/machine_files/config_errors/broken_show")
    @test_config("show.yaml")
    def test_show_player_in_show(self):
        with self.assertRaises(AssertionError) as e:
            super().setUp()
            self.post_event("play_broken_show")

        self.assertEqual(str(e.exception),
                         'Show {}: Invalid section "light_player:" found in show broken_show. '
                         'Did you mean "lights:" instead?'.format(os.path.join(self.get_absolute_machine_path(),
                                                                               "shows", "broken_show.yaml"))
                         )
        self.loop.close()