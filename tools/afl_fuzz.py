#!/usr/bin/python3
"""AFL fuzzer."""
import argparse
import asyncio
import gc
import os
import sys

import logging

import mpf.core
from mpf.core.logging import LogMixin
from mpf.core.utility_functions import Util
from mpf.tests.MpfTestCase import TestMachineController, UnitTestConfigLoader
from mpf.tests.loop import TimeTravelLoop, TestClock


class AflRunner(object):

    """AFL fuzzer."""

    __slots__ = ["loop", "clock", "machine", "debug", "machine_config_patches", "machine_config_defaults",
                "switch_list", "use_virtual", "_invalid_input", "_exception"]

    def __init__(self, use_virtual, debug):
        """Initialize fuzzer."""
        self.loop = None
        self.clock = None
        self.machine = None     # type: TestMachineController
        self.debug = debug
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
            'debug': False,
            'bcp': False,
            'no_load_cache': False,
            'create_config_cache': True,
            'text_ui': False,
            'production': not self.debug,
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

    def setup(self, machine_path):
        """Set up fuzzer."""
        self.loop = TimeTravelLoop()
        self.loop.set_exception_handler(self._exception_handler)
        self.clock = TestClock(self.loop)

        config_loader = UnitTestConfigLoader(machine_path, ["config.yaml"], self.machine_config_defaults,
                                             self.machine_config_patches, {})

        config = config_loader.load_mpf_config()
        try:
            # remove virtual_platform_start_active_switches as it messes with out switch logic
            config.get_machine_config().pop("virtual_platform_start_active_switches")
        except KeyError:
            pass

        self.machine = TestMachineController(
            self.get_options(), config, self.machine_config_patches, self.machine_config_defaults, self.clock, dict(),
            True)

        try:
            self.loop.run_until_complete(self.machine.initialize())
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
        balls_to_add = 3
        for device in sorted(self.machine.ball_devices.values()):
            if "trough" in device.tags:
                for switch in device.ball_count_handler.counter.config.get('ball_switches', []):
                    self.machine.switch_controller.process_switch_obj(switch, 1, True)
                    balls_to_add -= 1
                    if balls_to_add == 0:
                        break
                if balls_to_add == 0:
                    break
                if device.ball_count_handler.counter.config.get('entrance_switch'):
                    self.machine.switch_controller.process_switch_obj(
                        device.ball_count_handler.counter.config['entrance_switch'], 1, True)
                    balls_to_add -= 1
                    if balls_to_add == 0:
                        break

        # let balls settle
        self.advance_time_and_run(10)

    def start_game(self):
        """Start game."""
        found_start_switch = False
        for switch in self.machine.switches:
            if "start" in switch.tags:
                found_start_switch = True
                self.machine.switch_controller.process_switch_obj(switch, 1, True)
                self.machine.switch_controller.process_switch_obj(switch, 0, True)

        if not found_start_switch:
            raise AssertionError("Did not find any switch tagged with tag \"start\".")

    def _abort(self, **kwargs):
        """Abort fuzzer run."""
        del kwargs
        self._invalid_input = True
        if not self.debug:
            os._exit(0)  # NOQA

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
                if action == 0b11111111:
                    if self.machine.game and \
                            self.machine.game.balls_in_play < self.machine.ball_controller.num_balls_known:
                        self.machine.playfield.add_ball()
                        self.machine.game.balls_in_play += 1
                    else:
                        self._abort()
                else:
                    ms = int(action & 0b01111111)
                    ms *= ms
                    self.advance_time_and_run(ms / 1000.0)
            else:
                switch = int(action & 0b01111111)
                if switch >= len(self.switch_list):
                    self._abort()
                    return
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
            balls_to_add = 3
            for device in sorted(self.machine.ball_devices.values()):
                if "trough" in device.tags:
                    for switch in device.ball_count_handler.counter.config.get('ball_switches', []):
                        print("Enable switch {}".format(switch.name))
                        switch.hw_state = 1
                        balls_to_add -= 1
                        if balls_to_add == 0:
                            break

                    if balls_to_add == 0:
                        break
                    if device.ball_count_handler.counter.config.get('entrance_switch'):
                        print("Enable switch {}".format(device.config['entrance_switch'].name))
                        device.config['entrance_switch'].switch.hw_state = 1
                        balls_to_add -= 1
                        if balls_to_add == 0:
                            break
            print("Advance time 10s")

        if start_game:
            for switch in self.machine.switches:
                if "start" in switch.tags:
                    print("Enable/disable switch {}".format(switch.name))

        if wait > 0:
            print("Advance time {}s".format(wait))

        for action in actions:
            if action & 0b10000000:
                if action == 0b11111111:
                    print("Add ball into play")
                else:
                    ms = int(action & 0b01111111)
                    ms *= ms
                    print("Advance time by {} ms".format(ms))
            else:
                switch = int(action & 0b01111111)
                if switch >= len(self.switch_list):
                    print("Invalid switch. Abort!")
                    return
                switch_obj = self.machine.switches[self.switch_list[switch]]
                switch_obj.hw_state = state = switch_obj.hw_state ^ 1
                # print(switch_list[switch], state, switch_obj.hw_state)
                print("Toggle switch {}. New state: {}".format(switch_obj.name, state))


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

runner = AflRunner(use_virtual=args.use_virtual, debug=args.debug)
runner.setup(args.machine_path)

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

# run GC once to clean everything up
gc.collect()

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
