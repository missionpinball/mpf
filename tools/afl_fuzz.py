#!/usr/bin/python3
import argparse
import asyncio
import os
import sys

import time
import logging

import mpf.core
from mpf.core.logging import LogMixin
from mpf.core.utility_functions import Util
from mpf.tests.MpfTestCase import TestMachineController
from mpf.tests.loop import TimeTravelLoop, TestClock


class AflRunner(object):

    def __init__(self, use_virtual):
        self.loop = None
        self.clock = None
        self.machine = None     # type: TestMachineController
        self.machine_config_patches = dict()
        self.machine_config_patches['mpf'] = dict()
        self.machine_config_patches['mpf']['default_platform_hz'] = 1
        self.machine_config_patches['bcp'] = []
        self.switch_list = []
        self.use_virtual = use_virtual

    def _exception_handler(self, loop, context):
        try:
            loop.stop()
        except RuntimeError:
            pass

        self._exception = context

    def get_platform(self):
        if self.use_virtual:
            return "virtual"
        else:
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
            True)

        start = time.time()
        while not self.machine.test_init_complete and time.time() < start + 20:
            self.advance_time_and_run(0.01)

        self.machine.events.process_event_queue()
        self.advance_time_and_run(1)

        self.switch_list = sorted(self.machine.switches.keys())

        for switch in self.machine.switches:
            self.machine.switch_controller.process_switch_obj(switch, 0, True)

    def add_balls(self):
        """Add balls."""
        for device in self.machine.ball_devices:
            if "trough" in device.tags:
                for switch in device.config['ball_switches']:
                    self.machine.switch_controller.process_switch_obj(switch, 1, True)
                if device.config['entrance_switch']:
                    self.machine.switch_controller.process_switch_obj(device.config['entrance_switch'], 1, True)


        # let balls settle
        self.advance_time_and_run(10)

    def start_game(self):
        """Start game."""
        for switch in self.machine.switches:
            if "start" in switch.tags:
                self.machine.switch_controller.process_switch_obj(switch, 1, True)
                self.machine.switch_controller.process_switch_obj(switch, 0, True)

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

parser = argparse.ArgumentParser(
    description='Fuzz MPF using AFL')

parser.add_argument("-d",
                    action="store_true", dest="debug",
                    help="Turn on debug to reproduce fuzzer results")

parser.add_argument("-u",
                    action="store_true", dest="unit_test",
                    help="Run in unit tests mode which fails early")

parser.add_argument("-b",
                    action="store_true", dest="add_balls",
                    help="Add balls to trough")

parser.add_argument("-w",
                    action="store", dest="wait", default=0,
                    help="Run machine for x seconds before forking")

parser.add_argument("-G",
                    action="store_true", dest="start_game",
                    help="Start game")

parser.add_argument("-v",
                    action="store_true", dest="use_virtual",
                    help="Use virtual instead of smart_virtual for low-level fuzzing")

parser.add_argument("machine_path", help="Path of the machine folder",
                    default=None, nargs='?')

args = parser.parse_args()

if args.debug:
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s : %(levelname)s : %(name)s : %(message)s')
else:
    logging.basicConfig(level=99)

if args.unit_test:
    LogMixin.unit_test = True

runner = AflRunner(use_virtual=args.use_virtual)
runner.setUp(args.machine_path)

if args.add_balls:
    runner.add_balls()

if args.start_game:
    if not args.add_balls:
        raise AssertionError("Cannot start game without balls. Use -b")
    runner.start_game()

if int(args.wait) > 0:
    runner.advance_time_and_run(int(args.wait))

# keep effort minimal after those two lines. everything before this will execute only once.
# everything after this on every run

import afl
afl.init()

action_str = sys.stdin.buffer.read(-1)

runner.run(action_str)

if args.debug:
    runner.advance_time_and_run(10)
else:
    os._exit(0)
