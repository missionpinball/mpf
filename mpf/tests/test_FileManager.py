import os
import unittest
from unittest.mock import patch, MagicMock
from mpf.core.file_manager import FileManager


class TestFileManager(unittest.TestCase):
    def setUp(self):
        if not FileManager.initialized:
            FileManager.init()
        # Keep a backup of the original global yaml interface to prevent leaking mocks
        self.original_yaml_interface = FileManager.file_interfaces.get(".yaml")

    def tearDown(self):
        # Restore the original interface so later test suites don't crash
        if self.original_yaml_interface:
            FileManager.file_interfaces[".yaml"] = self.original_yaml_interface

    def test_invalid_extension(self):
        """If an invalid extension is supplied, it must throw an AssertionError."""
        if not FileManager.initialized:
            FileManager.init()
            
        with self.assertRaises(AssertionError):
            FileManager.save("test.invalid_ext", {}, False)

    @patch("os.open")
    @patch("os.fsync")
    @patch("os.close")
    @patch("os.replace")
    def test_directory_fsync_option(self, mock_replace, mock_close, mock_fsync, mock_open):
        """Verify that saving a file attempts to sync its parent directory."""
        if not FileManager.initialized:
            FileManager.init()

        # Mock a file interface so it doesn't look for an actual disk backend
        mock_interface = MagicMock()
        FileManager.file_interfaces[".yaml"] = mock_interface
        mock_open.return_value = 77  # Mock an arbitrary folder file descriptor

        # Save without fsync
        FileManager.save("test_dir/file.yaml", {}, False)

        # Verify that the parent directory path was opened, synchronized, and closed
        mock_open.assert_not_called()
        mock_fsync.assert_not_called()
        mock_close.assert_not_called()

        # Save with fsync
        FileManager.save("test_dir/file.yaml", {}, True)

        # Verify that the parent directory path was opened, synchronized, and closed
        mock_open.assert_called_once()
        mock_fsync.assert_called_once_with(77)
        mock_close.assert_called_once_with(77)

    @patch("os.open")
    @patch("os.replace")
    def test_directory_fsync_handles_windows_permission_error(self, mock_replace, mock_open):
        """Ensure the method doesn't crash if os.open raises a platform error (like on Windows)."""
        if not FileManager.initialized:
            FileManager.init()

        mock_interface = MagicMock()
        FileManager.file_interfaces[".yaml"] = mock_interface
        FileManager.log = MagicMock()

        # Simulate a Windows PermissionError/OSError when opening a directory path
        mock_open.side_effect = PermissionError(13, "Permission denied")

        # Execution should complete cleanly instead of throwing unhandled exceptions
        FileManager.save("test_dir/file.yaml", {}, True)

        # Confirm the safety path captured the issue gracefully inside the debug logs
        FileManager.log.debug.assert_called_once()
