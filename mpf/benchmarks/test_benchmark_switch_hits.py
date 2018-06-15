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

    def testPlayfieldActiveSwitchHits(self):
        for i in range(1000):
            self.machine.switch_controller.process_switch_by_num("1", 1, self.machine.default_platform)
            self.machine.switch_controller.process_switch_by_num("1", 0, self.machine.default_platform)
        self.machine_run()

        for runs in range(10):
            num = 10000
            start = time.time()
            for i in range(num):
                self.machine.switch_controller.process_switch_by_num("1", 1, self.machine.default_platform)
                self.machine.switch_controller.process_switch_by_num("1", 0, self.machine.default_platform)
            end = time.time()
            self.machine_run()
            end2 = time.time()
            print("Duration {:.5f}ms Processing {:.5f}ms".format((1000 * (end - start) / num), ((end2 - end) * 1000) / num))

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
            print("Duration {:.5f}ms Processing {:.5f}ms".format((1000 * (end - start) / num), ((end2 - end) * 1000) / num))
