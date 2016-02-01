from mpf.system.show_controller import Show
from tests.MpfTestCase import MpfTestCase

class TestAssetManager(MpfTestCase):

    def cb(self):
        pass

    def test_asset_loading_with_same_priority(self):
        asset_manager = next(iter(self.machine.asset_managers.values()))
        asset_manager.load_asset(Show(self.machine, dict(), "a", asset_manager), self.cb, 0)
        asset_manager.load_asset(Show(self.machine, dict(), "b", asset_manager), self.cb, 0)