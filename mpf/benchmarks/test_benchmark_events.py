import time

from mpf.core.logging import LogMixin

from mpf.tests.MpfGameTestCase import MpfGameTestCase


class BenchmarkEvents(MpfGameTestCase):

    def get_options(self):
        options = super().get_options()
        if self.unittest_verbosity() <= 1:
            options["production"] = True
        return options

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'benchmarks/machine_files/events/'

    def get_platform(self):
        return 'virtual'

    def setUp(self):
        LogMixin.unit_test = False
        super().setUp()

    def _output(self, what, start, end, num):
        print("{}: Duration {:.5f}ms  Per second: {:2f}".format(
            what,
            (1000 * (end - start) / num),
            num / (end - start)
        ))

    def _handler(self, **kwargs):
        del kwargs

    def _handler2(self, num, **kwargs):
        del kwargs
        self.machine.events.post("test5_{}".format(num))

    def _benchmark(self, function, name, num=10000, iterations=10):
        function(num, -1)
        total = 0
        for i in range(iterations):
            start = time.time()
            function(num, i)
            end = time.time()
            total += (end - start) / num
            self._output(name, start, end, num)

        print("Total average {:.5f}ms".format(total * 1000 / iterations))
        return total/iterations

    def _unique_events(self, num, run):
        for i in range(num):
            self.machine.events.add_handler("test_{}".format(i + run * 10000), self._handler)

    def _multiple_events(self, num, run):
        for i in range(num):
            self.machine.events.add_handler("test_{}".format(i + run * 10000), self._handler)
            self.machine.events.add_handler("test_{}".format(i + run * 10000), self._handler)
            self.machine.events.add_handler("test_{}".format(i + run * 10000), self._handler)

    def _post_event(self, num, run):
        if run == -1:
            for i in range(num):
                self.machine.events.add_handler("test3_{}".format(i), self._handler)

        for i in range(num):
            self.machine.events.post("test3_{}".format(i))

        self.machine_run()

    def _post_event_with_new_handler(self, num, run):
        if run == -1:
            for i in range(num):
                self.machine.events.add_handler("test4_{}".format(i), self._handler2, num=i)
                self.machine.events.add_handler("test5_{}".format(i), self._handler)

        for i in range(num):
            self.machine.events.post("test4_{}".format(i), run=run)

        self.machine_run()

    def testEvents(self):
        num = 10000
        self._benchmark(self._unique_events, "Add unique event handlers", num, 10)
        self._benchmark(self._multiple_events, "Add multiple event handlers", int(num / 3), 10)
        self._benchmark(self._post_event, "Post events", num, 10)
        self._benchmark(self._post_event_with_new_handler, "Post events with new handler", num, 10)

