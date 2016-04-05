"""Contains code for the smart_virtual platform."""

import logging

from mpf.core.delays import DelayManager
from mpf.platforms.virtual import (HardwarePlatform as VirtualPlatform, VirtualDriver)


class HardwarePlatform(VirtualPlatform):
    """Base class for the smart_virtual hardware platform."""

    def __init__(self, machine):
        super().__init__(machine)
        self.log = logging.getLogger("Smart Virtual Platform")
        self.log.debug("Configuring smart_virtual hardware interface.")

        self.delay = DelayManager(self.machine.delayRegistry)

    def __repr__(self):
        return '<Platform.SmartVirtual>'

    def initialize(self):
        self.machine.events.add_handler('machine_reset_phase_1',
                                        self._initialize2)

    def set_target(self, source, target, **kwargs):
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
                                            self.set_target)

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

    def configure_driver(self, config, device_type='coil'):
        # todo should probably throw out the number that we get since it could
        # be a weird string and just return an incremental int?

        driver = SmartVirtualDriver(config['number'], self.machine, self)

        driver.driver_settings = config
        driver.driver_settings['pulse_ms'] = 30

        return driver, config['number']

    def write_hw_rule(self, *args, **kwargs):
        pass

    def clear_hw_rule(self, sw_name):
        sw_num = self.machine.switches[sw_name].number

        for entry in list(self.hw_switch_rules.keys()):  # slice for copy
            if entry.startswith(
                    self.machine.switches.number(sw_num).name):
                del self.hw_switch_rules[entry]

    def tick(self, dt):
        # ticks every hw loop (typically hundreds of times per sec)
        pass

    def confirm_eject_via_switch(self, switch):
        self.machine.switch_controller.process_switch(switch.name, 1)
        self.machine.switch_controller.process_switch(switch.name, 0)

    def add_ball_to_device(self, device):
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
    def __init__(self, number, machine, platform):
        self.log = logging.getLogger('SmartVirtualDriver')
        self.number = number
        self.machine = machine
        self.platform = platform
        self.ball_switches = list()
        self.target_device = None
        self.type = None
        self.confirm_eject_switch = None

    def __repr__(self):
        return "SmartVirtualDriver.{}".format(self.number)

    def disable(self):
        if self.type == 'hold':
            self._handle_ball()

    def enable(self):
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

    def pulse(self, milliseconds=None):
        if self.type == 'eject':
            self._handle_ball()

        if milliseconds:
            return milliseconds
        else:
            return self.driver_settings['pulse_ms']

    def register_ball_switches(self, switches):
        self.ball_switches.extend(switches)

    def set_target_device(self, target):
        self.target_device = target
