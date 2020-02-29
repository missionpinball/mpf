#!/usr/bin/python3
"""AFL fuzzer."""
import argparse
import asyncio
import os
import sys

import logging

import mpf.core
from mpf.core.logging import LogMixin
from mpf.core.utility_functions import Util
from mpf.tests.MpfTestCase import TestMachineController
from mpf.tests.loop import TimeTravelLoop, TestClock


class AflRunner(object):

    """AFL fuzzer."""

    def __init__(self, use_virtual):
        """Initialize fuzzer."""
        self.loop = None
        self.clock = None
        self.machine = None     # type: TestMachineController
        self.machine_config_patches = dict()
        self.machine_config_patches['mpf'] = dict()
        self.machine_config_patches['mpf']['default_platform_hz'] = 1
        self.machine_config_patches['bcp'] = []
        self.machine_config_defaults = {}
        self.switch_list = []
        self.use_virtual = use_virtual
        self._invalid_input = False
        self._exception = None

    def _exception_handler(self, loop, context):
        try:
            loop.stop()
        except RuntimeError:
            pass

        self._exception = context

    def get_platform(self):
        """Return platform."""
        if self.use_virtual:
            return "virtual"

        return "smart_virtual"

    @staticmethod
    def get_config_file():
        """Return config file."""
        return "config.yaml"

    def get_options(self):
        """Return option arrays."""
        mpfconfig = os.path.abspath(os.path.join(
            mpf.core.__path__[0], os.pardir, 'mpfconfig.yaml'))

        return {
            'force_platform': self.get_platform(),
            'mpfconfigfile': mpfconfig,
            'configfile': Util.string_to_event_list(self.get_config_file()),
            'debug': True,
            'bcp': False,
            'no_load_cache': False,
            'create_config_cache': True,
            'text_ui': False,
        }

    def advance_time_and_run(self, delta=1.0):
        """Advance time and run."""
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
        """Set up fuzzer."""
        self.loop = TimeTravelLoop()
        self.loop.set_exception_handler(self._exception_handler)
        self.clock = TestClock(self.loop)

        self.machine = TestMachineController(
            os.path.abspath(os.path.join(
                mpf.core.__path__[0], os.pardir)), machine_path,
            self.get_options(), self.machine_config_patches, self.machine_config_defaults, self.clock, dict(),
            True)

        try:
            self.loop.run_until_complete(self.machine.initialise())
        except RuntimeError as e:
            try:
                self.machine.stop()
            # pylint: disable-msg=broad-except
            except Exception:
                pass
            if self._exception and "exception" in self._exception:
                raise self._exception['exception']
            elif self._exception:
                raise Exception(self._exception, e)
            raise e

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

    def _abort(self, **kwargs):
        """Abort fuzzer run."""
        del kwargs
        self._invalid_input = True

    def run(self, actions, find_logic_bugs):
        """Run fuzzer."""
        if find_logic_bugs:
            self.machine.events.add_handler("balldevice_ball_missing", self._abort)
            self.machine.events.add_handler("found_new_ball", self._abort)
            self.machine.events.add_handler("mode_game_stopped", self._abort)

        for action in actions:
            if self._invalid_input:
                # bail out if we hit an invalid input. afl will notice this
                return

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

        if find_logic_bugs:
            self.advance_time_and_run(60)
            if self._invalid_input:
                # might happen late
                return

            balls = 0
            for playfield in self.machine.playfields:
                balls += playfield.balls

            if balls != self.machine.game.balls_in_play:
                print("Balls in play:", self.machine.game.balls_in_play)
                print("Playfields:")
                for playfield in self.machine.playfields:
                    print(playfield.name, playfield.balls)
                print("Devices:")
                for device in self.machine.ball_devices:
                    print(device.name, device.balls, device.available_balls)
                raise AssertionError("Balls in play do not match balls on playfields.")

    def dump(self, wait, add_balls, start_game, actions):
        """Dump fuzzer input."""
        if add_balls:
            for device in self.machine.ball_devices:
                if "trough" in device.tags:
                    for switch in device.config['ball_switches']:
                        print("Enable switch {}".format(switch.name))
                    if device.config['entrance_switch']:
                        print("Enable switch {}".format(device.config['entrance_switch'].name))
            print("Advance time 10s")

        if start_game:
            for switch in self.machine.switches:
                if "start" in switch.tags:
                    print("Enable/disable switch {}".format(switch.name))

        if wait > 0:
            print("Advance time {}s".format(wait))

        for action in actions:
            if action & 0b10000000:
                ms = int(action & 0b01111111)
                ms *= ms
                print("Advance time by {} ms".format(ms))
            else:
                switch = int(action & 0b01111111)
                if switch >= len(self.switch_list):
                    continue
                switch_obj = self.machine.switches[self.switch_list[switch]]
                state = switch_obj.hw_state ^ 1
                # print(switch_list[switch], state, switch_obj.hw_state)
                print("Toggle switch {}. New state: {}".format(switch_obj.name, state))
                self.machine.switch_controller.process_switch_by_num(switch_obj.hw_switch.number, state,
                                                                     self.machine.default_platform)

parser = argparse.ArgumentParser(
    description='Fuzz MPF using AFL')

parser.add_argument("-d",
                    action="store_true", dest="debug",
                    help="Turn on debug to reproduce fuzzer results")

parser.add_argument("-D",
                    action="store_true", dest="dump",
                    help="Dump test case.")

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

parser.add_argument("-L",
                    action="store_true", dest="find_logic_bugs",
                    help="Find game logic bugs only")

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

if args.dump:
    action_str = sys.stdin.buffer.read(-1)
    runner.dump(int(args.wait), args.add_balls, args.start_game, action_str)
    os._exit(-1)    # NOQA

if args.add_balls:
    runner.add_balls()

if args.start_game:
    if not args.add_balls:
        raise AssertionError("Cannot start game without balls. Use -b")
    runner.start_game()

if int(args.wait) > 0:
    runner.advance_time_and_run(int(args.wait))

if args.start_game and not runner.machine.game:
    raise AssertionError("Failed to start a game.")

# keep effort minimal after those two lines. everything before this will execute only once.
# everything after this on every run

import afl  # NOQA
afl.init()

action_str = sys.stdin.buffer.read(-1)

runner.run(action_str, args.find_logic_bugs)

if args.debug:
    runner.advance_time_and_run(10)
else:
    os._exit(0)  # NOQA
