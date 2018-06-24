import time

from mpf.core.logging import LogMixin

from mpf.tests.MpfGameTestCase import MpfGameTestCase


class BenchmarkSwitchHits(MpfGameTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'benchmarks/machine_files/switch_hits/'

    def get_platform(self):
        return 'virtual'

    def setUp(self):
        LogMixin.unit_test = False
        super().setUp()

    def _output(self, start, end, end2, num):
        print("Duration {:.5f}ms Processing {:.5f}ms Total: {:5f}ms Per second: {:2f}".format(
            (1000 * (end - start) / num), ((end2 - end) * 1000) / num, (1000 * (end2 - start)) / num,
            (num * 1) / (end2 - start)
        ))

    def testMinimalSwitch(self):
        for i in range(1000):
            self.machine.switch_controller.process_switch_by_num("4", 1, self.machine.default_platform)
            self.machine.switch_controller.process_switch_by_num("4", 0, self.machine.default_platform)
        self.advance_time_and_run()

        num = 10000
        for runs in range(10):
            start = time.time()
            for i in range(num):
                self.machine.switch_controller.process_switch_by_num("4", 1, self.machine.default_platform)
                self.machine.switch_controller.process_switch_by_num("4", 0, self.machine.default_platform)
            end = time.time()
            self.advance_time_and_run()
            end2 = time.time()
            self._output(start, end, end2, num)

    def testSimpleHandlers(self):
        hit = 0
        handler = 100
        for i in range(handler):
            self.machine.switch_controller.add_switch_handler("s_switch4", lambda: hit.__add__(1))

        for i in range(1000):
            self.machine.switch_controller.process_switch_by_num("4", 1, self.machine.default_platform)
            self.machine.switch_controller.process_switch_by_num("4", 0, self.machine.default_platform)
        self.advance_time_and_run()

        num = 10000
        for runs in range(10):
            start = time.time()
            for i in range(num):
                self.machine.switch_controller.process_switch_by_num("4", 1, self.machine.default_platform)
                self.machine.switch_controller.process_switch_by_num("4", 0, self.machine.default_platform)
            end = time.time()
            self.advance_time_and_run()
            end2 = time.time()
            self._output(start, end, end2, num)

    def testTimedSwitchHandlers(self):
        hit = 0
        handler = 1
        for i in range(handler):
            self.machine.switch_controller.add_switch_handler("s_switch4", lambda: hit.__add__(1), ms=100)
        for i in range(1000):
            self.machine.switch_controller.process_switch_by_num("4", 1, self.machine.default_platform)
            self.machine.switch_controller.process_switch_by_num("4", 0, self.machine.default_platform)
        self.advance_time_and_run()

        num = 10000
        for runs in range(10):
            start = time.time()
            for i in range(num):
                self.machine.switch_controller.process_switch_by_num("4", 1, self.machine.default_platform)
                self.machine.switch_controller.process_switch_by_num("4", 0, self.machine.default_platform)
            end = time.time()
            self.advance_time_and_run()
            end2 = time.time()
            self._output(start, end, end2, num * handler)

    def testBenchmarkIgnoreWindowMsHits(self):
        for i in range(1000):
            self.machine.switch_controller.process_switch_by_num("3", 1, self.machine.default_platform)
            self.machine.switch_controller.process_switch_by_num("3", 0, self.machine.default_platform)
        self.machine.switch_controller.process_switch_by_num("3", 1, self.machine.default_platform)
        self.advance_time_and_run()

        num = 10000
        for runs in range(10):
            start = time.time()
            for i in range(num):
                self.machine.switch_controller.process_switch_by_num("3", 1, self.machine.default_platform)
                self.machine.switch_controller.process_switch_by_num("3", 0, self.machine.default_platform)
            end = time.time()
            self.machine.switch_controller.process_switch_by_num("3", 1, self.machine.default_platform)
            self.advance_time_and_run()
            end2 = time.time()
            self._output(start, end, end2, num)

    def testPlayfieldActiveSwitchHits(self):
        for i in range(1000):
            self.machine.switch_controller.process_switch_by_num("1", 1, self.machine.default_platform)
            self.machine.switch_controller.process_switch_by_num("1", 0, self.machine.default_platform)
        self.machine_run()

        num = 10000
        for runs in range(10):
            start = time.time()
            for i in range(num):
                self.machine.switch_controller.process_switch_by_num("1", 1, self.machine.default_platform)
                self.machine.switch_controller.process_switch_by_num("1", 0, self.machine.default_platform)
            end = time.time()
            self.machine_run()
            end2 = time.time()
            self._output(start, end, end2, num)

    def test20TagsHits(self):
        for i in range(1000):
            self.machine.switch_controller.process_switch_by_num("2", 1, self.machine.default_platform)
            self.machine.switch_controller.process_switch_by_num("2", 0, self.machine.default_platform)
        self.machine_run()

        for runs in range(10):
            num = 10000
            start = time.time()
            for i in range(num):
                self.machine.switch_controller.process_switch_by_num("2", 1, self.machine.default_platform)
                self.machine.switch_controller.process_switch_by_num("2", 0, self.machine.default_platform)
            end = time.time()
            self.machine_run()
            end2 = time.time()
            self._output(start, end, end2, num)
