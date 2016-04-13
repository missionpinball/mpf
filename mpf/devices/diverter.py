"""Contains the base class for diverter devices."""

from collections import deque
from mpf.core.delays import DelayManager
from mpf.core.system_wide_device import SystemWideDevice


class Diverter(SystemWideDevice):
    """Represents a diverter in a pinball machine.

    Args: Same as the Device parent class.
    """

    config_section = 'diverters'
    collection = 'diverters'
    class_label = 'diverter'

    def __init__(self, machine, name):
        super().__init__(machine, name)

        self.delay = DelayManager(machine.delayRegistry)

        # Attributes
        self.active = False
        self.enabled = False
        self.platform = None

        self.diverting_ejects_count = 0
        self.eject_state = False
        self.eject_attempt_queue = deque()

        self.trigger_type = 'software'  # 'software' or 'hardware'
        # TODO: make hardware the only options and let the platform do the work

        # Create a list of ball device objects when active and inactive. We need
        # this because ball eject attempts pass the target device as an object
        # rather than by name.

    def _initialize(self):
        # register for feeder device eject events
        for feeder_device in self.config['feeder_devices']:
            self.machine.events.add_handler(
                'balldevice_' + feeder_device.name +
                '_ball_eject_attempt',
                self._feeder_eject_attempt)

            self.machine.events.add_handler(
                'balldevice_' + feeder_device.name +
                '_ball_eject_failed',
                self._feeder_eject_count_decrease)

            self.machine.events.add_handler(
                'balldevice_' + feeder_device.name +
                '_ball_eject_success',
                self._feeder_eject_count_decrease)

        self.machine.events.add_handler('init_phase_3',
                                        self._register_switches)

        self.platform = self.config['activation_coil'].platform

    def _register_switches(self):
        # register for deactivation switches
        for switch in self.config['deactivation_switches']:
            self.machine.switch_controller.add_switch_handler(
                    switch.name, self.deactivate)

        # register for disable switches:
        for switch in self.config['disable_switches']:
            self.machine.switch_controller.add_switch_handler(
                    switch.name, self.disable)

    def enable(self, auto=False, **kwargs):
        """Enables this diverter.

        Args:
            auto: Boolean value which is used to indicate whether this
                diverter enabled itself automatically. This is passed to the
                event which is posted.
            **kwargs: unused

        If an 'activation_switches' is configured, then this method writes a
        hardware autofire rule to the pinball controller which fires the
        diverter coil when the switch is activated.

        If no `activation_switches` is specified, then the diverter is activated
        immediately.

        """
        del kwargs
        self.enabled = True

        self.machine.events.post('diverter_' + self.name + '_enabling',
                                 auto=auto)
        '''event: diverter_(name)_enabling
        desc: The diverter called (name) is enabling itself. Note that if this
            diverter has ``activation_switches:`` configured, it will not
            physically activate until one of those switches is hit. Otherwise
            this diverter will activate immediately.

        args:
            auto: Boolean which indicates whether this diverter enabled itself
                automatically for the purpose of routing balls to their proper
                location(s).
        '''

        if self.config['activation_switches']:
            self.enable_switches()
        else:
            self.activate()

    def disable(self, auto=False, **kwargs):
        """Disables this diverter.

        This method will remove the hardware rule if this diverter is activated
        via a hardware switch.

        Args:
            auto: Boolean value which is used to indicate whether this
                diverter disabled itself automatically. This is passed to the
                event which is posted.
            **kwargs: This is here because this disable method is called by
                whatever event the game programmer specifies in their machine
                configuration file, so we don't know what event that might be
                or whether it has random kwargs attached to it.
        """
        del kwargs
        self.enabled = False

        self.machine.events.post('diverter_' + self.name + '_disabling',
                                 auto=auto)
        '''event: diverter_(name)_disabling
        desc: The diverter called (name) is disabling itself. Note that if this
            diverter has ``activation_switches:`` configured, it will not
            physically deactivate now, instead deactivating based on switch
            hits and timing. Otherwise this diverter will deactivate immediately.

        args:
            auto: Boolean which indicates whether this diverter disabled itself
                automatically for the purpose of routing balls to their proper
                location(s).
        '''

        self.log.debug("Disabling Diverter")
        if self.config['activation_switches']:
            self.disable_switches()
        # if there is no deactivation way
        if not (self.config['activation_time'] or self.config['deactivation_switches'] or
                    self.config['deactivate_events']):
            self.deactivate()

    def activate(self, **kwargs):
        """Physically activates this diverter's coil."""
        del kwargs
        self.log.debug("Activating Diverter")
        self.active = True

        self.machine.events.post('diverter_' + self.name + '_activating')
        if self.config['type'] == 'pulse':
            self.config['activation_coil'].pulse()
        elif self.config['type'] == 'hold':
            self.config['activation_coil'].enable()
        self.schedule_deactivation()

    def deactivate(self, **kwargs):
        """Deactivates this diverter.

        This method will disable the activation_coil, and (optionally) if it's
        configured with a deactivation coil, it will pulse it.
        """
        del kwargs
        self.log.debug("Deactivating Diverter")
        self.active = False

        if self.config['activation_time']:
            self.delay.remove('deactivate_timed')

        self.machine.events.post('diverter_' + self.name + '_deactivating')
        '''event: diverter_(name)_deactivating
        desc: The diverter called (name) is deativating itself.

        '''
        self.config['activation_coil'].disable()

        if self.config['deactivation_coil']:
            self.config['deactivation_coil'].pulse()

    def schedule_deactivation(self):
        """Schedules a delay to deactivate this diverter.
        """
        if self.config['activation_time']:
            self.delay.add(name='deactivate_timed', ms=self.config['activation_time'],
                           callback=self.deactivate)

    def enable_switches(self):
        if self.trigger_type == 'hardware':
            self.enable_hw_switches()
        else:
            self.enable_sw_switches()

    def disable_switches(self):
        if self.trigger_type == 'hardware':
            self.disable_hw_switches()
        else:
            self.disable_sw_switches()

    def enable_hw_switches(self):
        # TODO: not used. probably broken
        """Enables the hardware switch rule which causes this diverter to
        activate when the switch is hit.

        This is typically used for diverters on loops and ramps where you don't
        want the diverter to phsyically activate until the ramp entry switch is
        activated.

        If this diverter is configured with a activation_time, this method will
        also set switch handlers which will set a delay to deactivate the
        diverter once the activation activation_time expires.

        If this diverter is configured with a deactivation switch, this method
        will set up the switch handlers to deactivate the diverter when the
        deactivation switch is activated.
        """
        self.log.debug("Enabling Diverter for hw switch: %s",
                       self.config['activation_switches'])
        if self.config['type'] == 'hold':

            for switch in self.config['activation_switches']:

                self.platform.set_hw_rule(
                        sw_name=switch.name,
                        sw_activity=1,
                        driver_name=self.config['activation_coil'].name,
                        driver_action='hold',
                        disable_on_release=False,
                        **self.config)

                # If there's a activation_time then we need to watch for the hw
                # switch to be activated so we can disable the diverter

                if self.config['activation_time']:
                    self.machine.switch_controller.add_switch_handler(
                            switch.name,
                            self.schedule_deactivation)

        elif self.config['type'] == 'pulse':

            for switch in self.config['activation_switches']:
                self.platform.set_hw_rule(
                        sw_name=switch.name,
                        sw_activity=1,
                        driver_name=self.config['activation_coil'].name,
                        driver_action='pulse',
                        disable_on_release=False,
                        **self.config)

    def enable_sw_switches(self):
        self.log.debug("Enabling Diverter sw switches: %s",
                       self.config['activation_switches'])

        for switch in self.config['activation_switches']:
            self.machine.switch_controller.add_switch_handler(
                    switch_name=switch.name, callback=self.activate)

    def disable_sw_switches(self):
        self.log.debug("Disabling Diverter sw switches: %s",
                       self.config['activation_switches'])

        for switch in self.config['activation_switches']:
            self.machine.switch_controller.remove_switch_handler(
                    switch_name=switch.name, callback=self.activate)

    def disable_hw_switches(self):
        # TODO: not used
        """Removes the hardware rule to disable the hardware activation switch
        for this diverter.
        """
        for switch in self.config['activation_switches']:
            self.platform.clear_hw_rule(switch.name)

            # todo this should not clear all the rules for this switch

    def _feeder_eject_count_decrease(self, target, **kwargs):
        del target
        del kwargs
        self.diverting_ejects_count -= 1
        if self.diverting_ejects_count <= 0:
            self.diverting_ejects_count = 0

            # If there are ejects waiting for the other target switch diverter
            if len(self.eject_attempt_queue) > 0:
                if not self.eject_state:
                    self.eject_state = True
                    self.log.debug(
                        "Enabling diverter since eject target is on the "
                        "active target list")
                    self.enable()
                elif self.eject_state:
                    self.eject_state = False
                    self.log.debug(
                        "Enabling diverter since eject target is on the "
                        "inactive target list")
                    self.disable()
                # And perform those ejects
                while len(self.eject_attempt_queue) > 0:
                    self.diverting_ejects_count += 1
                    queue = self.eject_attempt_queue.pop()
                    queue.clear()
            elif self.active and not self.config['activation_time']:
                # if diverter is active and no more ejects are ongoing
                self.deactivate()

    def _feeder_eject_attempt(self, queue, target, **kwargs):
        # Event handler which is called when one of this diverter's feeder
        # devices attempts to eject a ball. This is what allows this diverter
        # to get itself in the right position to send the ball to where it needs
        # to go.

        # Since the 'target' kwarg is going to be an object, not a name, we need
        # to figure out if this object is one of the targets of this diverter.
        del kwargs
        self.log.debug("Feeder device eject attempt for target: %s", target)

        desired_state = None
        if target in self.config['targets_when_active']:
            desired_state = True

        elif target in self.config['targets_when_inactive']:
            desired_state = False

        if desired_state is None:
            self.log.debug("Feeder device ejects to an unknown target: %s. "
                           "Ignoring!", target.name)
            return

        if self.diverting_ejects_count > 0 and self.eject_state != desired_state:
            self.log.debug("Feeder devices tries to eject to a target which "
                           "would require a state change. Postponing that "
                           "because we have an eject to the other side")
            queue.wait()
            self.eject_attempt_queue.append(queue)
            return

        self.diverting_ejects_count += 1

        if desired_state:
            self.log.debug("Enabling diverter since eject target is on the "
                           "active target list")
            self.eject_state = desired_state
            self.enable()
        elif not desired_state:
            self.log.debug("Enabling diverter since eject target is on the "
                           "inactive target list")
            self.eject_state = desired_state
            self.disable()
