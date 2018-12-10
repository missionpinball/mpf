import asyncio

from PIL import Image

from mpf.tests.MpfTestCase import MpfTestCase, MagicMock, patch


class TestRpiDmd(MpfTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/rpi_dmd/'

    def get_platform(self):
        # no force platform.
        return False

    def setUp(self):
        RGBMatrix = patch('mpf.platforms.rpi_dmd.RGBMatrix')
        RGBMatrixOptions = patch('mpf.platforms.rpi_dmd.RGBMatrixOptions')
        self.rgbmatrixoptions = RGBMatrixOptions.start()
        self.rgbmatrix = RGBMatrix.start()
        self.rgbmatrix_instance = MagicMock()
        self.rgbmatrix.return_value = self.rgbmatrix_instance
        self.addCleanup(self.rgbmatrix.stop)
        super().setUp()

    def test_rpi_dmd(self):
        data = bytes([0x00] * 32 * 32 * 3)
        self.machine.rgb_dmds.rpi_dmd.update(data)
        self.advance_time_and_run(.1)

        image = Image.frombytes("RGB", (32, 32), b'\x11' * 32 * 32 * 3)
        image.frombytes(data)
        self.rgbmatrix_instance.SetImage.assert_called_with(image)
