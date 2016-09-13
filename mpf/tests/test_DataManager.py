"""Test the bonus mode."""
import time
from unittest.mock import mock_open, patch

from mpf.file_interfaces.yaml_interface import YamlInterface
from mpf.core.data_manager import DataManager
from mpf.tests.MpfTestCase import MpfTestCase


class TestDataManager(MpfTestCase):

    def setUp(self):
        super().setUp()
        YamlInterface.cache = False

    def tearDown(self):
        YamlInterface.cache = True
        super().tearDown()

    def test_save_and_load(self):
        open_mock = mock_open(read_data="")
        with patch('mpf.file_interfaces.yaml_interface.open', open_mock, create=True):
            with patch('mpf.core.file_manager.os.path.isfile') as isfile_mock:
                isfile_mock.return_value = True
                manager = DataManager(self.machine, "machine_vars")
                self.assertTrue(isfile_mock.called)
                self.assertTrue(open_mock.called)

        self.assertNotIn("hallo", manager.get_data())

        open_mock = mock_open(read_data="")
        with patch('mpf.file_interfaces.yaml_interface.open', open_mock, create=True):
            with patch('mpf.core.data_manager.os.replace') as move_mock:
                manager.save_key("hallo", "world")
                while not move_mock.called:
                    time.sleep(.00001)
                open_mock().write.assert_called_once_with('hallo: world\n')
                self.assertTrue(move_mock.called)

        open_mock = mock_open(read_data='hallo: world\n')
        with patch('mpf.file_interfaces.yaml_interface.open', open_mock, create=True):
            with patch('mpf.core.file_manager.os.path.isfile') as isfile_mock:
                isfile_mock.return_value = True
                manager2 = DataManager(self.machine, "machine_vars")
                self.assertTrue(isfile_mock.called)
                self.assertTrue(open_mock.called)

        self.assertEqual("world", manager2.get_data()["hallo"])
        self.assertEqual({}, manager.get_data("hallo"))

    def test_get_data(self):
        open_mock = mock_open(read_data='hallo:\n  test: world\n')
        with patch('mpf.file_interfaces.yaml_interface.open', open_mock, create=True):
            with patch('mpf.core.file_manager.os.path.isfile') as isfile_mock:
                manager = DataManager(self.machine, "machine_vars")
                self.assertTrue(isfile_mock.called)
                self.assertTrue(open_mock.called)

        self.assertEqual({"test": "world"}, manager.get_data("hallo"))
        self.assertEqual({}, manager.get_data("invalid"))
