#!/usr/bin/python3
import asyncio
import os
import sys

import time
import logging

import mpf.core
from mpf.core.utility_functions import Util
from mpf.tests.MpfTestCase import TestMachineController
from mpf.tests.loop import TimeTravelLoop, TestClock


class AflRunner(object):

    def __init__(self):
        self.loop = None
        self.clock = None
        self.machine = None     # type: TestMachineController
        self.machine_config_patches = dict()
        self.machine_config_patches['mpf'] = dict()
        self.machine_config_patches['mpf']['default_platform_hz'] = 1
        self.machine_config_patches['mpf']['plugins'] = list()
        self.machine_config_patches['bcp'] = []
        self.switch_list = []

    def _exception_handler(self, loop, context):
        try:
            loop.stop()
        except RuntimeError:
            pass

        self._exception = context

    def get_platform(self):
        return "smart_virtual"

    def getConfigFile(self):
        return "config.yaml"

    def getAbsoluteMachinePath(self):
        # creates an absolute path based on machine_path
        return "/home/kantert/cloud/flipper/src/good_vs_evil"

    def getOptions(self):

        mpfconfig = os.path.abspath(os.path.join(
            mpf.core.__path__[0], os.pardir, 'mpfconfig.yaml'))

        return {
            'force_platform': self.get_platform(),
            'mpfconfigfile': mpfconfig,
            'configfile': Util.string_to_list(self.getConfigFile()),
            'debug': True,
            'bcp': False,
            'no_load_cache': False,
            'create_config_cache': True,
        }

    def advance_time_and_run(self, delta=1.0):
        try:
            self.loop.run_until_complete(asyncio.sleep(delay=delta, loop=self.loop))
            return
        except RuntimeError as e:
            if self._exception and "exception" in self._exception:
                raise self._exception['exception']
            elif self._exception:
                raise Exception(self._exception, e)
            raise e

    def setUp(self, machine_path):
        self.loop = TimeTravelLoop()
        self.loop.set_exception_handler(self._exception_handler)
        self.clock = TestClock(self.loop)

        self.machine = TestMachineController(
            os.path.abspath(os.path.join(
                mpf.core.__path__[0], os.pardir)), machine_path,
            self.getOptions(), self.machine_config_patches, self.clock, dict(),
            False)

        start = time.time()
        while not self.machine.test_init_complete and time.time() < start + 20:
            self.advance_time_and_run(0.01)

        self.machine.events.process_event_queue()
        self.advance_time_and_run(1)

        self.switch_list = sorted(self.machine.switches.keys())

    def run(self, actions):
        for action in actions:
            if action & 0b10000000:
                ms = int(action & 0b01111111)
                ms *= ms
                self.advance_time_and_run(ms / 1000.0)
            else:
                switch = int(action & 0b01111111)
                if switch >= len(self.switch_list):
                    continue
                switch_obj = self.machine.switches[self.switch_list[switch]]
                state = switch_obj.hw_state ^ 1
                # print(switch_list[switch], state, switch_obj.hw_state)
                self.machine.switch_controller.process_switch_by_num(switch_obj.hw_switch.number, state,
                                                                     self.machine.default_platform)
#logging.basicConfig(level=logging.DEBUG,
#                    format='%(asctime)s : %(levelname)s : %(name)s : %(message)s')

runner = AflRunner()
try:
    machine_path = sys.argv[1]
except:
    sys.exit("Usage {} machine_path".format(sys.argv[0]))
runner.setUp(sys.argv[1])

import afl
afl.init()

action_str = sys.stdin.buffer.read(-1)

runner.run(action_str)

os._exit(0)
