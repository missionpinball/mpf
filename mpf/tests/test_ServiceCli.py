import sys

from mpf.tests.MpfBcpTestCase import MpfBcpTestCase
from mpf.commands.service import ServiceCli
from unittest.mock import create_autospec


class TestServiceCli(MpfBcpTestCase):


    def setUp(self):
        super().setUp()
        self.mock_stdin = create_autospec(sys.stdin)
        self.mock_stdout = create_autospec(sys.stdout)

    def test_cli(self):
        cli = ServiceCli(self._bcp_external_client, self.loop, self.mock_stdin, self.mock_stdout)
        cli.onecmd("list_lights")
        self.mock_stdout.write.assert_called_with('+-------+--------+------+-------+\n| Board | Number | Name | Color |\n+-------+--------+------+-------+\n')
