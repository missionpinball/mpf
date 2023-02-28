"""Test the bonus mode."""
import os
import time
from unittest.mock import mock_open, patch

from mpf.file_interfaces.yaml_interface import YamlInterface
from mpf.core.data_manager import DataManager
from mpf.tests.MpfTestCase import MpfTestCase


class TestDataManager(MpfTestCase):

    def get_config_file(self):
        return "config.yaml"

    def get_machine_path(self):
        return 'tests/machine_files/data_manager/'

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
                manager = DataManager(self.machine, "machine_vars", min_wait_secs=0)
                self.assertTrue(isfile_mock.called)
                self.assertTrue(open_mock.called)

        self.assertNotIn("hallo", manager.get_data())

        open_mock = mock_open(read_data="")
        with patch('mpf.file_interfaces.yaml_interface.open', open_mock, create=True):
            with patch('mpf.core.data_manager.os.replace') as move_mock:
                manager.save_all({"hallo": "world"})
                while not move_mock.called:
                    time.sleep(.00001)
                expected_output = "hallo: world\n"
                output = ''.join([res[0][0] for res in open_mock().write.call_args_list])
                self.assertEqual(output, expected_output)
                self.assertTrue(move_mock.called)

        open_mock = mock_open(read_data='hallo: world\n')
        with patch('mpf.file_interfaces.yaml_interface.open', open_mock, create=True):
            with patch('mpf.core.file_manager.os.path.isfile') as isfile_mock:
                isfile_mock.return_value = True
                manager2 = DataManager(self.machine, "machine_vars", min_wait_secs=0)
                self.assertTrue(isfile_mock.called)
                self.assertTrue(open_mock.called)

        self.assertEqual("world", manager2.get_data()["hallo"])
        self.assertEqual({}, manager.get_data("hallo"))

    def test_get_data(self):
        open_mock = mock_open(read_data='hallo:\n  test: world\n')
        with patch('mpf.file_interfaces.yaml_interface.open', open_mock, create=True):
            with patch('mpf.core.file_manager.os.path.isfile') as isfile_mock:
                manager = DataManager(self.machine, "machine_vars", min_wait_secs=0)
                self.assertTrue(isfile_mock.called)
                self.assertTrue(open_mock.called)

        self.assertEqual({"test": "world"}, manager.get_data("hallo"))
        self.assertEqual({}, manager.get_data("invalid"))

    def test_paths_and_disable(self):
        open_mock = mock_open(read_data='hallo:\n  test: world\n')
        with patch('mpf.file_interfaces.yaml_interface.open', open_mock, create=True):
            with patch('mpf.core.file_manager.os.path.isfile') as isfile_mock:
                with patch('mpf.core.file_manager.os.mkdir') as mkdir_mock:
                    manager = DataManager(self.machine, "absolute_test", min_wait_secs=0)
                    isfile_mock.assert_called_with('/data/test_dir/test_file.yaml')
                    mkdir_mock.assert_called_with('/data/test_dir', 511)
                    open_mock.assert_called_once_with('/data/test_dir/test_file.yaml', encoding='utf8')

        self.assertEqual({"test": "world"}, manager.get_data("hallo"))
        self.assertEqual({}, manager.get_data("invalid"))

        open_mock = mock_open(read_data='hallo:\n  test: world\n')
        with patch('mpf.file_interfaces.yaml_interface.open', open_mock, create=True):
            with patch('mpf.core.file_manager.os.path.isfile') as isfile_mock:
                with patch('mpf.core.file_manager.os.mkdir') as mkdir_mock:
                    manager = DataManager(self.machine, "relative_test", min_wait_secs=0)
                    path = os.path.join(os.path.abspath(self.machine.machine_path), 'subdir/subdir2')
                    file_path = os.path.join(os.path.abspath(self.machine.machine_path), 'subdir/subdir2/test.yaml')
                    isfile_mock.assert_called_with(file_path)
                    mkdir_mock.assert_called_with(path, 511)
                    open_mock.assert_called_once_with(file_path, encoding='utf8')

        self.assertEqual({"test": "world"}, manager.get_data("hallo"))
        self.assertEqual({}, manager.get_data("invalid"))
        open_mock = mock_open(read_data='hallo:\n  test: world\n')
        with patch('mpf.file_interfaces.yaml_interface.open', open_mock, create=True):
            with patch('mpf.core.file_manager.os.path.isfile') as isfile_mock:
                with patch('mpf.core.file_manager.os.mkdir') as mkdir_mock:
                    manager = DataManager(self.machine, "disabled_test", min_wait_secs=0)
                    self.assertFalse(isfile_mock.called)
                    self.assertFalse(mkdir_mock.called)
                    self.assertFalse(open_mock.called)

        self.assertEqual({}, manager.get_data("hallo"))
        self.assertEqual({}, manager.get_data("invalid"))
