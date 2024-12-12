"""Test show pools."""
from mpf.tests.MpfTestCase import MpfTestCase, patch


class TestShowPools(MpfTestCase):

    def get_config_file(self):
        return 'test_show_pools.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/shows/'

    def test_pool_random(self):
        with patch("mpf.core.assets.random.randint") as rand:
            rand.return_value = 1
            self.post_event("play_pool_random")
            rand.assert_called_with(1, 4)
        self.assertIn("pool_random", self.machine.show_player.instances["_global"]["show_player"])

        self.assertEqual("leds_name_token",
                         self.machine.show_player.instances["_global"]["show_player"]["pool_random"].name)

        self.post_event("stop_pool_random")
        self.assertNotIn("pool_random", self.machine.show_player.instances["_global"]["show_player"])

        with patch("mpf.core.assets.random.randint") as rand:
            rand.return_value = 2
            self.post_event("play_pool_random")
            rand.assert_called_with(1, 4)
        self.assertIn("pool_random", self.machine.show_player.instances["_global"]["show_player"])

        self.assertEqual("leds_single_color",
                         self.machine.show_player.instances["_global"]["show_player"]["pool_random"].name)

        self.post_event("stop_pool_random")
        self.assertNotIn("pool_random", self.machine.show_player.instances["_global"]["show_player"])

        with patch("mpf.core.assets.random.randint") as rand:
            rand.return_value = 3
            self.post_event("play_pool_random")
            rand.assert_called_with(1, 4)
        self.assertIn("pool_random", self.machine.show_player.instances["_global"]["show_player"])

        self.assertEqual("leds_color_token",
                         self.machine.show_player.instances["_global"]["show_player"]["pool_random"].name)

        self.post_event("stop_pool_random")
        self.assertNotIn("pool_random", self.machine.show_player.instances["_global"]["show_player"])

        with patch("mpf.core.assets.random.randint") as rand:
            rand.return_value = 4
            self.post_event("play_pool_random")
            rand.assert_called_with(1, 4)
        self.assertIn("pool_random", self.machine.show_player.instances["_global"]["show_player"])

        self.assertEqual("leds_extended",
                         self.machine.show_player.instances["_global"]["show_player"]["pool_random"].name)
