"""Test assets."""
import time
from mpf.tests.MpfTestCase import MpfTestCase


class TestAssets(MpfTestCase):
    def getMachinePath(self):
        return 'tests/machine_files/asset_manager'

    def getConfigFile(self):
        return 'test_asset_loading.yaml'

    def test_asset_loading(self):
        # TODO: instantiate a fresh machine between test groups
        self.expected_duration = 1.5
        self._test_machine_wide_asset_loading()
        self._test_random_asset_group()
        self._test_random_asset_group_with_weighting()
        self._test_random_force_all()
        self._test_random_force_next()
        self._test_sequence_asset_group()
        self._test_sequence_asset_group_with_count()
        self._test_conditional_random_asset_group()
        self._test_conditional_sequence_asset_group()

    def _test_machine_wide_asset_loading(self):

        # test that the shows asset class gets built correctly
        self.assertTrue(self.machine, 'shows')
        self.assertTrue(self.machine.asset_manager._asset_classes)
        self.assertEqual(self.machine.asset_manager._asset_classes[0].path_string, 'shows')

        # tests that assets are registered as expected with various conditions

        # /shows folder
        self.assertIn('show1', self.machine.shows)
        self.assertIn('show2', self.machine.shows)
        self.assertIn('show3', self.machine.shows)

        # test subfolders listed in assets:shows machine-wide config folders
        self.assertIn('show4', self.machine.shows)  # /shows/preload
        self.assertIn('show4b', self.machine.shows)  # /shows/preload/subfolder
        self.assertIn('show5', self.machine.shows)  # /shows/on_demand

        # test shows from subfolder not listed in assets:shows
        self.assertIn('show11', self.machine.shows)  # /shows/custom1

        # test shows from the shows: section that have names configured to be
        # different from their file names
        self.assertIn('show_12_new_name', self.machine.shows)  # show12.png
        # custom1/show13.png
        self.assertIn('show_13_new_name', self.machine.shows)

        # test that the shows that were renamed were not also loaded based on
        # their original names
        self.assertNotIn('show12', self.machine.shows)
        self.assertNotIn('show13', self.machine.shows)

        # test that config dicts are merged and/or overwritten properly

        # test custom k/v pair from default config based on the folder the
        # asset was in
        self.assertEqual(self.machine.shows['show4'].config['test_key'],
                         'test_value')

        # test custom k/v pair from default config based on the folder the
        # asset was in (custom pair should be inherited from parent folder)
        self.assertEqual(self.machine.shows['show4b'].config['test_key'],
                         'test_value')

        # test custom k/v pair from asset entry in the shows: section
        self.assertEqual(self.machine.shows['show3'].config['test_key'],
                         'test_value_override3')

        # same as above, but test that it also works when the asset name is
        # different from the file name
        self.assertEqual(self.machine.shows['show_12_new_name'].config['test_key'], 'test_value_override12')

        # Test that mode assets were loaded properly
        self.assertIn('show6', self.machine.shows)
        self.assertIn('show7', self.machine.shows)
        self.assertIn('show8', self.machine.shows)
        self.assertIn('show9', self.machine.shows)
        self.assertIn('show10', self.machine.shows)

        # Make sure all the assets are loaded. Wait if not
        while (self.machine.asset_manager.num_assets_to_load <
               self.machine.asset_manager.num_assets_loaded):
            time.sleep(.0001)
            self.advance_time_and_run(.1)

        # Need to wait a bit since the loading was a separate thread
        self.advance_time_and_run(.1)

        # Make sure the ones that should have loaded on startup actually loaded
        self.assertTrue(self.machine.shows['show1'].loaded)
        self.assertFalse(self.machine.shows['show1'].loading)
        self.assertFalse(self.machine.shows['show1'].unloading)

        self.assertTrue(self.machine.shows['show2'].loaded)
        self.assertFalse(self.machine.shows['show2'].loading)
        self.assertFalse(self.machine.shows['show2'].unloading)

        self.assertTrue(self.machine.shows['show3'].loaded)
        self.assertFalse(self.machine.shows['show3'].loading)
        self.assertFalse(self.machine.shows['show3'].unloading)

        self.assertTrue(self.machine.shows['show8'].loaded)
        self.assertFalse(self.machine.shows['show8'].loading)
        self.assertFalse(self.machine.shows['show8'].unloading)

        self.assertTrue(self.machine.shows['show2'].loaded)
        self.assertFalse(self.machine.shows['show2'].loading)
        self.assertFalse(self.machine.shows['show2'].unloading)

        self.assertTrue(self.machine.shows['show4'].loaded)
        self.assertFalse(self.machine.shows['show4'].loading)
        self.assertFalse(self.machine.shows['show4'].unloading)

        self.assertTrue(self.machine.shows['show7'].loaded)
        self.assertFalse(self.machine.shows['show7'].loading)
        self.assertFalse(self.machine.shows['show7'].unloading)

        self.assertTrue(self.machine.shows['show11'].loaded)
        self.assertFalse(self.machine.shows['show11'].loading)
        self.assertFalse(self.machine.shows['show11'].unloading)

        self.assertTrue(self.machine.shows['show_12_new_name'].loaded)
        self.assertFalse(self.machine.shows['show_12_new_name'].loading)
        self.assertFalse(self.machine.shows['show_12_new_name'].unloading)

        self.assertTrue(self.machine.shows['show_13_new_name'].loaded)
        self.assertFalse(self.machine.shows['show_13_new_name'].loading)
        self.assertFalse(self.machine.shows['show_13_new_name'].unloading)

        # Make sure the ones that should not have loaded on startup didn't load
        self.assertFalse(self.machine.shows['show5'].loaded)
        self.assertFalse(self.machine.shows['show5'].loading)
        self.assertFalse(self.machine.shows['show5'].unloading)

        self.assertFalse(self.machine.shows['show9'].loaded)
        self.assertFalse(self.machine.shows['show9'].loading)
        self.assertFalse(self.machine.shows['show9'].unloading)

        self.assertFalse(self.machine.shows['show10'].loaded)
        self.assertFalse(self.machine.shows['show10'].loading)
        self.assertFalse(self.machine.shows['show10'].unloading)

        # Start the mode and make sure those assets load
        self.mock_event("loading_assets")
        self.mock_event("asset_loading_complete")
        self.machine.modes['mode1'].start()
        self.advance_time_and_run()

        # Give it a second to load. This file is tiny, so it shouldn't take
        # this long

        start_time = time.time()
        while (not self.machine.shows['show9'].loaded and
                time.time() < start_time + 5):
            self.assertTrue(self.machine.shows['show9'].loading)
            time.sleep(.0001)
            self.advance_time_and_run(.1)

        self.assertEventCalled("loading_assets")
        self.assertEventCalled("asset_loading_complete")

        self.assertTrue(self.machine.shows['show9'].loaded)
        self.assertFalse(self.machine.shows['show9'].loading)
        self.assertFalse(self.machine.shows['show9'].unloading)

        # test mode stop which should unload those assets
        self.machine.modes['mode1'].stop()
        self.advance_time_and_run(.1)

        start_time = time.time()
        while (self.machine.shows['show9'].loaded and
                time.time() < start_time + 5):
            self.assertTrue(self.machine.shows['show9'].unloading)
            time.sleep(.0001)
            self.advance_time_and_run(.1)

        self.assertFalse(self.machine.shows['show9'].loaded)
        self.assertFalse(self.machine.shows['show9'].loading)
        self.assertFalse(self.machine.shows['show9'].unloading)

    def _test_random_asset_group(self):
        # three assets, no weights

        # make sure the asset group was created
        self.assertIn('group1', self.machine.shows)

        # make sure the randomness is working. To test this, we request the
        # asset 10,000 times and then count the results and assume that each
        # should be 3,333 +- 500 just to make sure the test never fails/
        res = list()
        for x in range(10000):
            res.append(self.machine.shows['group1'].show)

        self.assertAlmostEqual(3333, res.count(self.machine.shows['show1']),
                               delta=500)
        self.assertAlmostEqual(3333, res.count(self.machine.shows['show2']),
                               delta=500)
        self.assertAlmostEqual(3333, res.count(self.machine.shows['show3']),
                               delta=500)

    def _test_random_asset_group_with_weighting(self):
        # three assets, third one has a weight of 2

        # make sure the asset group was created
        self.assertIn('group2', self.machine.shows)

        # make sure the randomness is working. To test this, we request the
        # asset 10,000 times and then count the results and assume that each
        # should be 3,333 +- 500 just to make sure the test never fails/
        res = list()
        for x in range(10000):
            res.append(self.machine.shows['group2'].show)

        self.assertAlmostEqual(2500, res.count(self.machine.shows['show1']),
                               delta=500)
        self.assertAlmostEqual(2500, res.count(self.machine.shows['show2']),
                               delta=500)
        self.assertAlmostEqual(5000, res.count(self.machine.shows['show3']),
                               delta=500)

    def _test_sequence_asset_group(self):
        # three assets, no weights

        self.assertIn('group3', self.machine.shows)

        # Should always return in order, 1, 2, 3, 1, 2, 3...
        self.assertIs(self.machine.shows['group3'].show, self.machine.shows['show1'])
        self.assertIs(self.machine.shows['group3'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group3'].show, self.machine.shows['show3'])
        self.assertIs(self.machine.shows['group3'].show, self.machine.shows['show1'])
        self.assertIs(self.machine.shows['group3'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group3'].show, self.machine.shows['show3'])
        self.assertIs(self.machine.shows['group3'].show, self.machine.shows['show1'])
        self.assertIs(self.machine.shows['group3'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group3'].show, self.machine.shows['show3'])

    def _test_sequence_asset_group_with_count(self):
        # three assets, no weights

        self.assertIn('group4', self.machine.shows)

        # Should always return in order, 1, 1, 1, 1, 2, 2, 3, 1, 1, 1, 1 ...
        self.assertIs(self.machine.shows['group4'].show, self.machine.shows['show1'])
        self.assertIs(self.machine.shows['group4'].show, self.machine.shows['show1'])
        self.assertIs(self.machine.shows['group4'].show, self.machine.shows['show1'])
        self.assertIs(self.machine.shows['group4'].show, self.machine.shows['show1'])
        self.assertIs(self.machine.shows['group4'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group4'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group4'].show, self.machine.shows['show3'])
        self.assertIs(self.machine.shows['group4'].show, self.machine.shows['show1'])
        self.assertIs(self.machine.shows['group4'].show, self.machine.shows['show1'])
        self.assertIs(self.machine.shows['group4'].show, self.machine.shows['show1'])
        self.assertIs(self.machine.shows['group4'].show, self.machine.shows['show1'])
        self.assertIs(self.machine.shows['group4'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group4'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group4'].show, self.machine.shows['show3'])

    def _test_random_force_next(self):
        # random, except it ensures the same one does not show up twice in a
        # row

        self.assertIn('group5', self.machine.shows)

        # do it 10,000 times just to be sure. :)
        last = self.machine.shows['group5'].show
        res = list()

        for x in range(10000):
            show = self.machine.shows['group5'].show
            self.assertIsNot(last, show)
            last = show

            res.append(show)

        # Also check that the weights were right

        # BTW these weights are non-intuitive since the last asset is not
        # considered for the next round. e.g. show1 = 1, show2 = 5,
        # show3 = 1, so you'd think they would be 1400, 7200, 1400, but in
        # reality, 50% of the time, asset2 is not in contention, so really
        # asset2 has a 6-to-1 (84%) chance of being selected 66% of the time,
        # but a 0% chance of being selected 33% of the time, etc. So trust that
        # these numbers are right. :)
        self.assertAlmostEqual(2733, res.count(self.machine.shows['show1']),
                               delta=500)
        self.assertAlmostEqual(4533, res.count(self.machine.shows['show2']),
                               delta=500)
        self.assertAlmostEqual(2733, res.count(self.machine.shows['show3']),
                               delta=500)

    def _test_random_force_all(self):
        # random, except it ensures the same one does not show up twice before
        # they're all shown

        self.assertIn('group6', self.machine.shows)

        for x in range(1000):
            this_set = set()
            this_set.add(self.machine.shows['group6'].show)
            this_set.add(self.machine.shows['group6'].show)
            this_set.add(self.machine.shows['group6'].show)

            self.assertEqual(len(this_set), 3)

    def _test_conditional_random_asset_group(self):

        # make sure the asset group was created
        self.assertIn('group1', self.machine.shows)

        # ONE valid show
        # Request the show 1,000 times and ensure that only one show was picked
        res = list()
        for x in range(1000):
            res.append(self.machine.shows['group7'].show)

        self.assertEqual(1000, res.count(self.machine.shows['show1']))
        self.assertEqual(0, res.count(self.machine.shows['show2']))
        self.assertEqual(0, res.count(self.machine.shows['show3']))

        # TWO valid shows
        # Request the show 10,000 times and ensure that two shows are fairly split
        self.machine.modes.mode1.start()
        self.advance_time_and_run()
        res = list()
        for x in range(10000):
            res.append(self.machine.shows['group7'].show)

        self.assertAlmostEqual(5000, res.count(self.machine.shows['show1']),
                               delta=250)
        self.assertAlmostEqual(5000, res.count(self.machine.shows['show2']),
                               delta=250)
        self.assertEqual(0, res.count(self.machine.shows['show3']))

        # THREE valid shows
        # Request the show 10,000 times and ensure that all three shows are fairly split
        self.machine.modes.mode1.stop()
        res = list()
        for x in range(10000):
            res.append(self.machine.shows['group7'].show)

        self.assertAlmostEqual(3333, res.count(self.machine.shows['show1']),
                               delta=250)
        self.assertAlmostEqual(3333, res.count(self.machine.shows['show2']),
                               delta=250)
        self.assertAlmostEqual(3333, res.count(self.machine.shows['show3']),
                               delta=250)

    def _test_conditional_sequence_asset_group(self):
        # These tests are not independent, and mode1 is still running/stopping from the above test :(
        self.advance_time_and_run()
        self.assertIn('group8', self.machine.shows)

        # ONE valid show
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show2'])

        # TWO valid shows
        self.machine.modes.mode1.start()
        self.advance_time_and_run()
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show1'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show1'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show1'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show1'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show2'])
        
        # THREE valid shows
        self.machine.modes.mode1.stop()
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show3'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show1'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show3'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show1'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show3'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show1'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show2'])
        self.assertIs(self.machine.shows['group8'].show, self.machine.shows['show3'])
                        
