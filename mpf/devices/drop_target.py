""" Contains the base classes for drop targets and drop target banks."""

from mpf.system.device import Device
from mpf.system.config import Config


class DropTarget(Device):
    """Represents a single drop target in a pinball machine.

    Args: Same as the `Target` parent class"""

    config_section = 'drop_targets'
    collection = 'drop_targets'
    class_label = 'drop_target'

    def __init__(self, machine, name, config, collection=None, validate=True):
        super().__init__(machine, name, config, collection,
                         validate=validate)

        self.complete = False
        self.reset_coil = self.config['reset_coil']
        self.knockdown_coil = self.config['knockdown_coil']
        self.banks = set()

        # can't read the switch until the switch controller is set up
        self.machine.events.add_handler('init_phase_4',
                                        self._update_state_from_switch)
        self.machine.events.add_handler('init_phase_4',
                                        self._register_switch_handlers)

    def _register_switch_handlers(self):
        # register for notification of switch state
        # this is in addition to the parent since drop targets track
        # self.complete in separately

        self.machine.switch_controller.add_switch_handler(
            self.config['switch'].name,
            self._update_state_from_switch, 0)
        self.machine.switch_controller.add_switch_handler(
            self.config['switch'].name,
            self._update_state_from_switch, 1)

    def knockdown(self, **kwargs):
        """Pulses the knockdown coil to knock down this drop target."""
        if self.knockdown_coil:
            self.knockdown_coil.pulse()

    def _update_state_from_switch(self):
        if self.machine.switch_controller.is_active(
                self.config['switch'].name):
            self._down()
        else:
            self._up()

        self._update_banks()

    def _down(self):
        self.complete = True
        self.machine.events.post(self.name + '_down')

    def _up(self):
        self.complete = False
        self.machine.events.post(self.name + '_up')

    def _update_banks(self):
        for bank in self.banks:
            bank.member_target_change()

    def add_to_bank(self, bank):
        """Adds this drop target to a drop target bank, which allows the bank to
        update its status based on state changes to this drop target.

        Args:
            bank: DropTargetBank object to add this drop target to.

        """
        self.banks.add(bank)

    def reset(self, **kwargs):
        """Resets this drop target.

        If this drop target is configured with a reset coil, then this method
        will pulse that coil. If not, then it checks to see if this drop target
        is part of a drop target bank, and if so, it calls the reset() method of
        the drop target bank.

        This method does not reset the target profile, however, the switch event
        handler should reset the target profile on its own when the drop target
        physically moves back to the up position.

        """

        if self.reset_coil:
            self.reset_coil.pulse()


class DropTargetBank(Device):
    """Represents a bank of drop targets in a pinball machine by grouping
    together multiple `DropTarget` class devices.

    """
    config_section = 'drop_target_banks'
    collection = 'drop_target_banks'
    class_label = 'drop_target_bank'

    def __init__(self, machine, name, config, collection=None, validate=True):
        super().__init__(machine, name, config, collection,
                         validate=validate)

        self.drop_targets = list()
        self.reset_coil = None
        self.reset_coils = set()
        self.complete = False
        self.down = 0
        self.up = 0

        self.drop_targets = self.config['drop_targets']
        self.reset_coil = self.config['reset_coil']
        self.reset_coils = self.config['reset_coils']

        for target in self.drop_targets:
            target.add_to_bank(self)

        self.member_target_change()

        if self.debug:
            self.log.debug('Drop Targets: %s', self.drop_targets)

    def reset(self, **kwargs):
        """Resets this bank of drop targets.

        This method has some intelligence to figure out what coil(s) it should
        fire. It builds up a set by looking at its own reset_coil and
        reset_coils settings, and also scanning through all the member drop
        targets and collecting their coils. Then it pulses each of them. (This
        coil list is a "set" which means it only sends a single pulse to each
        coil, even if each drop target is configured with its own coil.)

        """
        if self.debug:
            self.log.debug('Resetting')

        # figure out all the coils we need to pulse
        coils = set()

        for drop_target in self.drop_targets:
            if drop_target.reset_coil:
                coils.add(drop_target.reset_coil)

        for coil in self.reset_coils:
            coils.add(coil)

        if self.reset_coil:
            coils.add(self.reset_coil)

        # now pulse them
        for coil in coils:

            if self.debug:
                self.log.debug('Pulsing reset coils: %s', coils)

            coil.pulse()

    def member_target_change(self):
        """A member drop target has changed state.

        This method causes this group to update its down and up counts and
        complete status.

        """
        self.down = 0
        self.up = 0

        for target in self.drop_targets:
            if target.complete:
                self.down += 1
            else:
                self.up += 1

        if self.debug:
            self.log.debug(
                'Member drop target status change: Up: %s, Down: %s,'
                ' Total: %s', self.up, self.down,
                len(self.drop_targets))

        if self.down == len(self.drop_targets):
            self._bank_down()
        if not self.down:
            self._bank_up()
        else:
            self._bank_mixed()

    def _bank_down(self):
        self.complete = True
        if self.debug:
            self.log.debug('All targets are down')

        self.machine.events.post(self.name + '_down')

    def _bank_up(self):
        self.complete = False
        if self.debug:
            self.log.debug('All targets are up')
        self.machine.events.post(self.name + '_up')

    def _bank_mixed(self):
        self.complete = False
        self.machine.events.post(self.name + '_mixed', down=self.down)
