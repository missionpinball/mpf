"""Test Randomizer class."""
from mpf.tests.MpfTestCase import MpfTestCase
from mpf.core.randomizer import Randomizer

def standard_items():
    return [
        ('1', 1),
        ('2', 1),
        ('3', 1)
    ]

class TestRandomizer(MpfTestCase):
    def get_config_file(self):
        return 'randomizer.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/randomizer/'

    def test_one_element_with_force_different(self):
        r = Randomizer(['1'], self.machine)
        self.assertTrue(r.force_different)

        # it has one element and should thereby always return it
        self.assertEqual('1', next(r))
        self.assertEqual('1', next(r))
        self.assertEqual('1', next(r))

    def test_machine_randomizer(self):
        # no weights given case
        r = Randomizer(['1', '2', '3'], self.machine)

        results = list()
        for x in range(10000):
            results.append(next(r))

        self.assertAlmostEqual(3333, results.count('1'), delta=500)
        self.assertAlmostEqual(3333, results.count('2'), delta=500)
        self.assertAlmostEqual(3333, results.count('3'), delta=500)

    def test_force_different(self):
        r = Randomizer(standard_items(), self.machine)
        r.force_different = True

        last_item = None
        for x in range(1000):
            this_item = next(r)
            self.assertNotEqual(this_item, last_item)
            last_item = this_item

    def test_force_all(self):
        r = Randomizer(standard_items(), self.machine)
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
        r = Randomizer(standard_items(), self.machine)
        r.loop = False

        x = 0
        for _ in r:
            x += 1

        self.assertEqual(3, x) # enumeration terminates after three

    def test_loop(self):
        r = Randomizer(standard_items(), self.machine)
        r.loop = True

        x = 0
        for _ in r:
            x += 1
            if x >= 50:
                break

        self.assertEqual(50, x) # enumeration will never terminate

    def test_loop_no_random(self):
        r = Randomizer(standard_items(), self.machine)
        r.disable_random = True

        for i1 in range(50):
            self.assertEqual(next(r), '1')
            self.assertEqual(next(r), '2')
            self.assertEqual(next(r), '3')

    def test_no_loop_no_random(self):
        items = standard_items()
        for _ in range(50):
            r = Randomizer(items, self.machine)
            r.loop = False
            r.disable_random = True

            x = 0
            for i, result in enumerate(r):
                x += 1
                self.assertEqual(items[i][0], result)

            self.assertEqual(3, x) # enumeration terminates after three

    def test_conditionals(self):
        # Case 1 - generally working
        r = Randomizer(
            [
                '1{True}',
                '2{False}',
                '3{2 == 1+1}',
                '4{1 == "whatever"}',
            ],
            self.machine,
            template_type="event"
        )
        r.force_different = False

        results = list()
        for x in range(100):
            results.append(next(r))

        self.assertAlmostEqual(50, results.count('1'), delta=20)
        self.assertEqual(0, results.count('2'))
        self.assertAlmostEqual(50, results.count('3'), delta=20)
        self.assertEqual(0, results.count('4'))

        # Case 2 - conditional items can have weights
        r = Randomizer(
            [
                ('1{True}', 2),
                ('2{False}', 50),
                ('3{2 == 1+1}', 1),
            ],
            self.machine,
            template_type="event"
        )
        r.force_different = False

        results = list()
        for x in range(100):
            results.append(next(r))

        self.assertAlmostEqual(67, results.count('1'), delta=20)
        self.assertEqual(0, results.count('2'))
        self.assertAlmostEqual(33, results.count('3'), delta=20)

    def test_conditionals_no_random(self):
        # conditionals should loop consistently while all continue to resolve in order
        r = Randomizer([
                '1{True}',
                '2{False}',
                '3{2 == 1+1}',
                '4{1 == "whatever"}',
            ],
                self.machine,
                template_type="event"
        )
        r.disable_random = True

        for i in range(50):
            self.assertEqual(next(r), '1')
            self.assertEqual(next(r), '3')

    def test_conditionals_dynamic_updating_no_random(self):
        # conditionals should loop properly when conditional values change between draws
        self.machine.variables.set_machine_var('foo', 1)
        r = Randomizer([
                '1{machine.foo == 0}',
                '2{machine.foo == 1}',
                '3{machine.foo == 0}',
                '4{machine.foo == 1}',
            ],
                self.machine,
                template_type="event"
        )
        r.disable_random = True

        for i in range(50):
            self.assertEqual(next(r), '2')
            self.assertEqual(next(r), '4')

        self.machine.variables.set_machine_var('foo', 0)
        for i in range(50):
            self.assertEqual(next(r), '1')
            self.assertEqual(next(r), '3')

    def test_fallback_value(self):
        # This feature is intended for cases where conditional items all drop out of validity

        # Case 1 - no items at all falls back always
        r = Randomizer([], self.machine)
        r.fallback_value = "foo"

        results = list()
        for x in range(10):
            results.append(next(r))

        self.assertEqual(10, results.count('foo'))

        # Case 2 - looping never falls back
        r = Randomizer(['1', '2'], self.machine)
        r.loop = True
        r.force_all
        r.fallback_value = "foo"

        results = list()
        for x in range(100):
            results.append(next(r))

        self.assertEqual(50, results.count('1'))
        self.assertEqual(50, results.count('2'))
        self.assertEqual(0, results.count('foo'))

    def test_weights(self):
        # Case 1 - double-weight to one option skews true random draws
        items = [
            ('1', 2), # 50% share
            ('2', 1),
            ('3', 1),
        ]
        r = Randomizer(items, self.machine)
        r.force_different = False

        results = list()
        for x in range(10000):
            results.append(next(r))

        self.assertAlmostEqual(5000, results.count('1'), delta=500)
        self.assertAlmostEqual(2500, results.count('2'), delta=500)
        self.assertAlmostEqual(2500, results.count('3'), delta=500)

        # Case 2 - many items can have weights, and floating point weights round down
        items = [
            ('0', 0.9),
            ('1', 1.3),
            ('2', 6),
            ('3', 3),
        ]

        r = Randomizer(items, self.machine)
        r.force_different = False

        results = list()
        for x in range(10000):
            results.append(next(r))

        self.assertAlmostEqual(1000, results.count('1'), delta=150)
        self.assertAlmostEqual(6000, results.count('2'), delta=300)
        self.assertAlmostEqual(3000, results.count('3'), delta=250)
        self.assertEqual(0, results.count('0'))

        # Case 3 - force all being true causes even usage
        # (the weights only control the ordering within a set)
        items = [
            ('1', 2), # 50% share
            ('2', 1),
            ('3', 1),
        ]

        r = Randomizer(items, self.machine)
        r.force_all = True

        results = list()
        for x in range(10000):
            results.append(next(r))

        self.assertAlmostEqual(3334, results.count('1'), delta=10)
        self.assertAlmostEqual(3333, results.count('2'), delta=10)
        self.assertAlmostEqual(3333, results.count('3'), delta=10)

        # Case 4 - force different being true causes warped usage
        # (selection % becomes less extreme because the high % item gives way to low)
        items = [
            ('1', 8), # 80% share
            ('2', 1),
            ('3', 1),
        ]

        r = Randomizer(items, self.machine)
        r.force_different = True

        results = list()
        for x in range(10000):
            results.append(next(r))

        self.assertAlmostEqual(4700, results.count('1'), delta=300)
        self.assertAlmostEqual(2650, results.count('2'), delta=200)
        self.assertAlmostEqual(2650, results.count('3'), delta=200)

        # Case 5 - force different with force all causes even usage
        items = [
            ('1', 8),
            ('2', 1),
            ('3', 1),
        ]

        r = Randomizer(items, self.machine)
        r.force_all = True
        r.force_different = True

        results = list()
        for x in range(10000):
            results.append(next(r))

        self.assertAlmostEqual(3334, results.count('1'), delta=10)
        self.assertAlmostEqual(3333, results.count('2'), delta=10)
        self.assertAlmostEqual(3333, results.count('3'), delta=10)
