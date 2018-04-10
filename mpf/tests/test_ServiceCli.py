import sys

from mpf.tests.MpfBcpTestCase import MpfBcpTestCase
from mpf.commands.service import ServiceCli
from unittest.mock import create_autospec


class TestServiceCli(MpfBcpTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/service_mode/'

    def setUp(self):
        super().setUp()
        self.mock_stdin = create_autospec(sys.stdin)
        self.mock_stdout = create_autospec(sys.stdout)
        # we are connected as anonymous client
        self._bcp_client.name = None

    def _last_write(self, n=None):
        """:return: last `n` output lines"""
        if n is None:
            return self.mock_stdout.write.call_args[0][0]
        return "".join(map(lambda c: c[0][0], self.mock_stdout.write.call_args_list[-n:]))

    def test_cli(self):
        self.maxDiff = None
        cli = ServiceCli(self._bcp_external_client, self.loop, self.mock_stdin, self.mock_stdout)

        cli.onecmd("light_color l_light5 red")
        self.assertEqual("Success\n", self._last_write())

        cli.onecmd("light_color l_light1 invalid_color")
        self.assertEqual("Error: Invalid RGB string: invalid_color\n", self._last_write())

        cli.onecmd("light_color l_light1 white")
        self.assertEqual("Success\n", self._last_write())

        cli.onecmd("list_lights")
        expected = """+---------+-----------------------------------+----------+-----------------+
| Board   | Number                            | Name     | Color           |
+---------+-----------------------------------+----------+-----------------+
| Virtual | ['led-1-b', 'led-1-g', 'led-1-r'] | l_light1 | (255, 255, 255) |
| Virtual | ['led-5-b', 'led-5-g', 'led-5-r'] | l_light5 | (255, 0, 0)     |
+---------+-----------------------------------+----------+-----------------+
"""
        self.assertEqual(expected, self._last_write())

        cli.onecmd("light_off l_light5")
        self.assertEqual("Success\n", self._last_write())

        self.assertLightColor("l_light5", "black")

        cli.onecmd("light_color l_light5")
        self.assertEqual("Success\n", self._last_write())

        self.assertLightColor("l_light5", "white")

        cli.onecmd("light_off l_light5")
        self.assertEqual("Success\n", self._last_write())

        self.assertLightColor("l_light5", "black")

        self.hit_switch_and_run("s_door_open", 0)

        cli.onecmd("list_switches")
        expected = """+---------+--------+-----------------+--------+
| Board   | Number | Name            | State  |
+---------+--------+-----------------+--------+
| Virtual | 1      | s_door_open     | closed |
| Virtual | 17     | s_service_enter | open   |
| Virtual | 18     | s_service_esc   | open   |
| Virtual | 19     | s_service_up    | open   |
| Virtual | 20     | s_service_down  | open   |
+---------+--------+-----------------+--------+
"""
        self.assertEqual(expected, self._last_write())

        cli.onecmd("list_coils")
        expected = """+---------+--------+---------+
| Board   | Number | Name    |
+---------+--------+---------+
| Virtual | 1      | c_test  |
| Virtual | 2      | c_test2 |
| Virtual | 3      | c_test5 |
| Virtual | 10     | c_test6 |
| Virtual | 100    | c_test4 |
| Virtual | 1000   | c_test3 |
+---------+--------+---------+
"""
        self.assertEqual(expected, self._last_write())

        cli.onecmd("list_shows")
        expected = """+-----------+------------------------------------+
| Name      | Token                              |
+-----------+------------------------------------+
| flash     | ['led', 'leds', 'light', 'lights'] |
| led_color | ['color', 'led', 'leds']           |
| off       | ['led', 'leds', 'light', 'lights'] |
| on        | ['led', 'leds', 'light', 'lights'] |
+-----------+------------------------------------+
"""
        self.assertEqual(expected, self._last_write())

        self.assertLightColor("l_light5", "black")

        cli.onecmd("show_play on led:l_light5")
        self.assertLightColor("l_light5", "white")

        cli.onecmd("show_stop on")
        self.assertLightColor("l_light5", "black")

        cli.onecmd("show_play led_color led:l_light5 color:red")
        self.assertLightColor("l_light5", "red")

        self.assertEqual("disabled", self.machine.coils.c_test.hw_driver.state)

        cli.onecmd("coil_pulse c_test")
        self.assertEqual("Success\n", self._last_write())
        self.assertEqual("pulsed_10", self.machine.coils.c_test.hw_driver.state)

        cli.onecmd("coil_enable c_test")
        self.assertEqual("Error: Cannot enable driver with hold_power 0.0\n", self._last_write())

        cli.onecmd("coil_enable c_test6")
        self.assertEqual("Success\n", self._last_write())
        self.assertEqual("enabled", self.machine.coils.c_test6.hw_driver.state)

        cli.onecmd("coil_disable c_test6")
        self.assertEqual("Success\n", self._last_write())
        self.assertEqual("disabled", self.machine.coils.c_test6.hw_driver.state)

        self.assertLightColor("l_light1", "white")
        self.assertLightColor("l_light5", "red")

        cli.onecmd("quit")
        self.advance_time_and_run()

        self.assertLightColor("l_light1", "black")
        self.assertLightColor("l_light5", "black")
