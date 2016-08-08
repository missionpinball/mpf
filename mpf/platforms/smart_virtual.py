"""Contains code for the smart_virtual platform."""

import logging

from mpf.core.delays import DelayManager
from mpf.platforms.virtual import (HardwarePlatform as VirtualPlatform, VirtualDriver)


class HardwarePlatform(VirtualPlatform):

    """Base class for the smart_virtual hardware platform."""

    def __init__(self, machine):
        """Initialise smart virtual platform."""
        super().__init__(machine)
        self.log = logging.getLogger("Smart Virtual Platform")
        self.log.debug("Configuring smart_virtual hardware interface.")

        self.delay = DelayManager(self.machine.delayRegistry)

    def __repr__(self):
        """Return string representation."""
        return '<Platform.SmartVirtual>'

    def initialize(self):
        """Initialise platform."""
        self.machine.events.add_handler('machine_reset_phase_1',
                                        self._initialize2)

    @classmethod
    def _set_target(cls, source, target, **kwargs):
        del kwargs
        driver = None
        if source.config['eject_coil']:
            driver = source.config['eject_coil'].hw_driver
        elif source.config['hold_coil']:
            driver = source.config['hold_coil'].hw_driver
        if driver:
            driver.set_target_device(target)

    def _initialize2(self):
        for device in self.machine.ball_devices:
            if device.is_playfield():
                continue

            # we assume that the device always reaches its target. diverters are ignored
            self.machine.events.add_handler('balldevice_{}_ball_eject_attempt'.format(device.name),
                                            self._set_target)

            if device.config['eject_coil']:
                device.config['eject_coil'].hw_driver.register_ball_switches(
                    device.config['ball_switches'])

                device.config['eject_coil'].hw_driver.type = 'eject'

                if not device.config['eject_targets'][0].is_playfield():
                    device.config['eject_coil'].hw_driver.set_target_device(
                        device.config['eject_targets'][0])

                if device.config['confirm_eject_switch']:
                    device.config['eject_coil'].hw_driver.confirm_eject_switch = device.config['confirm_eject_switch']

            elif device.config['hold_coil']:
                device.config['hold_coil'].hw_driver.register_ball_switches(
                    device.config['ball_switches'])

                device.config['hold_coil'].hw_driver.type = 'hold'

                if not device.config['eject_targets'][0].is_playfield():
                    device.config['hold_coil'].hw_driver.set_target_device(
                        device.config['eject_targets'][0])

                if device.config['confirm_eject_switch']:
                    device.config['hold_coil'].hw_driver.confirm_eject_switch = device.config['confirm_eject_switch']

    def configure_driver(self, config):
        """Configure driver."""
        # todo should probably throw out the number that we get since it could
        # be a weird string and just return an incremental int?

        driver = SmartVirtualDriver(config, self.machine, self)

        return driver

    def confirm_eject_via_switch(self, switch):
        """Simulate eject via switch."""
        self.machine.switch_controller.process_switch(switch.name, 1)
        self.machine.switch_controller.process_switch(switch.name, 0)

    def add_ball_to_device(self, device):
        """Add ball to device."""
        if device.config['entrance_switch']:
            pass  # todo

        if device.config['ball_switches']:
            found_switch = False
            for switch in device.config['ball_switches']:
                if self.machine.switch_controller.is_inactive(switch.name):
                    self.machine.switch_controller.process_switch(switch.name,
                                                                  1,
                                                                  True)
                    found_switch = True
                    break

            if not found_switch:
                raise AssertionError("KABOOM! We just added a ball to {} which"
                                     "was already full.".format(device.name))


class SmartVirtualDriver(VirtualDriver):

    """Smart virtual driver."""

    def __init__(self, config, machine, platform):
        """Initialise smart virtual driver."""
        super().__init__(config)
        self.log = logging.getLogger('SmartVirtualDriver')
        self.machine = machine
        self.platform = platform
        self.ball_switches = list()
        self.target_device = None
        self.type = None
        self.confirm_eject_switch = None

    def __repr__(self):
        """Return string representation."""
        return "SmartVirtualDriver.{}".format(self.number)

    def disable(self, coil):
        """Disable driver."""
        del coil
        if self.type == 'hold':
            self._handle_ball()

    def enable(self, coil):
        """Enable driver."""
        pass

    def _handle_ball(self):
        for switch in self.ball_switches:
            if self.machine.switch_controller.is_active(switch.name):
                self.machine.switch_controller.process_switch(switch.name, 0,
                                                              logical=True)
                break

        if self.confirm_eject_switch:
            self.platform.delay.add(ms=50,
                                    callback=self.platform.confirm_eject_via_switch,
                                    switch=self.confirm_eject_switch)

        if self.target_device and not self.target_device.is_playfield():
            self.platform.delay.add(ms=100,
                                    callback=self.platform.add_ball_to_device,
                                    device=self.target_device)

    def pulse(self, coil, milliseconds):
        """Pulse driver."""
        del coil
        if self.type == 'eject':
            self._handle_ball()

        return milliseconds

    def register_ball_switches(self, switches):
        """Register ball switches."""
        self.ball_switches.extend(switches)

    def set_target_device(self, target):
        """Set target of driver for ball simulation."""
        self.target_device = target
