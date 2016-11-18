"""Contains code for the smart_virtual platform."""

import logging

from mpf.core.delays import DelayManager
from mpf.platforms.virtual import (HardwarePlatform as VirtualPlatform, VirtualDriver)


class BaseSmartVirtualCoilAction:

    """A action for a coil."""

    def __init__(self, actions, machine):
        """Initialise switch enable action."""
        self.log = logging.getLogger("SmartVirtual Coil Action")
        self.actions = actions
        self.machine = machine
        self.delay = DelayManager(self.machine.delayRegistry)
        self.machine.config['smart_virtual'] = self.machine.config_validator.validate_config(
            "smart_virtual", self.machine.config.get('smart_virtual', {}))

    def enable(self, coil):
        """Enable driver."""
        del coil
        if "enable" in self.actions:
            self._perform_action()
            return True
        else:
            return False

    def disable(self, coil):
        """Disable driver."""
        del coil
        if "disable" in self.actions:
            self._perform_action()
            return True
        else:
            return False

    def pulse(self, coil, milliseconds):
        """Pulse driver."""
        del coil
        del milliseconds
        if "pulse" in self.actions:
            self._perform_action()
            return True
        else:
            return False

    def _perform_action(self):
        """Implement your action here."""
        pass


class ResetDropTargetAction(BaseSmartVirtualCoilAction):

    """Disable switches when coil is pulsed."""

    def __init__(self, actions, machine, drop_target_bank):
        """Initialise switch enable action."""
        super().__init__(actions, machine)
        self.drop_target_bank = drop_target_bank

    def _hit_switches(self):
        for target in self.drop_target_bank.drop_targets:
            self.machine.switch_controller.process_switch(target.config['switch'].name, 0)

    def _perform_action(self):
        self.delay.add(ms=50, callback=self._hit_switches)


class SwitchDisableAction(BaseSmartVirtualCoilAction):

    """Disable switches when coil is pulsed."""

    def __init__(self, actions, machine, switches):
        """Initialise switch enable action."""
        super().__init__(actions, machine)
        self.switches = switches

    def _hit_switches(self):
        for switch in self.switches:
            self.machine.switch_controller.process_switch(switch.name, 0)

    def _perform_action(self):
        self.delay.add(ms=50, callback=self._hit_switches)


class SwitchEnableAction(SwitchDisableAction):

    """Enable switches when coil is pulsed."""

    def _hit_switches(self):
        for switch in self.switches:
            self.machine.switch_controller.process_switch(switch.name, 1)


class AddBallToTargetAction(BaseSmartVirtualCoilAction):

    """Hit switches when coil is pulsed."""

    # pylint: disable-msg=too-many-arguments
    def __init__(self, actions, machine, platform, device):
        """Initialise add ball to target action."""
        super().__init__(actions, machine)
        self.device = device
        self.ball_switches = device.config['ball_switches']
        self.platform = platform
        self.confirm_eject_switch = device.config['confirm_eject_switch']
        self.target_device = None

    def confirm_eject_via_switch(self, switch):
        """Simulate eject via switch."""
        self.machine.switch_controller.process_switch(switch.name, 1)
        self.machine.switch_controller.process_switch(switch.name, 0)

    def set_target(self, source, target, mechanical_eject, **kwargs):
        """Set target for action."""
        self.log.debug("Setting eject target. %s -> %s. Mechanical: %s", source.name, target.name, mechanical_eject)
        del kwargs
        driver = None
        if source.config['eject_coil']:
            driver = source.config['eject_coil'].hw_driver
        elif source.config['hold_coil']:
            driver = source.config['hold_coil'].hw_driver
        if driver and driver.action:
            driver.action.target_device = target

        if mechanical_eject and self.machine.config['smart_virtual']['simulate_manual_plunger']:
            # simulate mechanical eject
            self.delay.add(ms=self.machine.config['smart_virtual']['simulate_manual_plunger_timeout'],
                           callback=self._perform_action)

    def _perform_action(self):
        self.log.debug("Removing ball from device %s", self.device.name)

        if not self.device.balls:
            return

        for switch in self.ball_switches:
            if self.machine.switch_controller.is_active(switch.name):
                self.machine.switch_controller.process_switch(switch.name, 0,
                                                              logical=True)
                self.log.debug("Deactivating: %s", switch.name)
                break

        if (self.device.config['entrance_switch_full_timeout'] and
                self.device.machine.switch_controller.is_active(
                self.device.config['entrance_switch'].name)):

            self.machine.switch_controller.process_switch(
                self.device.config['entrance_switch'].name, 0, True)
            self.log.debug("Deactivating: %s", self.device.config['entrance_switch'].name)

        if self.confirm_eject_switch:
            self.delay.add(ms=50, callback=self.confirm_eject_via_switch,
                           switch=self.confirm_eject_switch)
            self.log.debug("Adding delay for confirm eject switch")

        if self.target_device and not self.target_device.is_playfield():
            self.delay.add(ms=100, callback=self.platform.add_ball_to_device,
                           device=self.target_device)
            self.log.debug("Adding delay for %s to receive ball in 100ms", self.target_device.name)
            self.target_device = None


class HardwarePlatform(VirtualPlatform):

    """Base class for the smart_virtual hardware platform."""

    def __init__(self, machine):
        """Initialise smart virtual platform."""
        super().__init__(machine)
        self.delay = DelayManager(self.machine.delayRegistry)

    def __repr__(self):
        """Return string representation."""
        return '<Platform.SmartVirtual>'

    def _setup_log(self):
        self.log = logging.getLogger("Smart Virtual Platform")
        self.log.debug("Configuring smart_virtual hardware interface.")

    def initialize(self):
        """Initialise platform."""
        self.machine.events.add_handler('machine_reset_phase_1',
                                        self._initialize2)

    def _initialize2(self, **kwargs):
        del kwargs
        self._initialise_ball_devices()
        self._initialise_drop_targets()
        self._initialise_drop_target_banks()

    def _initialise_drop_targets(self):
        for device in self.machine.drop_targets:
            if device.config['reset_coil']:
                device.config['reset_coil'].hw_driver.action = SwitchDisableAction(
                    ["pulse"], self.machine, [device.config['switch']])
            if device.config['knockdown_coil']:
                device.config['knockdown_coil'].hw_driver.action = SwitchEnableAction(
                    ["pulse"], self.machine, [device.config['switch']])

    def _initialise_drop_target_banks(self):
        for device in self.machine.drop_target_banks:
            if device.config['reset_coil']:
                device.config['reset_coil'].hw_driver.action = ResetDropTargetAction(
                    ["pulse"], self.machine, device)

            for coil in device.config['reset_coils']:
                coil.hw_driver.action = ResetDropTargetAction(
                    ["pulse"], self.machine, device)

    def _initialise_ball_devices(self):
        for device in self.machine.ball_devices:
            if device.is_playfield():
                continue

            action = None
            if device.config['eject_coil']:
                action = device.config['eject_coil'].hw_driver.action = AddBallToTargetAction(
                    ["pulse", "enable"], self.machine, self, device)

            elif device.config['hold_coil']:
                action = device.config['hold_coil'].hw_driver.action = AddBallToTargetAction(
                    ["disable"], self.machine, self, device)
            if action:
                # we assume that the device always reaches its target. diverters are ignored
                self.machine.events.add_handler('balldevice_{}_ball_eject_attempt'.format(device.name),
                                                action.set_target)

    def configure_driver(self, config):
        """Configure driver."""
        # generate number if None
        if config['number'] is None:
            config['number'] = self._next_driver
            self._next_driver += 1

        driver = SmartVirtualDriver(config)

        return driver

    def add_ball_to_device(self, device):
        """Add ball to device."""
        if device.balls + 1 > device.config['ball_capacity']:
            raise AssertionError("KABOOM! We just added a ball to {} which has a capacity "
                                 "of {} but already had {} ball(s)".format(device.name,
                                                                           device.config['ball_capacity'],
                                                                           device.balls))

        if device.config['entrance_switch']:

            # if there's an entrance_switch_full_timeout, that means the ball
            # will sit on this switch if the device is full, otherwise, it
            # will pass over it, hitting during the process

            if device.config['entrance_switch_full_timeout']:
                if device.balls == device.config['ball_capacity'] - 1:

                    if self.machine.switch_controller.is_active(
                            device.config['entrance_switch'].name):
                        raise AssertionError(
                            "KABOOM! We just added a ball to {} which already "
                            "had an active entrance switch".format(
                                device.name))

                    self.machine.switch_controller.process_switch(
                        device.config['entrance_switch'].name, 1, True)
                    return

            self.machine.switch_controller.process_switch(
                device.config['entrance_switch'].name, 1, True)
            self.machine.switch_controller.process_switch(
                device.config['entrance_switch'].name, 0, True)

        if device.config['ball_switches']:
            found_switch = False
            for switch in device.config['ball_switches']:
                if self.machine.switch_controller.is_inactive(switch.name):
                    self.machine.switch_controller.process_switch(
                        switch.name, 1, True)
                    found_switch = True
                    break

            if not found_switch:
                raise AssertionError("KABOOM! We just added a ball to {} which"
                                     "was already full.".format(device.name))


class SmartVirtualDriver(VirtualDriver):

    """Smart virtual driver."""

    def __init__(self, config):
        """Initialise smart virtual driver."""
        super().__init__(config)
        self.action = None

    def __repr__(self):
        """Return string representation."""
        return "SmartVirtualDriver.{}".format(self.number)

    def disable(self, coil):
        """Disable driver."""
        if self.action:
            self.action.disable(coil)

    def enable(self, coil):
        """Enable driver."""
        if self.action:
            self.action.enable(coil)

    def pulse(self, coil, milliseconds):
        """Pulse driver."""
        if self.action:
            self.action.pulse(coil, milliseconds)

        return milliseconds
