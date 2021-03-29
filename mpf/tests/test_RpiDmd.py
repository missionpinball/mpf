from mpf.tests.MpfTestCase import MpfTestCase, MagicMock, patch


class TestRpiDmd(MpfTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/rpi_dmd/'

    def get_platform(self):
        # no force platform.
        return False

    def setUp(self):
        modules = {
            'PIL': MagicMock(),
            'PIL.Image': MagicMock(),
        }
        self.module_patcher = patch.dict('sys.modules', modules)
        self.module_patcher.start()
        Image = patch('mpf.platforms.rpi_dmd.Image')
        self.image = Image.start()

        RGBMatrix = patch('mpf.platforms.rpi_dmd.RGBMatrix')
        RGBMatrixOptions = patch('mpf.platforms.rpi_dmd.RGBMatrixOptions')
        self.rgbmatrixoptions = RGBMatrixOptions.start()
        self.rgbmatrix = RGBMatrix.start()
        self.rgbmatrix_instance = MagicMock()
        self.rgbmatrix.return_value = self.rgbmatrix_instance
        self.addCleanup(self.rgbmatrix.stop)
        super().setUp()

    def tearDown(self):
        self.module_patcher.stop()
        super().tearDown()

    def test_rpi_dmd(self):
        data = bytes([0x02] * 32 * 32 * 3)
        self.machine.rgb_dmds["rpi_dmd"].update(data)
        self.advance_time_and_run(.1)

        self.assertTrue(len(self.rgbmatrix_instance.SetImage.mock_calls) > 0)
        last_call = self.rgbmatrix_instance.SetImage.mock_calls[1]
        frombytes_call = last_call[1][0]
        frombytes_arg = frombytes_call.mock_calls[0][1][0]
        self.assertEqual(data, frombytes_arg)
