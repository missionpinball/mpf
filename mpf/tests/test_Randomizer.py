"""Test Randomizer class"""
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase
from mpf.tests.MpfTestCase import MpfTestCase
from mpf.core.randomizer import Randomizer


class TestRandomizer(MpfFakeGameTestCase, MpfTestCase):

    def getConfigFile(self):
        return 'randomizer.yaml'

    def getMachinePath(self):
        return 'tests/machine_files/randomizer/'

    def test_machine_randomizer(self):

        items = [
            ('1', 1),
            ('2', 1),
            ('3', 1),
        ]

        r = Randomizer(self.machine, items, 'machine')

        results = list()

        for x in range(10000):
            results.append(next(r))

        self.assertAlmostEqual(3333, results.count('1'), delta=500)
        self.assertAlmostEqual(3333, results.count('2'), delta=500)
        self.assertAlmostEqual(3333, results.count('3'), delta=500)

    def test_force_different(self):

        items = [
            ('1', 1),
            ('2', 1),
            ('3', 1),
        ]

        r = Randomizer(self.machine, items, 'machine')
        r.force_different = True

        last_item = None
        for x in range(1000):
            this_item = next(r)
            self.assertNotEqual(this_item, last_item)
            last_item = this_item

    def test_force_all(self):

        items = [
            ('1', 1),
            ('2', 1),
            ('3', 1),
        ]

        r = Randomizer(self.machine, items, 'machine')
        r.force_all = True

        last_item = None
        for x in range(100):
            results = set()
            results.add(next(r))
            self.assertNotEqual(last_item, r.get_current())
            results.add(next(r))
            results.add(next(r))
            last_item = r.get_current()
            self.assertEqual(len(results), 3)

    def test_no_loop(self):

        items = [
            ('1', 1),
            ('2', 1),
            ('3', 1),
        ]

        r = Randomizer(self.machine, items, 'machine')
        r.loop = False

        x = 0
        for _ in r:
            x += 1

        self.assertEqual(3, x)

    def test_player_memory(self):

        items = [
            ('1', 1),
            ('2', 1),
            ('3', 1),
        ]

        # make sure we can instantiate the randomizer before we have players
        r = Randomizer(self.machine, items, 'player')
        r.force_all = True

        # should raise this error if there's no player
        with self.assertRaises(AssertionError):
            next(r)

        for _ in range(50):

            p1_items = list()
            p2_items = list()

            self.start_game()

            p1_items.append(next(r))
            p1_items.append(next(r))

            # add a second player
            self.add_player()
            self.drain_ball()

            self.assertEqual(self.machine.game.player.number, 2)

            p2_items.append(next(r))
            p2_items.append(next(r))

            self.drain_ball()

            self.assertNotIn(next(r), p1_items)

            self.drain_ball()

            self.assertNotIn(next(r), p2_items)

            self.stop_game()

    def test_weights(self):
        items = [
            ('1', 2),
            ('2', 1),
            ('3', 1),
        ]

        r = Randomizer(self.machine, items, 'machine')
        r.force_different = False

        results = list()

        for x in range(10000):
            results.append(next(r))

        self.assertAlmostEqual(5000, results.count('1'), delta=500)
        self.assertAlmostEqual(2500, results.count('2'), delta=500)
        self.assertAlmostEqual(2500, results.count('3'), delta=500)

        items = [
            ('1', 1),
            ('2', 1),
            ('3', 3),
        ]

        r = Randomizer(self.machine, items, 'machine')
        r.force_different = False

        results = list()

        for x in range(10000):
            results.append(next(r))

        self.assertAlmostEqual(2000, results.count('1'), delta=500)
        self.assertAlmostEqual(2000, results.count('2'), delta=500)
        self.assertAlmostEqual(6000, results.count('3'), delta=500)

        items = [
            ('1', 1),
            ('2', 6),
            ('3', 3),
        ]

        r = Randomizer(self.machine, items, 'machine')
        r.force_different = False

        results = list()

        for x in range(10000):
            results.append(next(r))

        self.assertAlmostEqual(1000, results.count('1'), delta=500)
        self.assertAlmostEqual(6000, results.count('2'), delta=500)
        self.assertAlmostEqual(3000, results.count('3'), delta=500)

    def test_loop_no_random(self):

        items = [
            ('1', 1),
            ('2', 1),
            ('3', 1),
        ]

        r = Randomizer(self.machine, items, 'machine')
        r.disable_random = True

        for i1 in range(50):
            self.assertEqual(next(r), '1')
            self.assertEqual(next(r), '2')
            self.assertEqual(next(r), '3')

    def test_no_loop_no_random(self):

        items = [
            ('1', 1),
            ('2', 1),
            ('3', 1),
        ]

        for _ in range(50):

            r = Randomizer(self.machine, items, 'machine')
            r.loop = False
            r.disable_random = True

            x = 0
            for i, result in enumerate(r):
                x += 1
                self.assertEqual(items[i][0], result)

            self.assertEqual(3, x)