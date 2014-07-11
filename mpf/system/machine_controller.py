"""The main machine object for the Mission Pinball Framework.

"""
# devices.py (contains classes for various playfield devices)
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
import os
import yaml
from collections import defaultdict
import time

from mpf.system.hardware import HardwareDict
from mpf.system.timing import Timing, Timer
from mpf.system.tasks import Task, DelayManager
from mpf.system.events import EventManager
from mpf.system.switch_controller import SwitchController
from mpf.system.ball_controller import BallController
from mpf.modules.ball_search import BallSearch
from mpf.modules.keyboard import Keyboard
from mpf.system.devices import Flipper, AutofireCoil, BallDevice


class MachineController(object):
    """Base class for the Machine Controller object.

    The machine controller is the main entity of the entire framework. It's the
    main part that's in charge and makes things happen.

    Parameters
    ----------

    config_file : string
        The name of the main configuration file which will be read when the
        machine controller is created. This config file typically contains a
        list of additional config files that hold settings for the machine, but
        it can also hold settings itself.

    physical_hw : bool
        Specifies whether there is a physical pinball controller attached, or
        whether the machine controller should operate in software-only
        (virtual hardware) mode.
    """

    def __init__(self, config_file, physical_hw=True):
        self.log = logging.getLogger(__name__)
        self.starttime = time.time()
        self.config = defaultdict()  # so we can simplify checking for options
        self.platform = None
        self.physical_hw = physical_hw
        self.switch_events = []
        self.done = False
        self.HZ = None
        self.gameflow_index = 0

        self.coils = HardwareDict()
        self.lamps = HardwareDict()
        self.switches = HardwareDict()
        self.leds = HardwareDict()
        # todo combine leds and lamps?
        # todo add GI and flashers?

        # create all the machine-wide objects & set them up.
        self.events = EventManager()
        self.config = self._load_config(config_file)
        self.set_platform()
        self.timing = Timing(self)
        self.timing.configure(HZ=self.config['Machine']['HZ'])
        self.switch_controller = SwitchController(self)
        self.process_config()
        self.ball_controller = BallController(self)
        self.ballsearch = BallSearch(self)

        # todo clean this up when you fix game flow
        self.game = None
        self.attract = None

        self.events.post("machine_init_complete")
        self.reset()

        # register event handlers
        self.events.add_handler('machine_flow_advance', self.flow_advance)

    def reset(self):
        """Resets the machine."""
        # Do we want to reset all timers here? todo

        # reset variables
        self.gameflow_index = 0

        # todo remove (just a test)
        self.periodic = self.timing.add(Timer(self.periodic_timer_test,
                                              frequency=2000))

        self.switch_controller.add_switch_handler(switch_name='start', state=1,
                                                  ms=500, callback=self.test)
        #self.switch_controller.add_switch_handler('start', self.test, 0, 4000)

        # todo now start attract mode
        # self.attract_mode = Task()

        # after our reset is over, we start the gameflow
        self._flow_do()

    def flow_advance(self, position=None):
        """Advances the machine to the next machine mode as specified in the
        gameflow. Typically this just advances between Attract mode and Game
        mode.

        """

        if not position:
            if self.gameflow_index == len(self.config['GameFlow']) - 1:
                self.gameflow_index = 0
            else:
                self.gameflow_index += 1
        else:
            self.gameflow_index = position
        self.log.debug("Advancing Machine Flow. New Index: %s",
                       self.gameflow_index)
        self._flow_do()

    def _flow_do(self):
        # todo change this to set it self up automatically from the yaml file
        # Maybe this can switch to events, where there's an event like
        # 'gameflow_<yamlentry>' that each of these things watches for?

        from mpf.game.attract import Attract
        from mpf.game.game import Game

        if self.gameflow_index == 0:
            self.attract = Attract(self)
            if self.game:
                self.game.stop()
                self.game = None
            self.attract.start()
        elif self.gameflow_index == 1:
            self.game = Game(self)
            if self.attract:
                self.attract.stop()
                self.attract = None
            self.game.start()

        # todo when I fix this, also clean up the stuff in init

    def _get_config_from_file(self, file):
        # Returns a yaml dictionary from the passed file
        if os.path.isfile(file):
            try:
                self.log.debug("Loading configuration file: %s", file)
                return yaml.load(open(file, 'r'))
            except yaml.YAMLError, exc:
                if hasattr(exc, 'problem_mark'):
                    mark = exc.problem_mark
                    self.log.error("Error found in config file %s. "
                                      "Line %, Position %s", file, mark.line+1,
                                      mark.column+1)
        else:
            self.log.error("Error: %s not found", file)

    def _load_config(self, file):
        # Get the list of config files from the passed yaml file
        file_list = self._get_config_from_file(file)
        # Pull out the path from that config file to use for the remaining files
        file_path = os.path.split(file)[0]

        # Loop through all the config files and build up our config dic
        config = {}

        for config_file in file_list:
            updates = self._get_config_from_file(os.path.join(file_path,
                                                              config_file))
            if updates:
                config.update(updates)

        return config

    def set_platform(self):
        """ Sets the hardware platform based on the "Platform" item in the
        configuration dictionary. Looks for a module of that name in the
        /platform directory.

        """

        try:
            hardware_platform = __import__('mpf.platform.%s' %
                               self.config['Hardware']['Platform'],
                               fromlist=["HardwarePlatform"])

            # above line has an effect similar to:
            # from mpf.platform.<platform_name> import HardwarePlatform

        except ImportError:
            self.log.error("Error importing platform module: %s",
                           self.config['Hardware']['Platform'])
            quit()  # No point in continuing if we error here

        self.platform = hardware_platform.HardwarePlatform(self).parent

    def process_config(self):
        """Processes the hardware config based on the machine config files.

        """
        self.platform.process_hw_config()  # This just sets the low level hw

        # read in op settings and merge them into the config dictionary

        # Now setup all the devices:
        # todo also could probably automate this instead of having these very
        # similar repeating blocks

        # Keyboard mapping
        if 'key_map' in self.config:
            self.keyboard = Keyboard(self)

        # Flippers
        self.flippers = {}
        self.flippers = HardwareDict()
        for flipper in self.config['Devices']['Flippers']:
            Flipper(flipper, self, self.flippers,
                    self.config['Devices']['Flippers'][flipper])

        # Autofire Coils
        self.autofires = {}
        self.autofires = HardwareDict()
        for coil in self.config['Devices']['Autofire Coils']:
            coil = AutofireCoil(coil, self, self.autofires,
                                self.config['Devices']['Autofire Coils'][coil])

        # Ball Devices
        self.balldevices = {}
        self.balldevices = HardwareDict()
        for balldevice in self.config['Devices']['BallDevices']:
            BallDevice(balldevice, self, self.balldevices,
                       self.config['Devices']['BallDevices'][balldevice])

        # Create easy references to our trough and plunger devices
        self.trough = self.balldevices.items_tagged('trough')[0]
        if len(self.balldevices.items_tagged('trough')) > 1:
            self.log.warning("More than one trough device found")
        self.plunger = self.balldevices.items_tagged('plunger')[0]
        if len(self.balldevices.items_tagged('plunger')) > 1:
            self.log.warning("More than one plunger device found")
            # 'plunger' is the device that's served from the trough. It's fine
            # if there are more than one shooter lane. We're just talking about
            # where new balls are served from

    def string_to_list(self, string):
        """ Converts a comma-separated string into a python list.

        """
        if type(string) is str:
            # convert to list then strip out leading / trailing white space
            return [x.strip() for x in string.split(',')]
        else:
            # if we're not passed a string, just return an empty list.
            return []

    def enable_autofires(self):
        """Enables all the autofire coils in the machine."""

        self.log.debug("Enabling autofire coils")
        for autofire in self.autofires:
            autofire.enable()

    def disable_autofires(self):
        """Disables all the autofire coils in the machine."""

        self.log.debug("Disabling autofire coils")
        for autofire in self.autofires:
            autofire.disable()

    def enable_flippers(self):
        """Enables all the flippers in the machine."""

        self.log.debug("Enabling flippers")
        for flipper in self.flippers:
            flipper.enable()

    def disable_flippers(self):
        """Disables all the flippers in the machine."""

        self.log.debug("Disabling flippers")
        for flipper in self.flippers:
            flipper.disable()

    def run(self):
        """The main machine run loop.

        """
        self.log.debug("Starting the main machine run loop.")
        loops = 0

        self.platform.timer_initialize()

        if self.hw_polling:

            try:
                while self.done is False:
                    self.platform.hw_loop()
                    loops += 1

            finally:
                if loops != 0:
                    self.log.debug("Hardware loop speed: %sHz",
                                   round(loops / (time.time() -
                                                  self.starttime)))

        # todo add support to read software switch events

    def timer_tick(self):
        """Called by the platform each machine tick based on self.HZ"""
        self.timing.timer_tick()  # notifies the timing module
        Task.timer_tick(Timing.tick)  # notifies tasks
        self.events.post('timer_tick')  # sends the timer_tick system event
        DelayManager.timer_tick()

    def periodic_timer_test(self):  # todo remove
        print "periodic timer test. Current timer tick:", Timing.tick
        #self.coils.flipperLwLMain.pulse()

    def test(self):
        print "in test method."

    def end_run_loop(self):
        """Causes the main run_loop to end."""
        self.done = True

# The MIT License (MIT)

# Copyright (c) 2013-2014 Brian Madden and Gabe Knuth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
