from mpf._version import log_url

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
                         'Config File Error in show: "broken_show" >> Invalid section "light_player:" '
                         'found. Did you mean "lights:" instead? Context: broken_show '
                         'Error Code: CFE-show-3 ({})'.format(log_url.format("CFE-show-3")))
        self.loop.close()
