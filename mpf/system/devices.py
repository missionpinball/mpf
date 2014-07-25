"""Contains the classes for our various playfield devices, including:

* Flippers
* Autofire Coils (Coils that automatically fire based on switch activity, like
pop bumpers or slingshots.)
* Ball Devices (Anything that can hold a ball, like the trough, VUKs, the
plunger lane, etc.)

"""
# devices.py
# Mission Pinball Framework
# Written by Brian Madden & Gabe Knuth
# Released under the MIT License. (See license info at the end of this file.)

# Documentation and more info at http://missionpinball.com/framework

import logging
from collections import defaultdict
from mpf.system.tasks import DelayManager


class Device(object):
    """Parent class for all devices in a pinball machine.

    Devices are the "lowest level" hardware in a machine, including lights,
    coils, switches.

    """

    def __init__(self, machine, name, config, collection=-1):

        # todo this code is similar to the HardwareObject class. Wonder if
        # there's any value in subclassing and/or combining?
        self.machine = machine
        self.name = name
        self.config = config
        self.tags = []
        self.label = ""

        if 'tags' in config:
            self.tags = self.machine.string_to_list(config['tags'])
        if 'label' in config:
            self.label = config['label']  # todo change to multi lang
        # todo more pythonic way, like self.label = blah if blah?

        # Add this instance to our dictionary for this type of device
        if collection != -1:
            # Have to use -1 instead of None to catch an empty collection dict
            collection[name] = self


class Flipper(Device):
    """Represents a flipper in a pinball machine. Subclass of Device.

    Contains several methods for actions that can be performed on this flipper,
    like :meth:`enable`, :meth:`disable`, etc.

    Flippers have several options, including player buttons, EOS swtiches,
    multiple coil options (pulsing, hold coils, etc.)

    More details: http://missionpinball.com/docs/devices/flippers/

    Parameters
    ----------

    machine: machine object
        A reference to the machine controller instance.

    name: string
        The name you'll refer to this flipper object as.


    config: dictionary
        A dictionary that holds the configuration values which specify how
        this flipper should be configured. If this is None, it will use the
        system config settings that were read in from the config files when
        the machine was reset.

    collection: bool


    """

    def __init__(self, machine, name, config, collection=None):
        super(Flipper, self).__init__(machine, name, config, collection)
        self.log = logging.getLogger('Flipper.' + name)
        self.log.debug("Creating Flipper device")

        # todo convert to dict
        self.no_hold = False
        self.strength = 100
        self.inverted = False

        if config:
            config = defaultdict(lambda: None, config)
            self.configure(config)

    def configure(self, config=None):
        """Configures the flipper device.

        Parameters
        ----------

        config : dictionary
            A dictionary that holds the configuration values which specify how
            this flipper should be configured. If this is None, it will use the
            system config settings that were read in from the config files when
            the machine was reset.

        """
        if not config:
            pass  # todo add an error

        self.main_coil = self.machine.coils[config['main_coil']]
        self.activation_switch = self.machine.switches[config[
            'activation_switch']]
        # I don't love these if/then  statements. See the todo note in the
        # HardwareDict class of the hardware module
        if config['hold_coil']:
            self.hold_coil = self.machine.coils[config['hold_coil']]
        else:
            self.hold_coil = None

        if config['eos_switch']:
            self.eos_switch = self.machine.switches[config['eos_switch']]
        else:
            self.eos_switch = None

        self.hold_pwm = config['hold_pwm']
        self.use_eos = config['use_eos']
        self.label = config['label']

        self.flipper_coils = []
        self.flipper_coils.append(self.main_coil)
        if self.hold_coil:
            self.flipper_coils.append(self.hold_coil)

        self.flipper_switches = []
        self.flipper_switches.append(self.activation_switch.name)
        if self.eos_switch:
            self.flipper_switches.append(self.eos_switch.name)

    def enable(self):
        """Enables the flipper by writing the necessary hardware rules to the
        hardware controller.

        The hardware rules for coils can be kind of complex given all the
        options, so we've mapped all the options out here. We literally have
        methods to enable the various rules based on the rule letters here,
        which we've implemented below. Keeps it easy to understand. :)

        Two coils, using EOS switch to indicate the end of the power stroke:
        Rule  Type     Coil  Switch  Action
        A.    Enable   Main  Button  active
        D.    Enable   Hold  Button  active
        E.    Disable  Main  EOS     active
        F.    Disable  Main  Button  inactive
        G.    Disable  Hold  Button  inactive

        One coil, using EOS switch
        Rule  Type     Coil  Switch  Action
        A.    Enable   Main  Button  active
        H.    PWM      Main  EOS     active
        F.    Disable  Main  Button  inactive

        Two coils, not using EOS switch:
        Rule  Type     Coil  Switch  Action
        B.    Pulse    Main  Button  active
        D.    Enable   Hold  Button  active
        F.    Disable  Main  Button  inactive
        G.    Disable  Hold  Button  inactive

        One coil, not using EOS switch
        Rule  Type       Coil  Switch  Action
        C.    Pulse/PWM  Main  button  active
        F.    Disable    Main  button  inactive

        Use EOS switch for safety (for platforms that support mutiple switch
        rules). Note that this rule is the letter "i", not a numeral 1.
        I. Enable power if button is active and EOS is not active
        """

        # First make sure we've read in the configuration for this flipper
        if not self.main_coil:
            self.configure()

        # Now let's lets apply the proper hardware rules for our config

        if self.hold_coil and self.use_eos and self.eos_switch:
            self._enable_flipper_rule_A()
            self._enable_flipper_rule_D()
            self._enable_flipper_rule_E()
            self._enable_flipper_rule_F()
            self._enable_flipper_rule_G()

        elif not self.hold_coil and self.use_eos and self.eos_switch:
            self._enable_flipper_rule_A()
            self._enable_flipper_rule_H()
            self._enable_flipper_rule_F()

        elif self.hold_coil and not self.use_eos:
            self._enable_flipper_rule_B()
            self._enable_flipper_rule_D()
            self._enable_flipper_rule_F()
            self._enable_flipper_rule_G()

        elif not self.hold_coil and not self.use_eos:
            self._enable_flipper_rule_C()
            self._enable_flipper_rule_F()

            # todo detect bad EOS and program around it

    def enable_no_hold(self):  # todo niy
        """Enables the flippers in 'no hold' mode.

        No Hold is a novelty mode where the flippers to not stay up even when
        the buttons are held in.

        This mode is not yet implemented.

        """

        self.no_hold = True
        self.enable()

    def enable_inverted(self):  # todo niy
        """Enables inverted flippers.

        Inverted flippers is a novelty mode where the left flipper button
        controls the right flippers and vice-versa.

        This mode is not yet implemented.

        """

        self.inverted = True
        self.enable()

    def enable_partial_power(self, percent):  # todo niy
        """Enables flippers which operated at less than full power.

        This is a novelty mode, like "weak flippers" from the Wizard of Oz.

        Parameters
        ----------

        percent : float
            Value between 0 and 1.0 which represents the percentage of power
            the flippers will be enabled at.

        This mode is not yet implemented.

        """
        self.power = percent
        self.enable()

    def disable(self):
        """Disables the flipper.

        This method makes it so the cabinet flipper buttons no longer control
        the flippers. Used when no game is active and when the player has
        tilted.

        """

        if self.flipper_switches:
            for switch in self.flipper_switches:
                    self.machine.platform.clear_hw_rule(switch)

    def _enable_flipper_rule_A(self):
        """
        Rule  Type     Coil  Switch  Action
        A.    Enable   Main  Button  active
        """
        self.machine.platform.set_hw_rule(sw_name=self.activation_switch.name,
                                       sw_activity='active',
                                       coil_name=self.main_coil.name,
                                       coil_action_time=-1,
                                       debounced=False)

    def _enable_flipper_rule_B(self):
        """
        Rule  Type     Coil  Switch  Action
        B.    Pulse    Main  Button  active
        """
        self.machine.platform.set_hw_rule(sw_name=self.activation_switch.name,
                                       sw_activity='active',
                                       coil_name=self.main_coil.name,
                                       coil_action_time=self.main_coil.
                                       pulse_time,
                                       pulse_time=self.main_coil.pulse_time,
                                       debounced=False)

    def _enable_flipper_rule_C(self):
        """
        Rule  Type       Coil  Switch  Action
        C.    Pulse/PWM  Main  button  active
        """
        self.machine.platform.set_hw_rule(sw_name=self.activation_switch.name,
                                       sw_activity='active',
                                       coil_name=self.main_coil.name,
                                       coil_action_time=-1,
                                       pulse_time=self.main_coil.pulse_time,
                                       pwm_on=self.main_coil.pwm_on,
                                       pwm_off=self.main_coil.pwm_off,
                                       debounced=False)

    def _enable_flipper_rule_D(self):
        """
        Rule  Type     Coil  Switch  Action
        D.    Enable   Hold  Button  active
        """
        self.machine.platform.set_hw_rule(sw_name=self.activation_switch.name,
                                       sw_activity='active',
                                       coil_name=self.hold_coil.name,
                                       coil_action_time=-1,
                                       debounced=False)

    def _enable_flipper_rule_E(self):
        """
        Rule  Type     Coil  Switch  Action
        E.    Disable  Main  EOS     active
        """
        self.machine.platform.set_hw_rule(sw_name=self.eos_switch.name,
                                       sw_activity='active',
                                       coil_name=self.main_coil.name,
                                       coil_action_time=0,
                                       debounced=False)

    def _enable_flipper_rule_F(self):
        """
        Rule  Type     Coil  Switch  Action
        F.    Disable  Main  Button  inactive
        """
        self.machine.platform.set_hw_rule(sw_name=self.activation_switch.name,
                                       sw_activity='inactive',
                                       coil_name=self.main_coil.name,
                                       coil_action_time=0,
                                       debounced=False)

    def _enable_flipper_rule_G(self):
        """
        Rule  Type     Coil  Switch  Action
        G.    Disable  Hold  Button  inactive
        """
        self.machine.platform.set_hw_rule(sw_name=self.activation_switch.name,
                                       sw_activity='inactive',
                                       coil_name=self.hold_coil.name,
                                       coil_action_time=0,
                                       debounced=False)

    def _enable_flipper_rule_H(self):
        """
        Rule  Type     Coil  Switch  Action
        H.    PWM      Main  EOS     active
        """
        self.machine.platform.set_hw_rule(sw_name=self.eos_switch.name,
                                       sw_activity='active',
                                       coil_name=self.main_coil.name,
                                       coil_action_time=-1,
                                       pwm_on=self.main_coil.pwm_on,
                                       pwm_off=self.main_coil.pwm_off)


class AutofireCoil(Device):
    """Base class for coils in the pinball machine which should fire
    automatically based on switch activity using hardware switch rules.

    Autofire coils are used when you want the coils to respond "instantly"
    without waiting for the lag of the python game code running on the host
    computer.

    Examples of Autofire Coils are pop bumpers, slingshots, and flippers.

    """

    def __init__(self, machine, name, config, collection=None):
        super(AutofireCoil, self).__init__(machine, name, config, collection)
        self.log = logging.getLogger('AutofireCoil.' + name)
        self.log.debug("Creating auto-firing coil rule: %s", name)

        # todo convert to dict
        self.switch = None
        self.switch_activity = 'active'
        self.coil = None
        self.coil_action_time = 0  # -1 for hold, 0 for disable, 1+ for pulse
        self.pulse_ms = 0
        self.pwm_on_ms = 0
        self.pwm_off_ms = 0
        self.delay = 0
        self.recycle_ms = 125
        self.debounced = False
        self.drive_now = False

        if config:
            self.configure(config)

    def configure(self, config=None):
        """Configures an autofire coil.

        Parameters
        ----------

        config : dictionary
            The configuration dictionary which contains all the settings this
            coil should be configured with.

        """
        if not config:
            self.log.error("No configuration received for AutofireCoil: %s",
                           self.name)

        # Required
        self.coil = config['coil']
        self.switch = config['switch']

        # Don't want to use defaultdict here because a lot of the config dict
        # items might have 0 as a legit value, so it makes 'if item:' not work

        # Translate 'active' / 'inactive' to hardware open (0) or closed (1)
        if 'switch activity' in config:
            self.switch_activity = config['switch_activity']

        if 'pulse_ms' in config:
            self.pulse_ms = config['pulse_ms']
        else:
            self.pulse_ms = self.machine.coils[config['coil']].pulse_time

        if 'pwm_on_ms' in config:
            self.pwm_on_ms = config['pwm_on_ms']
        else:
            self.pwm_on_ms = self.machine.coils[config['coil']].pwm_on

        if 'pwm_off_ms' in config:
            self.pwm_off_ms = config['pwm_off_ms']
        else:
            self.pwm_off_ms = self.machine.coils[config['coil']].pwm_off

        if 'coil_action_time' in config:
            self.coil_action_time = config['coil_action_time']
        else:
            self.coil_action_time = self.pulse_ms

        if 'delay' in config:
            self.delay = config['delay']

        if 'recycle_ms' in config:
            self.recycle_ms = config['recycle_ms']

        if 'debounced' in config:
            self.debounced = config['debounced']

        if 'drive_now' in config:
            self.drive_now = config['drive_now']

    def enable(self):
        """Enables the autofire coil rule."""
        if not self.coil:
            self.configure()

        self.machine.platform.set_hw_rule(sw_name=self.switch,
                                       sw_activity=self.switch_activity,
                                       coil_name=self.coil,
                                       coil_action_time=self.coil_action_time,
                                       pulse_time=self.pulse_ms,
                                       pwm_on=self.pwm_on_ms,
                                       pwm_off=self.pwm_off_ms,
                                       delay=self.delay,
                                       recycle_time=self.recycle_ms,
                                       debounced=self.debounced,
                                       drive_now=self.drive_now)

    def disable(self):
        """Disables the autofire coil rule."""
        self.machine.platform.clear_hw_rule(self.switch)


class BallDevice(Device):
    """Base class for a 'Ball Device' in a pinball machine.

    A ball device  is anything that can hold one or more balls, such as a
    trough, an eject hole, a VUK, a catapult, etc.

    Most (all?) machines will have at least two: the main trough (or wherever
    the balls end up when they drain), and the shooter lane.

    todo:
    whether they're 1-to-1 or virtual?
    trigger recount switch(es)
    manual eject only?
    found_new_ball / or ball count change?
    eject type: 1, all, manual?
    eject firing type: hold a coil, for how long, etc.
    what happens on eject? event on attempt. event on success?

    Parameters
    ----------

    name : string
        How you want to refer to this ball device.

    machine: machine controller instance
        A reference to the machine controller

    hw_dict : dict
        A reference to the hardware dictionary which holds a list of ball
        devices. (Note: this might change)

    config : dict
        A dictionary of settings which specify how this ball device should be
        set up. These settings typically come from the machine config files,
        but really they could come from anywhere. Refer to the config file
        reference for a description of these settings.

    """

    def __init__(self, machine, name, config, collection=None):
        super(BallDevice, self).__init__(machine, name, config, collection)
        self.log = logging.getLogger('BallDevice.' + name)
        self.log.debug("Creating Device")

        self.delay = DelayManager()

        # set our config defaults
        # todo lots of stuff here
        if 'ball_capacity' not in self.config:
            self.config['ball_capacity'] = 0
        if 'post_eject_delay_check' not in self.config:
            self.config['post_eject_delay_check'] = ".5s"  # todo make optional
        if 'ball_switches' not in self.config:
            self.config['ball_switches'] = None
        if 'ball_count_delay' not in self.config:
            self.config['ball_count_delay'] = "0.5s"
        if 'eject_coil' not in self.config:
            self.config['eject_coil'] = None
        if 'eject_switch' not in self.config:
            self.config['eject_switch'] = None  # todo what about devices w/o this?
        if 'entrance_switch' not in self.config:
            self.config['entrance_switch'] = None
        if 'jam_switch' not in self.config:
            self.config['jam_switch'] = None
        if 'eject_coil_hold_times' not in self.config:
            self.config['eject_coil_hold_times'] = None  # todo change to list
        if 'eject_target' not in self.config:
            self.config['eject_target'] = None
        if 'confirm_eject_type' not in self.config:
            self.config['confirm_eject_type'] = 'count'  # todo make optional?
        if 'confirm_eject_target' not in self.config:
            self.config['confirm_eject_target'] = None
        if 'eject_type' not in self.config:
            self.config['eject_type'] = 'single'
        if 'player_controlled_eject' not in self.config:
            self.config['player_controlled_eject'] = False  # todo change this
        if 'player_controlled_switch_tag' not in self.config:
            self.config['player_controlled_switch_tag'] = None  # todo change this
        if 'feeder_device' not in self.config:
            self.config['feeder_device'] = None

        # initialize our variables
        self.num_previous_balls_contained = 0
        self.num_balls_contained = 0
        self.eject_in_progress = 0
        self.ok_to_eject = False
        self.num_jam_sw_count = 0
        self.num_desired_balls = 0
        self.num_balls_to_eject = 0
        self.num_balls_to_eject_stealth = 0
        self.num_balls_to_auto_eject = 0
        self.num_new_balls_to_ignore = 0

        # now configure the device. Pass along a config dict if we got one
        self.configure(config=config)

    def configure(self, config=None):
        """Performs the actual configuration of the ball device based on the
        dictionary that was passed to it.

        """

        # Merge in any new changes that were just passed
        if config:
            self.config.update(config)

        self.log.debug("Configuring device with: %s", config)

        # now let the fun begin!

        # convert entries that might be multiple items into lists
        # todo should this be automatic based on having a comma in the item?
        self.config['ball_switches'] = self.machine.string_to_list(
            self.config['ball_switches'])

        if not self.config['ball_capacity']:
            self.config['ball_capacity'] = len(self.config['ball_switches'])

        # Register switch handlers for ball switch activity
        for switch in self.config['ball_switches']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch, state=1, ms=0,
                callback=self._ball_switch_handler)
        for switch in self.config['ball_switches']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch, state=0, ms=0,
                callback=self._ball_switch_handler)

        # Configure switch handlers for jam switch activity
        if self.config['jam_switch']:
            self.machine.switch_controller.add_switch_handler(
                switch_name=switch, state=1, ms=0,
                callback=self.configjam_switch_handler)
            # todo do I also need to add inactive and make a smarter
            # handler?

        # Set up the eject confirmation for this device
        if self.config['confirm_eject_type']:
            self.config['confirm_eject'] = True  # todo remove
            if self.config['confirm_eject_type'] == 'device':
                # watch for ball entry event on that device
                self.machine.events.add_handler(
                    'balldevice_' + self.config['confirm_eject_target'] +
                    '_ball_enter', self.eject_success)

            elif self.config['confirm_eject_type'] == 'switch':
                # watch for that switch to activate momentarily
                # todo support timed switch here?
                self.machine.switch_controller.add_switch_handler(
                    switch_name=self.config
                    ['confirm_eject_target'],
                    callback=self.eject_success,
                    state=1, ms=0)

            elif self.config['confirm_eject_type'] == 'playfield':
                # watch for live ball added event
                self.machine.events.add_handler('playfield_valid',
                                                   self.eject_success)

            elif self.config['confirm_eject_type'] == 'event':
                # watch for that event
                self.machine.events.add_handler(
                    self.config['confirm_eject_target'], self.eject_success)

            # Note for confirm_eject_type of "count", the code to handle
            # that is in eject()

            # todo add recount delay

        # Add event listeners for any player-controlled eject switches for
        # this ball device
        if self.config['player_controlled_eject']:
            self.machine.events.add_handler('sw_' +
                self.config['player_controlled_eject_tag'],
                handler=self.player_requests_eject)
            # todo combine the two above config items into one?

        # convert delay times in s or ms to game ticks
        if self.config['post_eject_delay_check']:
            self.config['post_eject_delay_check'] = \
                self.machine.timing.time_to_ticks(
                self.config['post_eject_delay_check'])

        if self.config['ball_count_delay']:
            self.config['ball_count_delay'] = \
                self.machine.timing.time_to_ticks(
                self.config['ball_count_delay'])

    def count_balls(self, process_balls=True):
        """Counts the balls in the device and (optionally) processes any
        new balls that came in.

        Parameters
        ----------

        process_balls : bool
            False means that it only updates the count value and does not
            process new balls. This is useful for the first count after a
            machine reset.

        """

        # todo check if a game is in progress. If not, process_balls = False

        self.log.debug("Received request to count balls."
                       " Process_balls = %s", process_balls)

        # todo look at this code. If we don't have ball switches, do we need
        # to do anything to count? Right not we just skip this all.
        if self.config['ball_switches']:

            ball_count = 0
            ball_change = 0
            self.num_previous_balls_contained = self.num_balls_contained
            self.log.debug("Previous number of balls: %s",
                             self.num_previous_balls_contained)

            for switch in self.config['ball_switches']:
                if self.machine.switch_controller.is_active(switch):
                    ball_count += 1
                    self.log.debug("Active switch: %s", switch)
            self.log.debug("Counted %s balls", ball_count)

            self.num_balls_contained = ball_count
            ball_change = ball_count - self.num_previous_balls_contained
            self.log.debug("Ball count change for device '%s': %s", self.name,
                           ball_change)
            if ball_change:
                # if there is a change in the ball count, either up or down, we
                # want to notify the ball controller
                self.machine.ball_controller.ball_contained_count_change(
                    change=ball_change)

            if ball_change < 0 and self.eject_in_progress and \
                    self.config['confirm_eject_type'] == 'count':
                # todo or if the pf is already valid and conf type is pf, then...
                # device has lost a ball, eject is in progress, and we need
                # to verify the eject via a count, so we have a successful eject
                self.eject_success(ball_change)

            # set ok_to_eject
            self.ok_to_eject = False
            if self.machine.switch_controller.is_active(
                    self.config['eject_switch']):
                if self.config['eject_target'] == 'balldevice':
                    if self.machine.balldevices[self.config['eject_target']].\
                            ball_capacity - self.machine.balldevices[self.config[
                            'eject_target']].num_balls_contained > 0:
                        # We have room in the target
                        self.ok_to_eject = True
                else:
                    self.ok_to_eject = True

            if process_balls:

                if ball_change < 0 and not self.eject_in_progress:
                    # Device has randomly lost a ball?
                    self.log.debug("Weird, we're missing a ball but there's "
                                   "not an eject in progress, so let's do a "
                                   "full count.")
                    self.machine.ball_controller.ball_update_all_counts()

                elif ball_change > 0:
                    # Device has gained a ball
                    self._found_new_ball(ball_change)

            if self.num_balls_to_eject and self.ok_to_eject:
                # if we have a pending request to eject a ball, do it now
                self.eject()
        else:
            # we don't have ball switches
            ball_count = self.num_balls_contained

        return ball_count

    def is_full(self):
        """Checks to see if this device is "full", meaning it is holding
        either the max number of balls it can hold, or it's holding all the
        known balls in the machine.

        """

        if self.num_balls_contained == self.ball_capacity:
            return True
        elif self.num_balls_contained == \
                self.machine.ball_controller.num_balls_known:
            return True
        else:
            return False

    def _ball_switch_handler(self):
        # We just had a ball switch change.
        # If this device is configured for a delay before counting,
        # wait and/or reset that delay.

        # We don't know if we can eject until everything settles
        self.ok_to_eject = False

        if self.config['ball_count_delay']:
            self.log.debug("%s switch just changed state. Will count after "
                           "%s ticks", self.name,
                             self.config['ball_count_delay'])
            self.delay.add(name='ball_count',
                           delay=self.config['ball_count_delay'],
                           callback=self.count_balls)
        else:
            # If no delay is set then just count the balls now
            self.count_balls()

    def jam_switch_handler(self):
        """The device's jam switch was just activated.

        This method is typically used with trough devices to figure out if
        balls fell back in.

        """
        self.num_jam_sw_count += 1
        self.log.debug("Ball device %s jam switch hit. New count: %s",
                       self.name, self.num_jam_sw_count)

    def _found_new_ball(self, new_balls=1):
        """At least one new ball entered our ball device."""

        if not new_balls:
            return  # Just in case we somehow got here but there aren't
                    # actually any new balls.

        self.log.debug("Found %s new ball(s) in ball device: %s",
                         new_balls, self.name)

        if self.machine.ball_controller.flag_ball_search_in_progress:
            self.machine.ball_controller.ball_search_end()
        # todo move this to an event

        if self.num_new_balls_to_ignore:
            new_balls -= 1
            self.num_new_balls_to_ignore -= 1
            # if we still have new balls then loop back through
            if new_balls > 0:
                self._found_new_ball(new_balls)
            return  # if that was our only new ball then abort

        if self.eject_in_progress:
            self.log.debug("Ball Device %s received a new ball while its "
                             "eject_in_progress flag was set. So we think "
                             "the ball fell back in.", self.name)
            # Subtract our failed eject from the new_ball count
            new_balls -= 1
            # Retry the eject, but force it since our flag is set
            # todo or reset the flag and try again??
            self.eject(force=True)

        # At this point we can *finally* start processing our new balls
        for i in range(new_balls):  # we want to fire this once for each ball
            self.machine.events.post('balldevice_' + self.name + '_ball_enter')

    def eject(self, num=0, force=False):
        """Eject a ball from the device

        Parameter 'force' will force the eject even if eject_in_progress
        is not zero

        """
        self.log.debug("Received request to eject %s ball(s), force=%s",
                         num, force)
        self.log.debug("----Previous eject_in_progress count: %s",
                         self.eject_in_progress)
        self.log.debug("----ok_to_eject: %s",
                         self.ok_to_eject)
        self.log.debug("----balls contained: %s", self.num_balls_contained)

        self.num_balls_to_eject += num
        self.log.debug("----total balls to eject: %s", self.num_balls_to_eject)
        self.machine.events.post('balldevice_' + self.name +
                                         '_ball_eject_request')
        if self.num_balls_to_eject:

            if not self.ok_to_eject:
                self.stage_ball()

            if (self.ok_to_eject and not self.eject_in_progress) or\
                    (force is True):
                # todo cancel any checks sinc we're about to eject

            # add the support for stealth and auto

                self.eject_in_progress += num
                if self.config['jam_switch']:
                    self.num_jam_sw_count = 0  # todo if we're using this
                    if self.machine.switch_controller.is_active(
                            self.config['jam_switch']):
                        self.num_jam_sw_count += 1
                        # catches if the ball is blocking the switch to begin
                        # with
                self.machine.events.post('balldevice_' + self.name +
                                         '_ball_eject_attempt')
                self.machine.coils[self.config['eject_coil']].pulse()
                # todo check for release time?
                self.num_balls_contained -= 1  # todo do we do this here?
                self.machine.ball_controller.ball_contained_count_change(
                    change=-1)

        if self.config['confirm_eject_type'] is 'switch' or\
                (self.config['confirm_eject_type'] is 'playfield' and\
                 self.machine.ball_controller.num_balls_in_play > 0):
            # We need to set a delay to confirm the eject. We can go right into
            # the eject_sucess from here because if the ball falls back in,
            # the ball switch handler will cause a recound and figure it out.
            # We only do this if the device is configured to confirm eject
            # via a 'count,' or if it's set to confirm eject via the playfield
            # but there's already a ball in play.
            self.delay.add(name=self.name + '_confirm_eject',
                           event_type=None,
                           delay=self.config['post_eject_delay_check'],
                           handler=self.eject_success)

        if not self.config['confirm_eject_type']:
            self.eject_success()
            # todo do we need to pass a value to the eject success?

    def stage_ball(self):
        """Used to make sure the device has a ball 'staged' and ready to
        eject.

        """
        self.log.debug("Staging Ball")
        if self.machine.switch_controller.is_inactive(
                self.config['eject_switch']):
            self.log.debug("I don't have a ball ready")
            if self.config['feeder_device']:
                # get a ball from the feeder device
                self.log.debug("Requesting a ball from feeder device: '%s'",
                               self.config['feeder_device'])
                self.machine.balldevices[self.config['feeder_device']].\
                    eject(1)
            else:
                self.log.warning("No feeder device configured! Stage failed!")
        else:
            self.log.debug("Ball is already staged and ready to go")

    def eject_success(self, balls_ejected=1):
        """We got an eject success for this device."""

        # Since there are many ways we can get here, let's first make sure we
        # actually had an eject in progress
        if self.eject_in_progress:
            self.log.debug("Confirmed %s ball(s) ejected successfully",
                           balls_ejected)

            # cancel any pending eject check since we're confirming it now
            self.delay.remove(self.name + '_confirm_eject')
            self.eject_in_progress -= balls_ejected
            self.num_jam_sw_count = 0  # todo add if we're using this
            self.num_balls_to_eject -= balls_ejected

            # todo cancel post eject check delay
            # todo was inc live?

            self.machine.events.post('balldevice_' + self.name +
                                     '_ball_eject_success',
                                     balls_ejected=balls_ejected)
            # need to add num balls to eject confirm

            if self.num_balls_to_eject_stealth:
                self.num_balls_to_eject_stealth -= 1
                # change to count this down
            elif 'ball_add_live' in self.tags:
                self.machine.events.post('ball_add_live_success')
                # change to add num live?

            # if we still have balls to eject, then loop through that
            if self.num_balls_to_eject:
                self.eject()
                # num=0 here because we don't want to increase the current
                # count

    def eject_all(self, increment_live=False):
        """Ejects all balls from the device."""

        self.log.debug("Ejecting all balls")
        self.eject(self.num_balls_contained)
        # todo implement inc live

    def player_requests_eject(self):
        """We just got a request for the device to eject a ball based on an
        event from the player who's initiating the eject request.

        """

        self.log.debug("Processing player-requested eject")
        if self.ok_to_eject and not self.eject_in_progress:
            self.eject(1)
        else:
            self.log.debug("Could not process eject. ok_to_eject=%s, "
                           "eject_in_progress=%s", self.ok_to_eject,
                           self.eject_in_progress)

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
