"""RPC Interface for BCP clients."""
from copy import deepcopy

from mpf.core.events import PostedEvent
from mpf.core.player import Player
from mpf.core.utility_functions import Util
from mpf.core.mpf_controller import MpfController


class BcpInterface(MpfController):

    """Implements the BCP interface which can be used by all clients.

    Args:
        machine: A reference to the main MPF machine object.

    The following BCP commands are currently implemented:
        error
        get
        hello?version=xxx&controller_name=xxx&controller_version=xxx
        mode_start?name=xxx&priority=xxx
        mode_stop?name=xxx
        player_added?player_num=x
        player_variable?name=x&value=x&prev_value=x&change=x&player_num=x
        set
        shot?name=x
        switch?name=x&state=x
        timer
        trigger?name=xxx

    """

    def __init__(self, machine):
        """Initialise BCP."""
        super().__init__(machine)

        if 'bcp' not in machine.config or not machine.config['bcp']:
            self.configured = False
            return

        self.configured = True

        self.config = machine.config['bcp']
        self.bcp_events = dict()

        self.bcp_receive_commands = dict(
            error=self.bcp_receive_error,
            switch=self.bcp_receive_switch,
            trigger=self.bcp_receive_trigger,
            register_trigger=self.bcp_receive_register_trigger,
            set_machine_var=self._set_machine_var,
            monitor_events=self._monitor_events,
            monitor_machine_vars=self._monitor_machine_vars,
            monitor_player_vars=self._monitor_player_vars,
            monitor_devices=self._monitor_devices)

        self._setup_player_monitor()

        self._setup_machine_var_monitor()

        self.machine.events.add_handler('player_add_success',
                                        self.bcp_player_added)
        self.machine.events.add_handler('machine_reset_phase_1',
                                        self.bcp_reset)

        self.machine.mode_controller.register_start_method(
            self.bcp_mode_start, 'mode')

    def __repr__(self):
        """Return string representation."""
        return '<BCP Interface>'

    def register_command_callback(self, cmd, callback):
        """Register a BCP command."""
        if not self.configured:
            return
        self.bcp_receive_commands[cmd] = callback

    def add_registered_trigger_event_for_client(self, client, event):
        """Add trigger for event."""
        # register handler if first transport

        # Note here we're registering the trigger for the event name, not the
        # full event with condition. This means that this event will be
        # always sent regardless of condition, and the MC will have to process
        # the condition.

        event, _ = self.machine.events.get_event_and_condition_from_string(event)

        if not self.machine.bcp.transport.get_transports_for_handler(event):
            self.machine.events.add_handler(event=event,
                                            handler=self.bcp_trigger,
                                            name=event)
        # register transport
        self.machine.bcp.transport.add_handler_to_transport(event, client)

    def remove_registered_trigger_event_for_client(self, client, event):
        """Remove trigger for event."""
        event, _ = self.machine.events.get_event_and_condition_from_string(event)

        # unregister transport
        self.machine.bcp.transport.remove_transport_from_handle(event, client)

        # if not transports remain. remove handler
        if not self.machine.bcp.transport.get_transports_for_handler(event):
            self.machine.events.remove_handler_by_event(event=event, handler=self.bcp_trigger)

    def _set_machine_var(self, client, name, value):
        """Set machine var via bcp."""
        del client
        self.machine.create_machine_var(name, value)

    def _monitor_events(self, client):
        """Monitor all events."""
        self.machine.bcp.transport.add_handler_to_transport("_monitor_events", client)
        self.machine.events.monitor_events = True

    def monitor_posted_event(self, posted_event: PostedEvent):
        """Send monitored posted event to bcp clients."""
        self.machine.bcp.transport.send_to_clients_with_handler(
            handler="_monitor_events",
            bcp_command="monitored_event",
            event_name=posted_event.event,
            event_type=posted_event.type,
            event_callback=posted_event.callback,
            event_kwargs=Util.convert_to_simply_type(posted_event.kwargs),
            registered_handlers=Util.convert_to_simply_type(
                self.machine.events.registered_handlers.get(posted_event.event, []))
        )

    def _monitor_devices(self, client):
        """Register client to get notified of device changes."""
        self.machine.bcp.transport.add_handler_to_transport("_devices", client)

        # initially send all states
        for collection in self.machine.device_manager.get_monitorable_devices().values():
            for device in collection.values():
                self.machine.bcp.transport.send_to_client(
                    client=client,
                    bcp_command='device',
                    type=device.class_label,
                    name=device.name,
                    changes=False,
                    state=device.get_monitorable_state())

    def notify_device_changes(self, device, attribute_name, old_value, new_value):
        """Notify all listeners about device change."""
        if not self.configured:
            return

        self.machine.bcp.transport.send_to_clients_with_handler(
            handler="_devices",
            bcp_command='device',
            type=device.class_label,
            name=device.name,
            changes=(attribute_name, Util.convert_to_simply_type(old_value), Util.convert_to_simply_type(new_value)),
            state=device.get_monitorable_state())

    def _monitor_player_vars(self, client):
        self.machine.bcp.transport.add_handler_to_transport("_player_vars", client)

    def _monitor_machine_vars(self, client):
        self._send_machine_vars(client)
        self.machine.bcp.transport.add_handler_to_transport("_machine_vars", client)

    def _send_machine_vars(self, client):
        self.machine.bcp.transport.send_to_client(
            client, bcp_command='settings', settings=Util.convert_to_simply_type(self.machine.settings.get_settings()))
        for var_name, settings in self.machine.machine_vars.items():
            self.machine.bcp.transport.send_to_client(client, bcp_command='machine_variable',
                                                      name=var_name,
                                                      value=settings['value'])

    def _setup_player_monitor(self):
        Player.monitor_enabled = True
        self.machine.register_monitor('player', self._player_var_change)

    def _setup_machine_var_monitor(self):
        self.machine.machine_var_monitor = True
        self.machine.register_monitor('machine_vars', self._machine_var_change)

    # pylint: disable-msg=too-many-arguments
    def _player_var_change(self, name, value, prev_value, change, player_num):
        self.machine.bcp.transport.send_to_clients_with_handler(
            handler="_player_vars",
            bcp_command='player_variable',
            name=name,
            value=value,
            prev_value=prev_value,
            change=change,
            player_num=player_num)

    def _machine_var_change(self, name, value, prev_value, change):
        self.machine.bcp.transport.send_to_clients_with_handler(
            handler="_machine_vars",
            bcp_command='machine_variable',
            name=name,
            value=value,
            prev_value=prev_value,
            change=change)

    def process_bcp_message(self, cmd, kwargs, client):
        """Process BCP message.

        Args:
            cmd:
            kwargs:
        """
        if self._debug_to_console or self._debug_to_file:
            if 'rawbytes' in kwargs:
                debug_kwargs = deepcopy(kwargs)
                debug_kwargs['rawbytes'] = '<{} bytes>'.format(
                    len(debug_kwargs.pop('rawbytes')))

                self.debug_log("Processing command: %s %s", cmd, debug_kwargs)
            else:
                self.debug_log("Processing command: %s %s", cmd, kwargs)

        if cmd in self.bcp_receive_commands:
            try:
                self.bcp_receive_commands[cmd](client=client, **kwargs)
            except TypeError as e:
                self.machine.bcp.transport.send_to_client(client, "error", cmd=cmd, error=str(e), kwargs=kwargs)

        else:
            self.warning_log("Received invalid BCP command: %s from client: %s", cmd, client.name)

    def bcp_receive_error(self, client, **kwargs):
        """A remote BCP host has sent a BCP error message, indicating that a command from MPF was not recognized.

        This method only posts a warning to the log. It doesn't do anything else
        at this point.
        """
        self.warning_log('Received Error command from host with parameters: %s, from client %s',
                         kwargs, str(client))

    def bcp_mode_start(self, config, priority, mode, **kwargs):
        """Send BCP 'mode_start' to the connected BCP hosts.

        Schedule automatic sending of 'mode_stop' when the mode stops.
        """
        del config
        del kwargs
        self.machine.bcp.transport.send_to_all_clients('mode_start', name=mode.name, priority=priority)

        return self.bcp_mode_stop, mode.name

    def bcp_mode_stop(self, name, **kwargs):
        """Send BCP 'mode_stop' to the connected BCP hosts."""
        del kwargs
        self.machine.bcp.transport.send_to_all_clients('mode_stop', name=name)

    def bcp_reset(self, **kwargs):
        """Send the 'reset' command to the remote BCP host."""
        del kwargs
        self.machine.bcp.transport.send_to_all_clients("reset")

    def bcp_receive_switch(self, client, name, state, **kwargs):
        """Process an incoming switch state change request from a remote BCP host.

        Args:
            name: String name of the switch to set.
            state: Integer representing the state this switch will be set to.
                1 = active, 0 = inactive, -1 means this switch will be flipped
                from whatever its current state is to the opposite state.
        """
        del kwargs
        del client
        state = int(state)

        if name not in self.machine.switches:
            self.warning_log("Received BCP switch message with invalid switch"
                             "name: '%s'", name)
            return

        if state == -1:
            if self.machine.switch_controller.is_active(name):
                state = 0
            else:
                state = 1

        self.machine.switch_controller.process_switch(name=name,
                                                      state=state,
                                                      logical=True)

    def bcp_receive_register_trigger(self, client, event, **kwargs):
        """Register a trigger for a client."""
        del kwargs
        self.add_registered_trigger_event_for_client(client, event)

    def bcp_player_added(self, num, **kwargs):
        """Send BCP 'player_added' to the connected BCP hosts."""
        del kwargs
        self.machine.bcp.transport.send_to_clients_with_handler('_player_vars', 'player_added', player_num=num)

    def bcp_trigger(self, name, **kwargs):
        """Send BCP 'trigger' to the connected BCP hosts."""
        # ignore events which already came from bcp to prevent loops
        if "_from_bcp" in kwargs:
            return

        # Since player variables are sent automatically, if we get a trigger
        # for an event that starts with "player_", we need to only send it here
        # if there's *not* a player variable with that name, since if there is
        # a player variable then the player variable handler will send it.
        if name.startswith('player_'):
            try:
                if self.machine.game.player.is_player_var(name.lstrip('player_')):
                    return

            except AttributeError:
                pass

        self.machine.bcp.transport.send_to_clients_with_handler(
            handler=name, bcp_command='trigger', name=name, **kwargs)

    def bcp_receive_trigger(self, client, name, callback=None, **kwargs):
        """Process an incoming trigger command from a remote BCP host."""
        del client
        kwargs['_from_bcp'] = True
        if callback:
            self.machine.events.post(event=name,
                                     callback=self.bcp_trigger,
                                     name=kwargs.pop('callback'),
                                     **kwargs)

        else:
            self.machine.events.post(event=name, **kwargs)
