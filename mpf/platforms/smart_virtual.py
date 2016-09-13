"""Contains code for the smart_virtual platform."""

import logging

from mpf.core.delays import DelayManager
from mpf.platforms.virtual import (HardwarePlatform as VirtualPlatform, VirtualDriver)


class BaseSmartVirtualCoilAction:

    """A action for a coil."""

    def __init__(self, actions, machine):
        """Initialise switch enable action."""
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
    def __init__(self, actions, machine, platform, confirm_eject_switch, ball_switches):
        """Initialise add ball to target action."""
        super().__init__(actions, machine)
        self.ball_switches = ball_switches
        self.platform = platform
        self.confirm_eject_switch = confirm_eject_switch
        self.target_device = None

    def confirm_eject_via_switch(self, switch):
        """Simulate eject via switch."""
        self.machine.switch_controller.process_switch(switch.name, 1)
        self.machine.switch_controller.process_switch(switch.name, 0)

    def set_target(self, source, target, mechanical_eject, **kwargs):
        """Set target for action."""
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
        for switch in self.ball_switches:
            if self.machine.switch_controller.is_active(switch.name):
                self.machine.switch_controller.process_switch(switch.name, 0,
                                                              logical=True)
                break

        if self.confirm_eject_switch:
            self.delay.add(ms=50, callback=self.confirm_eject_via_switch, switch=self.confirm_eject_switch)

        if self.target_device and not self.target_device.is_playfield():
            self.delay.add(ms=100, callback=self.platform.add_ball_to_device, device=self.target_device)
            self.target_device = None


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

    def _initialize2(self):
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
                    ["pulse"], self.machine, self, device.config['confirm_eject_switch'],
                    device.config['ball_switches']
                )

            elif device.config['hold_coil']:
                action = device.config['hold_coil'].hw_driver.action = AddBallToTargetAction(
                    ["disable"], self.machine, self, device.config['confirm_eject_switch'],
                    device.config['ball_switches']
                )
            if action:
                # we assume that the device always reaches its target. diverters are ignored
                self.machine.events.add_handler('balldevice_{}_ball_eject_attempt'.format(device.name),
                                                action.set_target)

    def configure_driver(self, config):
        """Configure driver."""
        # todo should probably throw out the number that we get since it could
        # be a weird string and just return an incremental int?

        driver = SmartVirtualDriver(config)

        return driver

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
