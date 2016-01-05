from .KmcTestCase import KmcTestCase


class TestKmcDisplays(KmcTestCase):

    def get_machine_path(self):
        return 'tests/machine_files/kmc'

    def get_config_file(self):
        return 'test_kmc_displays_single.yaml'

    def test_kmc_display(self):
        print(self.kmc.displays)
        print(self.kmc.displays['window'])
        print(self.kmc.displays['window'].size)
