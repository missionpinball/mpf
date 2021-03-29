"""Contains the base classes for drop targets and drop target banks."""
from enum import Enum
from typing import List, Optional
from typing import Set

from mpf.core.mode import Mode
from mpf.core.player import Player

from mpf.core.delays import DelayManager
from mpf.core.device_monitor import DeviceMonitor
from mpf.core.events import event_handler
from mpf.core.mode_device import ModeDevice
from mpf.core.system_wide_device import SystemWideDevice

MYPY = False
if MYPY:   # pragma: no cover
    from mpf.devices.driver import Driver           # pylint: disable-msg=cyclic-import,unused-import
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import


@DeviceMonitor("complete")
class DropTarget(SystemWideDevice):

    """Represents a single drop target in a pinball machine.

    Args: Same as the `Target` parent class
    """

    config_section = 'drop_targets'
    collection = 'drop_targets'
    class_label = 'drop_target'

    __slots__ = ["reset_coil", "knockdown_coil", "banks", "_in_ball_search", "complete", "delay", "_ignore_switch_hits"]

    def __init__(self, machine: "MachineController", name: str) -> None:
        """Initialise drop target."""
        self.reset_coil = None              # type: Optional[Driver]
        self.knockdown_coil = None          # type: Optional[Driver]
        self.banks = set()                  # type: Set[DropTargetBank]
        super().__init__(machine, name)

        self._in_ball_search = False
        self.complete = False
        self.delay = DelayManager(machine)

        self._ignore_switch_hits = False

    async def _initialize(self):
        await super()._initialize()
        self.reset_coil = self.config['reset_coil']
        self.knockdown_coil = self.config['knockdown_coil']

        # can't read the switch until the switch controller is set up
        self.machine.events.add_handler('init_phase_4',
                                        self._update_state_from_switch, priority=2)
        self.machine.events.add_handler('init_phase_4',
                                        self._register_switch_handlers, priority=1)

        if self.config['ball_search_order']:
            self.config['playfield'].ball_search.register(
                self.config['ball_search_order'], self._ball_search, self.name)

        if '{}_active'.format(self.config['playfield'].name) in self.config['switch'].tags:
            self.raise_config_error(
                "Drop target device '{}' uses switch '{}' which has a "
                "'{}_active' tag. This is handled internally by the device. Remove the "
                "redundant '{}_active' tag from that switch.".format(
                    self.name, self.config['switch'].name, self.config['playfield'].name,
                    self.config['playfield'].name), 1)

    def _ignore_switch_hits_for(self, ms):
        """Ignore switch hits for ms."""
        self._ignore_switch_hits = True
        self.delay.reset(name="ignore_switch", callback=self._restore_switch_hits, ms=ms)

    def _restore_switch_hits(self):
        self._ignore_switch_hits = False
        self._update_state_from_switch(reconcile=True)

    def _ball_search_phase1(self):
        if not self.complete and self.reset_coil:
            self.reset_coil.pulse()
            return True
        # if down. knock down again
        if self.complete and self.knockdown_coil:
            self.knockdown_coil.pulse()
            return True
        return False

    def _ball_search_phase2(self):
        if self.reset_coil and self.knockdown_coil:
            self._in_ball_search = True
            if self.complete:
                self.reset_coil.pulse()
                self.delay.add(100, self._ball_search_knockdown)
            else:
                self.knockdown_coil.pulse()
                self.delay.add(100, self._ball_search_reset)
            return True

        # fall back to phase1
        return self._ball_search_phase1()

    def _ball_search_phase3(self):
        if self.complete:
            if self.reset_coil:
                self.reset_coil.pulse()
                if self.knockdown_coil:
                    self._in_ball_search = True
                    self.delay.add(100, self._ball_search_knockdown)
                return True

            # fall back to phase1
            return self._ball_search_phase1()

        if self.knockdown_coil:
            self.knockdown_coil.pulse()
            if self.reset_coil:
                self._in_ball_search = True
                self.delay.add(100, self._ball_search_reset)
            return True

        # fall back to phase1
        return self._ball_search_phase1()

    def _ball_search_iteration_finish(self):
        self._in_ball_search = False

    def _ball_search_knockdown(self):
        self.knockdown_coil.pulse()
        self.delay.add(100, self._ball_search_iteration_finish)

    def _ball_search_reset(self):
        self.reset_coil.pulse()
        self.delay.add(100, self._ball_search_iteration_finish)

    def _ball_search(self, phase, iteration):
        del iteration
        if phase == 1:
            # phase 1: do not change state.
            # if up. reset again
            return self._ball_search_phase1()
        if phase == 2:
            # phase 2: if we can reset and knockdown the target we will do that
            return self._ball_search_phase2()

        # phase3: reset no matter what
        return self._ball_search_phase3()

    def _register_switch_handlers(self, **kwargs):
        del kwargs
        # register for notification of switch state
        # this is in addition to the parent since drop targets track
        # self.complete in separately

        self.machine.switch_controller.add_switch_handler_obj(
            self.config['switch'],
            self._update_state_from_switch, 0)
        self.machine.switch_controller.add_switch_handler_obj(
            self.config['switch'],
            self._update_state_from_switch, 1)

    @event_handler(6)
    def event_enable_keep_up(self, **kwargs):
        """Handle enable_keep_up control event."""
        del kwargs
        self.enable_keep_up()

    def enable_keep_up(self):
        """Keep the target up by enabling the coil."""
        if self.reset_coil:
            self.reset_coil.enable()

    @event_handler(5)
    def event_disable_keep_up(self, **kwargs):
        """Handle disable_keep_up control event."""
        del kwargs
        self.disable_keep_up()

    def disable_keep_up(self):
        """No longer keep up the target up."""
        if self.reset_coil:
            self.reset_coil.disable()

    @event_handler(7)
    def event_knockdown(self, **kwargs):
        """Handle knockdown control event."""
        del kwargs
        self.knockdown()

    def knockdown(self):
        """Pulse the knockdown coil to knock down this drop target."""
        if self.knockdown_coil and not self.machine.switch_controller.is_active(self.config['switch']):
            self._ignore_switch_hits_for(ms=self.config['ignore_switch_ms'])
            self.knockdown_coil.pulse(max_wait_ms=self.config['knockdown_coil_max_wait_ms'])

    def _update_state_from_switch(self, reconcile=False, **kwargs):
        del kwargs

        is_complete = self.machine.switch_controller.is_active(
            self.config['switch'])

        if self._in_ball_search or self._ignore_switch_hits:
            return

        if not reconcile:
            self.config['playfield'].mark_playfield_active_from_device_action()

        if is_complete != self.complete:

            if is_complete:
                self._down()
            else:
                self._up()

            self._update_banks()

    def _down(self):
        self.complete = True
        self.machine.events.post('drop_target_' + self.name + '_down', device=self)
        '''event: drop_target_(name)_down
        desc: The drop target with the (name) has just changed to the "down"
        state.'''

    def _up(self):
        self.complete = False
        self.machine.events.post('drop_target_' + self.name + '_up', device=self)
        '''event: drop_target_(name)_up
        desc: The drop target (name) has just changed to the "up" state.'''

    def _update_banks(self):
        for bank in self.banks:
            bank.member_target_change()

    def add_to_bank(self, bank):
        """Add this drop target to a drop target bank.

         This allows the bank to update its status based on state changes to this drop target.

        Args:
        ----
            bank: DropTargetBank object to add this drop target to.
        """
        self.banks.add(bank)

    def external_reset_from_bank(self):
        """Handle the reset from our bank.

        The bank might pulse the coil from this device or it might have a
        separate reset coil which will trigger a reset on switch of this
        device.
        Make sure we do not mark the playfield as active.
        """
        if self.machine.switch_controller.is_active(self.config['switch']):
            self._ignore_switch_hits_for(ms=self.config['ignore_switch_ms'])

    def remove_from_bank(self, bank):
        """Remove the DropTarget from a bank.

        Args:
        ----
            bank: DropTargetBank object to remove
        """
        self.banks.remove(bank)

    @event_handler(1)
    def event_reset(self, **kwargs):
        """Handle reset control event."""
        del kwargs
        self.reset()

    def reset(self):
        """Reset this drop target.

        If this drop target is configured with a reset coil, then this method
        will pulse that coil. If not, then it checks to see if this drop target
        is part of a drop target bank, and if so, it calls the reset() method of
        the drop target bank.

        This method does not reset the target profile, however, the switch event
        handler should reset the target profile on its own when the drop target
        physically moves back to the up position.
        """
        if self.reset_coil and self.machine.switch_controller.is_active(self.config['switch']):
            self._ignore_switch_hits_for(ms=self.config['ignore_switch_ms'])
            self.reset_coil.pulse(max_wait_ms=self.config['reset_coil_max_wait_ms'])


class DropTargetBankState(Enum):

    """States of the drop target bank."""

    UNKNOWN = "unknown"
    UP = "up"
    DOWN = "down"
    MIXED = "mixed"


@DeviceMonitor("complete", "down", "up", "state")
class DropTargetBank(SystemWideDevice, ModeDevice):

    """A bank of drop targets in a pinball machine by grouping together multiple `DropTarget` class devices."""

    config_section = 'drop_target_banks'
    collection = 'drop_target_banks'
    class_label = 'drop_target_bank'

    def __init__(self, machine: "MachineController", name: str) -> None:
        """Initialise drop target bank."""
        super().__init__(machine, name)

        self.drop_targets = list()          # type: List[DropTarget]
        self.reset_coil = None              # type: Optional[Driver]
        self.reset_coils = set()            # type: Set[Driver]
        self.complete = False
        self.state = DropTargetBankState.UNKNOWN
        self.down = 0
        self.up = 0
        self.delay = DelayManager(machine)
        self._ignore_switch_hits = False

    @property
    def can_exist_outside_of_game(self):
        """Return true if this device can exist outside of a game."""
        return True

    async def _initialize(self):
        await super()._initialize()
        self.drop_targets = self.config['drop_targets']
        self.reset_coil = self.config['reset_coil']
        self.reset_coils = self.config['reset_coils']

    def device_loaded_in_mode(self, mode: Mode, player: Player):
        """Add targets."""
        self._add_targets_to_bank()

    async def device_added_system_wide(self):
        """Add targets."""
        await super().device_added_system_wide()
        self._add_targets_to_bank()

    def _add_targets_to_bank(self):
        """Add targets to bank."""
        for target in self.drop_targets:
            target.add_to_bank(self)

        self.member_target_change()

        self.debug_log('Drop Targets: %s', self.drop_targets)

    @event_handler(5)
    def event_reset(self, **kwargs):
        """Handle reset control event."""
        del kwargs
        self.reset()

    def reset(self):
        """Reset this bank of drop targets.

        This method has some intelligence to figure out what coil(s) it should
        fire. It builds up a set by looking at its own reset_coil and
        reset_coils settings, and also scanning through all the member drop
        targets and collecting their coils. Then it pulses each of them. (This
        coil list is a "set" which means it only sends a single pulse to each
        coil, even if each drop target is configured with its own coil.)
        """
        self.debug_log('Resetting')

        if self.down == 0:
            self.info_log('All targets are already up. Will not reset bank.')
            return

        self.info_log('%s targets are down. Will reset those.', self.down)

        # figure out all the coils we need to pulse
        coils = set()       # type: Set[Driver]

        for drop_target in self.drop_targets:
            # add all reset coil for targets which are down
            if drop_target.reset_coil and drop_target.complete:
                coils.add(drop_target.reset_coil)

            # tell the drop target that we are going to reset it physically
            drop_target.external_reset_from_bank()

        for coil in self.reset_coils:
            coils.add(coil)

        if self.reset_coil:
            coils.add(self.reset_coil)

        if self.config['ignore_switch_ms']:
            self._ignore_switch_hits = True
            self.delay.add(ms=self.config['ignore_switch_ms'],
                           callback=self._restore_switch_hits,
                           name='ignore_hits')

        # now pulse them
        for coil in coils:
            self.debug_log('Pulsing reset coils: %s', coils)
            coil.pulse(max_wait_ms=self.config['reset_coil_max_wait_ms'])

    def _restore_switch_hits(self):
        self._ignore_switch_hits = False
        self.member_target_change()

    def member_target_change(self):
        """Handle that a member drop target has changed state.

        This method causes this group to update its down and up counts and
        complete status.
        """
        if self._ignore_switch_hits:
            return

        self.down = 0
        self.up = 0

        for target in self.drop_targets:
            if target.complete:
                self.down += 1
            else:
                self.up += 1

        self.debug_log(
            'Member drop target status change: Up: %s, Down: %s,'
            ' Total: %s', self.up, self.down,
            len(self.drop_targets))

        if self.down == len(self.drop_targets):
            self._bank_down()
        elif not self.down:
            self._bank_up()
        else:
            self._bank_mixed()

    def _bank_down(self):
        if self.state == DropTargetBankState.DOWN:
            return
        self.state = DropTargetBankState.DOWN
        self.complete = True
        self.debug_log('All targets are down')

        if self.config['reset_on_complete']:
            self.debug_log("Reset on complete after %s", self.config['reset_on_complete'])
            self.delay.add(self.config['reset_on_complete'], self.reset)

        self.machine.events.post('drop_target_bank_' + self.name + '_down')
        '''event: drop_target_bank_(name)_down
        desc: Every drop target in the drop target bank called
        (name) is now in the "down" state. This event is
        only posted once, when all the drop targets are down.'''

    def _bank_up(self):
        if self.state == DropTargetBankState.UP:
            return
        self.state = DropTargetBankState.UP
        self.complete = False
        self.debug_log('All targets are up')
        self.machine.events.post('drop_target_bank_' + self.name + '_up')
        '''event: drop_target_bank_(name)_up
        desc: Every drop target in the drop target bank called
        (name) is now in the "up" state. This event is
        only posted once, when all the drop targets are up.'''

    def _bank_mixed(self):
        if self.state == DropTargetBankState.MIXED:
            return
        self.state = DropTargetBankState.MIXED
        self.complete = False
        self.machine.events.post('drop_target_bank_' + self.name + '_mixed',
                                 down=self.down)
        '''event: drop_target_bank_(name)_mixed
        desc: The drop targets in the drop target bank
        (name) are in a "mixed" state, meaning that they're
        not all down or not all up. This event is posted every time a member
        drop target changes but the overall bank is not not complete.'''

    def device_removed_from_mode(self, mode):
        """Remove targets which were added in this mode."""
        for target in self.drop_targets:
            target.remove_from_bank(self)
