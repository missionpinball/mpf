"""Test Randomizer class."""
from mpf.tests.MpfTestCase import MpfTestCase
from mpf.core.randomizer import Randomizer


class TestRandomizer(MpfTestCase):

    def get_config_file(self):
        return 'randomizer.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/randomizer/'

    def test_one_element_with_force_different(self):
        items = ['1']

        r = Randomizer(items)
        self.assertTrue(r.force_different)

        # it has one element and should thereby always return it
        self.assertEqual('1', next(r))
        self.assertEqual('1', next(r))
        self.assertEqual('1', next(r))

    def test_machine_randomizer(self):

        items = [
            '1',
            '2',
            '3',
        ]

        r = Randomizer(items)

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

        r = Randomizer(items)
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

        r = Randomizer(items)
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

        r = Randomizer(items)
        r.loop = False

        x = 0
        for _ in r:
            x += 1

        self.assertEqual(3, x)

    def test_weights(self):
        items = [
            ('1', 2),
            ('2', 1),
            ('3', 1),
        ]

        r = Randomizer(items)
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

        r = Randomizer(items)
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

        r = Randomizer(items)
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

        r = Randomizer(items)
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

            r = Randomizer(items)
            r.loop = False
            r.disable_random = True

            x = 0
            for i, result in enumerate(r):
                x += 1
                self.assertEqual(items[i][0], result)

            self.assertEqual(3, x)

    def test_fallback_value(self):

        items = []

        r = Randomizer(items)
        r.fallback_value = "foo"

        results = list()

        for x in range(100):
            results.append(next(r))

        self.assertEqual(100, results.count('foo'))