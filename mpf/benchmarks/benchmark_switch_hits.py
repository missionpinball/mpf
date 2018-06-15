import time

from mpf.tests.MpfGameTestCase import MpfGameTestCase


class BenchmarkSwitchHits(MpfGameTestCase):

    def getConfigFile(self):
        return 'config.yaml'

    def getMachinePath(self):
        return 'benchmarks/machine_files/switch_hits/'

    def get_platform(self):
        return 'virtual'

    def testExcessiveSwitchHits(self):
        for i in range(1000):
            self.machine.switch_controller.process_switch_by_num("1", 1, self.machine.default_platform)
            self.machine.switch_controller.process_switch_by_num("1", 0, self.machine.default_platform)

        num = 10000
        start = time.time()
        for i in range(num):
            self.machine.switch_controller.process_switch_by_num("1", 1, self.machine.default_platform)
            self.machine.switch_controller.process_switch_by_num("1", 0, self.machine.default_platform)
        end = time.time()
        self.machine_run()
        print("Duration", "{:.10f}".format((end - start) / num))

        num = 10000
        start = time.time()
        for i in range(num):
            self.machine.switch_controller.process_switch_by_num("1", 1, self.machine.default_platform)
            self.machine.switch_controller.process_switch_by_num("1", 0, self.machine.default_platform)
        end = time.time()
        self.machine_run()
        print("Duration", "{:.10f}".format((end - start) / num))

        num = 10000
        start = time.time()
        for i in range(num):
            self.machine.switch_controller.process_switch_by_num("1", 1, self.machine.default_platform)
            self.machine.switch_controller.process_switch_by_num("1", 0, self.machine.default_platform)
        end = time.time()
        self.machine_run()
        print("Duration", "{:.10f}".format((end - start) / num))

        num = 10000
        start = time.time()
        for i in range(num):
            self.machine.switch_controller.process_switch_by_num("1", 1, self.machine.default_platform)
            self.machine.switch_controller.process_switch_by_num("1", 0, self.machine.default_platform)
        end = time.time()
        self.machine_run()
        print("Duration", "{:.10f}".format((end - start) / num))
