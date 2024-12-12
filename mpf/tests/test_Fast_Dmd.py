# mpf.tests.test_Fast_Dmd

from mpf.tests.test_Fast import TestFastBase
from mpf.tests.MpfTestCase import test_config

class TestFastDmd(TestFastBase):
    """Tests the FAST Audio Interface boards."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.serial_connections_to_mock = ['dmd']

    def get_config_file(self):
        return 'dmd.yaml'

    def create_expected_commands(self):
            self.serial_connections['dmd'].expected_commands = dict()

    def test_dmd(self):
        # This was migrated from MPF 0.56 and has not been tested with real hardware.
        # Chances are it doesn't actually work, which should be fine because I don't
        # think anyone has these DMDs. But it should be easy to finish with a real DMD.

        pass