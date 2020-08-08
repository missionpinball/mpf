"""Contains code for the smart_virtual platform."""
import abc
import logging

from typing import List
from mpf.core.logging import LogMixin
from mpf.core.platform import DriverConfig
from mpf.devices.ball_device.enable_coil_ejector import EnableCoilEjector
from mpf.devices.ball_device.hold_coil_ejector import HoldCoilEjector
from mpf.devices.ball_device.pulse_coil_ejector import PulseCoilEjector

from mpf.platforms.interfaces.driver_platform_interface import PulseSettings, HoldSettings

from mpf.core.delays import DelayManager
from mpf.platforms.virtual import (VirtualHardwarePlatform as VirtualPlatform, VirtualDriver)
from mpf.devices.ball_device.ball_device import BallDevice  # pylint: disable-msg=cyclic-import,unused-import

MYPY = False
if MYPY:   # pragma: no cover
    from typing import Dict     # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import


class BaseSmartVirtualCoilAction(metaclass=abc.ABCMeta):

    """A action for a coil."""

    def __init__(self, actions: List[str], machine: "MachineController") -> None:
        """Initialise switch enable action."""
        self.log = logging.getLogger("SmartVirtual Coil Action")
        self.actions = actions
        self.machine = machine
        self.delay = DelayManager(self.machine)
        self.machine.config['smart_virtual'] = self.machine.config_validator.validate_config(
            "smart_virtual", self.machine.config.get('smart_virtual', {}))

    def enable(self, coil):
        """Enable driver."""
        del coil
        if "enable" in self.actions:
            self._perform_action()
            return True

        return False

    def disable(self, coil):
        """Disable driver."""
        del coil
        if "disable" in self.actions:
            self._perform_action()
            return True

        return False

    def pulse(self, coil, milliseconds):
        """Pulse driver."""
        del coil
        del milliseconds
        if "pulse" in self.actions:
            self._perform_action()
            return True

        return False

    @abc.abstractmethod
    def _perform_action(self):
        """Implement your action here."""


class ResetDropTargetAction(BaseSmartVirtualCoilAction):

    """Set switches inactive when coil is pulsed."""

    def __init__(self, actions, machine, drop_target_bank):
        """Initialise switch enable action."""
        super().__init__(actions, machine)
        self.drop_target_bank = drop_target_bank

    def _hit_switches(self):
        # need to pull the drop targets from the config, not the drop_targets
        # attribute, because if the bank is defined in a mode then the
        # attr won't be populated yet, but if there's a bank in a mode with a
        # single reset coil we assume that coil will reset all the drop targets
        # anytime it's called.
        for target in self.drop_target_bank.config['drop_targets']:
            self.machine.switch_controller.process_switch_obj(target.config['switch'], 0, logical=True)

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
            self.log.debug("Disabling switch %s due to coil pulse", switch)
            self.machine.switch_controller.process_switch_obj(switch, 0, logical=True)

    def _perform_action(self):
        self.delay.add(ms=50, callback=self._hit_switches)


class SwitchEnableAction(SwitchDisableAction):

    """Enable switches when coil is pulsed."""

    def _hit_switches(self):
        for switch in self.switches:
            self.log.debug("Enabling switch %s due to coil pulse", switch.name)
            self.machine.switch_controller.process_switch_obj(switch, 1, logical=True)


class ScoreReelAdvanceAction(BaseSmartVirtualCoilAction):

    """Virtual score reel."""

    # pylint: disable-msg=too-many-arguments
    def __init__(self, actions, machine, switch_map, limit_lo, limit_hi, name):
        """Initialise virtual score reel."""
        super().__init__(actions, machine)
        self.switch_map = switch_map
        self.position = limit_lo
        self.limit_lo = limit_lo
        self.limit_hi = limit_hi
        self.name = name

        # set initial position
        self._update_switches()

    def _perform_action(self):
        # increment position and handle overflow
        self.position += 1
        self.position %= self.limit_hi + 1
        if self.position < self.limit_lo:
            self.position = self.limit_lo

        self.machine.log.debug("Virtual score reel for %s at value %s", self.name, self.position)

        self._update_switches()

    def _update_switches(self):
        # disable all switches except the current position
        for position, switch in self.switch_map.items():
            if not switch:
                continue

            state = self.position == position

            if not self.machine.switch_controller.is_state(switch, state):
                self.machine.switch_controller.process_switch_obj(switch, state, logical=True)


class AddBallToTargetAction(BaseSmartVirtualCoilAction):

    """Hit switches when coil is pulsed."""

    # pylint: disable-msg=too-many-arguments
    def __init__(self, actions, machine, platform, device: BallDevice):
        """Initialise add ball to target action."""
        super().__init__(actions, machine)
        self.device = device    # type: BallDevice
        self.ball_switches = device.ball_count_handler.counter.config.get('ball_switches', [])
        self.platform = platform
        self.confirm_eject_switch = device.config['confirm_eject_switch']
        self.target_device = None
        self.result = "success"

    def confirm_eject_via_switch(self, switch):
        """Simulate eject via switch."""
        self.log.debug('Confirming eject via switch: %s', switch.name)
        self.machine.switch_controller.process_switch_obj(switch, 1, logical=True)
        self.delay.add(ms=10, callback=self._release_confirm_switch, switch=switch)

    def _release_confirm_switch(self, switch):
        self.log.debug('Releasing eject confirmation switch: %s', switch.name)
        self.machine.switch_controller.process_switch_obj(switch, 0, logical=True)

    def set_target(self, source, target, mechanical_eject, **kwargs):
        """Set target for action."""
        self.log.debug("Setting eject target. %s -> %s. Mechanical: %s",
                       source.name, target.name, mechanical_eject)
        del kwargs
        driver = None
        if isinstance(source.ejector, (EnableCoilEjector, PulseCoilEjector)) and source.ejector.config['eject_coil']:
            driver = source.ejector.config['eject_coil'].hw_driver
        elif isinstance(source.ejector, HoldCoilEjector) and source.ejector.config['hold_coil']:
            driver = source.ejector.config['hold_coil'].hw_driver
        if driver and driver.action:
            driver.action.target_device = target

        if "delay" in self.actions and self.machine.config['smart_virtual']['simulate_manual_plunger']:
            self.log.debug("Adding %sms delay before ejecting",
                           self.machine.config['smart_virtual']['simulate_manual_plunger_timeout'])

            # simulate mechanical eject
            self.delay.add(ms=self.machine.config['smart_virtual']['simulate_manual_plunger_timeout'],
                           callback=self._perform_action)

    def set_result(self, result):
        """Set result to "success" (default), "return" or "missing"."""
        self.result = result

    def _perform_action(self):
        self.log.debug("Removing ball from device %s", self.device.name)

        if not self.device.balls:
            return

        for switch in self.ball_switches:
            if self.machine.switch_controller.is_active(switch):
                self.machine.switch_controller.process_switch_obj(switch, 0, logical=True)
                self.log.debug("Deactivating: %s", switch.name)
                break

        if self.result == "success":
            if (self.device.ball_count_handler.counter.config.get('entrance_switch_full_timeout') and
                    self.device.machine.switch_controller.is_active(
                        self.device.ball_count_handler.counter.config['entrance_switch'][0])):

                self.machine.switch_controller.process_switch_obj(
                    self.device.ball_count_handler.counter.config['entrance_switch'][0], 0, logical=True)
                self.log.debug("Deactivating: %s",
                               self.device.ball_count_handler.counter.config['entrance_switch'][0].name)

            if self.confirm_eject_switch:
                self.delay.add(ms=50, callback=self.confirm_eject_via_switch,
                               switch=self.confirm_eject_switch)
                self.log.debug("Adding delay for confirm eject switch")

            if self.target_device and not self.target_device.is_playfield():
                self.delay.add(ms=100, callback=self.platform.add_ball_to_device,
                               device=self.target_device)
                self.log.debug("Adding delay for %s to receive ball in 100ms", self.target_device.name)
                self.target_device = None
        elif self.result == "return":
            self.delay.add(ms=100, callback=self.platform.add_ball_to_device,
                           device=self.target_device)
        elif self.result == "missing":
            if self.target_device.is_playfield() and not self.confirm_eject_switch:
                raise AssertionError("Ball cannot go missing to a playfield without confirm_switch.")
            # missing does not do anything
        else:
            raise AssertionError("Invalid result {}".format(self.result))


class SmartVirtualHardwarePlatform(VirtualPlatform):

    """Base class for the smart_virtual hardware platform."""

    def __init__(self, machine):
        """Initialise smart virtual platform."""
        super().__init__(machine)
        self.delay = DelayManager(self.machine)
        self.actions = {}       # type: Dict[BallDevice, AddBallToTargetAction]

    def __repr__(self):
        """Return string representation."""
        return '<Platform.SmartVirtual>'

    def _setup_log(self):
        self.log = logging.getLogger("Smart Virtual Platform")
        self.debug_log("Configuring smart_virtual hardware interface.")

    async def start(self):
        """Initialise platform when all devices are ready."""
        self._initialise_ball_devices()
        self._initialise_drop_targets()
        self._initialise_drop_target_banks()
        self._initialise_score_reels()

    def _initialise_score_reels(self):
        for device in self.machine.score_reels.values():
            if device.config['coil_inc']:
                device.config['coil_inc'].hw_driver.action = ScoreReelAdvanceAction(
                    ["pulse"], self.machine,
                    {
                        0: device.config['switch_0'],
                        1: device.config['switch_1'],
                        2: device.config['switch_2'],
                        3: device.config['switch_3'],
                        4: device.config['switch_4'],
                        5: device.config['switch_5'],
                        6: device.config['switch_6'],
                        7: device.config['switch_7'],
                        8: device.config['switch_8'],
                        9: device.config['switch_9'],
                        10: device.config['switch_10'],
                        11: device.config['switch_11'],
                        12: device.config['switch_12']
                    },
                    device.config['limit_lo'],
                    device.config['limit_hi'],
                    device.name
                )

    def _initialise_drop_targets(self):
        for device in self.machine.drop_targets.values():
            if device.config['reset_coil']:
                device.config['reset_coil'].hw_driver.action = SwitchDisableAction(
                    ["pulse"], self.machine, [device.config['switch']])
            if device.config['knockdown_coil']:
                device.config['knockdown_coil'].hw_driver.action = SwitchEnableAction(
                    ["pulse"], self.machine, [device.config['switch']])

    def _initialise_drop_target_banks(self):
        for device in self.machine.drop_target_banks.values():
            if device.config['reset_coil']:
                device.config['reset_coil'].hw_driver.action = ResetDropTargetAction(
                    ["pulse"], self.machine, device)

            for coil in device.config['reset_coils']:
                coil.hw_driver.action = ResetDropTargetAction(
                    ["pulse"], self.machine, device)

    def _initialise_ball_devices(self):
        for device in self.machine.ball_devices.values():
            if device.is_playfield():
                continue

            action = None
            if isinstance(device.ejector, (EnableCoilEjector, PulseCoilEjector)) and \
                    device.ejector.config['eject_coil']:
                action = device.ejector.config['eject_coil'].hw_driver.action = AddBallToTargetAction(
                    ["pulse", "enable"], self.machine, self, device)

            elif isinstance(device.ejector, HoldCoilEjector) and device.ejector.config['hold_coil']:
                action = device.ejector.config['hold_coil'].hw_driver.action = AddBallToTargetAction(
                    ["disable"], self.machine, self, device)
            elif device.config['mechanical_eject']:
                action = AddBallToTargetAction(["delay"], self.machine, self, device)

            if action:
                # we assume that the device always reaches its target. diverters are ignored
                self.machine.events.add_handler('balldevice_{}_ejecting_ball'.format(device.name),
                                                action.set_target)
                self.actions[device] = action

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict):
        """Configure driver."""
        del platform_settings
        # generate number if None
        if number is None:
            number = str(self._next_driver)
            self._next_driver += 1

        driver = SmartVirtualDriver(config, number)

        return driver

    def add_ball_to_device(self, device: BallDevice):
        """Add ball to device."""
        self.debug_log("Adding ball to %s", device.name)
        if LogMixin.unit_test and device.balls >= device.capacity:
            raise AssertionError("KABOOM! We just added a ball to {} which has a capacity "
                                 "of {} but already had {} ball(s)".format(
                                     device.name, device.capacity, device.balls))

        if device.ball_count_handler.counter.config.get('entrance_switch'):
            entrance_switch = device.ball_count_handler.counter.config['entrance_switch'][0]
            # if there's an entrance_switch_full_timeout, that means the ball
            # will sit on this switch if the device is full, otherwise, it
            # will pass over it, hitting during the process
            if device.ball_count_handler.counter.config.get('entrance_switch_full_timeout'):
                if device.balls == device.capacity - 1:

                    if LogMixin.unit_test and self.machine.switch_controller.is_active(entrance_switch):
                        raise AssertionError(
                            "KABOOM! We just added a ball to {} which already "
                            "had an active entrance switch {}".format(
                                device.name, entrance_switch))

                    self.debug_log('Enabling switch %s due to ball being added to %s',
                                   entrance_switch.name, device.name)

                    self.machine.switch_controller.process_switch_obj(entrance_switch, 1, True)
                    return

            self.debug_log('Hitting switch %s due to ball being added to %s', entrance_switch.name, device.name)
            self.machine.switch_controller.process_switch_obj(entrance_switch, 1, True)
            self.machine.switch_controller.process_switch_obj(entrance_switch, 0, True)

        if device.ball_count_handler.counter.config.get('ball_switches'):
            found_switch = False
            for switch in device.ball_count_handler.counter.config['ball_switches']:
                if self.machine.switch_controller.is_inactive(switch):
                    self.debug_log('Enabling switch %s due to ball being added to %s', switch.name, device.name)
                    self.machine.switch_controller.process_switch_obj(
                        switch, 1, logical=True)
                    found_switch = True
                    break

            if LogMixin.unit_test and not found_switch:
                raise AssertionError("KABOOM! We just added a ball to {} which "
                                     "was already full.".format(device.name))


class SmartVirtualDriver(VirtualDriver):

    """Smart virtual driver."""

    def __init__(self, config, number):
        """Initialise smart virtual driver."""
        super().__init__(config, number)
        self.action = None

    def __repr__(self):
        """Return string representation."""
        return "SmartVirtualDriver.{}".format(self.number)

    def disable(self):
        """Disable driver."""
        super().disable()
        if self.action:
            self.action.disable(self)

    def enable(self, pulse_settings: PulseSettings, hold_settings: HoldSettings):
        """Enable driver."""
        super().enable(pulse_settings, hold_settings)
        if self.action:
            self.action.enable(self)

    def pulse(self, pulse_settings: PulseSettings):
        """Pulse driver."""
        super().pulse(pulse_settings)
        if self.action:
            self.action.pulse(self, pulse_settings.duration)
