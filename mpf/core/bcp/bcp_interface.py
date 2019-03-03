"""RPC Interface for BCP clients."""
import asyncio
from copy import deepcopy

from mpf.core.rgb_color import ColorException

from mpf.core.events import PostedEvent
from mpf.core.player import Player
from mpf.core.utility_functions import Util
from mpf.core.mpf_controller import MpfController
from mpf.core.switch_controller import MonitoredSwitchChange
from mpf.exceptions.DriverLimitsError import DriverLimitsError


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

    config_name = "bcp_interface"

    __slots__ = ["configured", "config", "_client_reset_queue", "_client_reset_complete_status", "bcp_receive_commands",
                 "_shows"]

    def __init__(self, machine):
        """Initialise BCP."""
        super().__init__(machine)

        if 'bcp' not in machine.config or not machine.config['bcp']:
            self.configured = False
            return

        self.configured = True

        self.config = machine.config['bcp']

        self._client_reset_queue = None
        self._client_reset_complete_status = {}

        self.bcp_receive_commands = dict(
            reset_complete=self._bcp_receive_reset_complete,
            error=self._bcp_receive_error,
            switch=self._bcp_receive_switch,
            trigger=self._bcp_receive_trigger,
            register_trigger=self._bcp_receive_register_trigger,
            evaluate_placeholder=self._evaluate_placeholder,
            remove_trigger=self._bcp_receive_deregister_trigger,
            monitor_start=self._bcp_receive_monitor_start,
            monitor_stop=self._bcp_receive_monitor_stop,
            set_machine_var=self._bcp_receive_set_machine_var,
            service=self._service,
        )
        self._shows = {}

        self.machine.events.add_handler('machine_reset_phase_1', self.bcp_reset)

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
        if not self.machine.bcp.transport.get_transports_for_handler(event):
            self.machine.events.add_handler(event=event,
                                            handler=self.bcp_trigger,
                                            name=event)
        # register transport
        self.machine.bcp.transport.add_handler_to_transport(event, client)

    def remove_registered_trigger_event_for_client(self, client, event):
        """Remove trigger for event."""
        # unregister transport
        self.machine.bcp.transport.remove_transport_from_handle(event, client)

        # if not transports remain, remove handler
        if not self.machine.bcp.transport.get_transports_for_handler(event):
            self.machine.events.remove_handler_by_event(event=event, handler=self.bcp_trigger)

    @asyncio.coroutine
    def _bcp_receive_set_machine_var(self, client, name, value):
        """Set machine var via bcp."""
        del client
        self.machine.set_machine_var(name, value)

    @asyncio.coroutine
    def _service_stop(self, client):
        for show in self._shows.values():
            show.stop()
        for light in self.machine.lights.values():
            light.remove_from_stack_by_key("service")
        self._shows = {}
        yield from self.machine.service.stop_service()
        self.machine.bcp.transport.send_to_client(client, "service_stop")

    @asyncio.coroutine
    def _service(self, client, subcommand, **kwargs):
        """Run service command."""
        if subcommand == "start":
            self.machine.service.start_service()
        elif subcommand == "stop":
            yield from self._service_stop(client)
        elif subcommand == "list_switches":
            self.machine.bcp.transport.send_to_client(client, "list_switches",
                                                      switches=[(s[0], str(s[1].hw_switch.number), s[1].name,
                                                                 s[1].state)
                                                                for s in self.machine.service.get_switch_map()])
        elif subcommand == "list_coils":
            self.machine.bcp.transport.send_to_client(client, "list_coils",
                                                      coils=[(s[0], str(s[1].hw_driver.number), s[1].name) for s in
                                                             self.machine.service.get_coil_map()])
        elif subcommand == "list_lights":
            self.machine.bcp.transport.send_to_client(client, "list_lights",
                                                      lights=[(s[0], s[1].get_hw_numbers(), s[1].name, s[1].get_color())
                                                              for s in self.machine.service.get_light_map()])
        elif subcommand == "list_shows":
            self.machine.bcp.transport.send_to_client(client, "list_shows",
                                                      shows=[(s.name, sorted(s.tokens))
                                                             for s in sorted(self.machine.shows.values(),
                                                                             key=lambda x: x.name)])
        elif subcommand == "monitor_switches":
            pass
        elif subcommand == "coil_pulse":
            self._coil_pulse(client, kwargs.get("coil"), kwargs.get("pulse_ms"), kwargs.get("pulse_power"))
        elif subcommand == "coil_enable":
            self._coil_enable(client, kwargs.get("coil"), kwargs.get("pulse_ms"), kwargs.get("pulse_power"),
                              kwargs.get("hold_power"))
        elif subcommand == "coil_disable":
            self._coil_disable(client, kwargs.get("coil"))
        elif subcommand == "show_play":
            self._show_play(client, kwargs.get("show"), kwargs.get("token"))
        elif subcommand == "show_stop":
            self._show_stop(client, kwargs.get("show"))
        elif subcommand == "light_color":
            self._light_color(client, kwargs.get("light"), kwargs.get("color"))

    def _show_play(self, client, show_name, token):
        try:
            show = self.machine.shows[show_name]
        except KeyError:
            self.machine.bcp.transport.send_to_client(client, "show_play", error="Show not found")
            return
        if show_name in self._shows:
            self._shows[show_name].stop()
        try:
            self._shows[show_name] = show.play(show_tokens=token, priority=100000)
        except (ValueError, AssertionError) as e:
            self.machine.bcp.transport.send_to_client(client, "show_play", error="Show error: {}".format(e))
            return
        self.machine.bcp.transport.send_to_client(client, "show_play", error=False)

    def _show_stop(self, client, show_name):
        if show_name in self._shows:
            self._shows[show_name].stop()
            del self._shows[show_name]
            self.machine.bcp.transport.send_to_client(client, "show_stop", error=False)
        else:
            self.machine.bcp.transport.send_to_client(client, "show_stop", error="Show not playing")

    def _coil_pulse(self, client, coil_name, pulse_ms, pulse_power):
        try:
            coil = self.machine.coils[coil_name]
        except KeyError:
            self.machine.bcp.transport.send_to_client(client, "coil_pulse", error="Coil not found")
            return
        if pulse_ms:
            pulse_ms = int(pulse_ms)
        if pulse_power:
            pulse_power = float(pulse_power)
        coil.pulse(pulse_ms=pulse_ms, pulse_power=pulse_power)
        self.machine.bcp.transport.send_to_client(client, "coil_pulse", error=False)

    def _coil_disable(self, client, coil_name):
        try:
            coil = self.machine.coils[coil_name]
        except KeyError:
            self.machine.bcp.transport.send_to_client(client, "coil_disable", error="Coil not found")
            return
        coil.disable()
        self.machine.bcp.transport.send_to_client(client, "coil_disable", error=False)

    # pylint: disable-msg=too-many-arguments
    def _coil_enable(self, client, coil_name, pulse_ms, pulse_power, hold_power):
        try:
            coil = self.machine.coils[coil_name]
        except KeyError:
            self.machine.bcp.transport.send_to_client(client, "coil_enable", error="Coil not found")
            return
        if pulse_ms:
            pulse_ms = int(pulse_ms)
        if pulse_power:
            pulse_power = float(pulse_power)
        if hold_power:
            hold_power = float(hold_power)
        try:
            coil.enable(pulse_ms=pulse_ms, pulse_power=pulse_power, hold_power=hold_power)
        except DriverLimitsError as e:
            self.machine.bcp.transport.send_to_client(client, "coil_enable", error=str(e))
            return

        self.machine.bcp.transport.send_to_client(client, "coil_enable", error=False)

    def _light_color(self, client, light_name, color_name):
        try:
            light = self.machine.lights[light_name]
        except KeyError:
            self.machine.bcp.transport.send_to_client(client, "light_color", error="Light not found")
            return
        try:
            light.color(color_name, key="service")
        except (DriverLimitsError, ColorException) as e:
            self.machine.bcp.transport.send_to_client(client, "light_color", error=str(e))
            return

        self.machine.bcp.transport.send_to_client(client, "light_color", error=False)

    @asyncio.coroutine
    def _bcp_receive_monitor_start(self, client, category):
        """Start monitoring the specified category."""
        category = str.lower(category)

        if category == "events":
            self._monitor_events(client)
        elif category == "devices":
            self._monitor_devices(client)
        elif category == "drivers":
            self._monitor_drivers(client)
        elif category == "switches":
            self._monitor_switches(client)
        elif category == "machine_vars":
            self._monitor_machine_vars(client)
        elif category == "player_vars":
            self._monitor_player_vars(client)
        elif category == "modes":
            self._monitor_modes(client)
        elif category == "core_events":
            self._monitor_core_events(client)
        elif category == "status_request":
            self._monitor_status_request(client)
        else:
            self.machine.bcp.transport.send_to_client(client,
                                                      "error",
                                                      cmd="monitor_start?category={}".format(category),
                                                      error="Invalid category value")

    @asyncio.coroutine
    def _bcp_receive_monitor_stop(self, client, category):
        """Stop monitoring the specified category."""
        category = str.lower(category)

        if category == "events":
            self._monitor_events_stop(client)
        elif category == "devices":
            self._monitor_devices_stop(client)
        elif category == "drivers":
            self._monitor_drivers_stop(client)
        elif category == "switches":
            self._monitor_switches_stop(client)
        elif category == "machine_vars":
            self._monitor_machine_vars_stop(client)
        elif category == "player_vars":
            self._monitor_player_vars_stop(client)
        elif category == "modes":
            self._monitor_modes_stop(client)
        elif category == "core_events":
            self._monitor_core_events_stop(client)
        elif category == "status_request":
            self._monitor_status_request_stop(client)
        else:
            self.machine.bcp.transport.send_to_client(client,
                                                      "error",
                                                      cmd="monitor_stop?category={}".format(category),
                                                      error="Invalid category value")

    def _monitor_drivers(self, client):
        """Monitor all drivers."""
        self.machine.bcp.transport.add_handler_to_transport("_monitor_drivers", client)

    def _monitor_drivers_stop(self, client):
        """Monitor all drivers."""
        self.machine.bcp.transport.remove_transport_from_handle("_monitor_drivers", client)

    def _monitor_events(self, client):
        """Monitor all events."""
        self.machine.bcp.transport.add_handler_to_transport("_monitor_events", client)
        self.machine.events.monitor_events = True

    def _monitor_events_stop(self, client):
        """Stop monitoring all events for the specified client."""
        self.machine.bcp.transport.remove_transport_from_handle("_monitor_events", client)

        if not self.machine.bcp.transport.get_transports_for_handler("_monitor_events"):
            self.machine.events.monitor_events = False

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
        # trigger updates of lights
        self.machine.light_controller.monitor_lights()

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

    def _monitor_devices_stop(self, client):
        """Remove client to no longer get notified of device changes."""
        self.machine.bcp.transport.remove_transport_from_handle("_devices", client)

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

    def _monitor_switches(self, client):
        """Register client to get notified of switch changes."""
        self.machine.switch_controller.add_monitor(self._notify_switch_changes)
        self.machine.bcp.transport.add_handler_to_transport("_switches", client)

    def _monitor_switches_stop(self, client):
        """Remove client to no longer get notified of switch changes."""
        self.machine.bcp.transport.add_handler_to_transport("_switches", client)

        # If there are no more clients monitoring switches, remove monitor
        if not self.machine.bcp.transport.get_transports_for_handler("_switches"):
            self.machine.switch_controller.remove_monitor(self._notify_switch_changes)

    def _notify_switch_changes(self, change: MonitoredSwitchChange):
        """Notify all listeners about switch change."""
        self.machine.bcp.transport.send_to_clients_with_handler(
            handler="_switches",
            bcp_command='switch',
            name=change.name,
            state=change.state)

    def _monitor_player_vars(self, client):
        # Setup player variables to be monitored (if necessary)
        if not self.machine.bcp.transport.get_transports_for_handler("_player_vars"):
            Player.monitor_enabled = True
            self.machine.register_monitor('player', self._player_var_change)

        self.machine.bcp.transport.add_handler_to_transport("_player_vars", client)

    def _monitor_player_vars_stop(self, client):
        self.machine.bcp.transport.remove_transport_from_handle("_player_vars", client)

        # If there are no more clients monitoring player variables, stop monitoring
        if not self.machine.bcp.transport.get_transports_for_handler("_player_vars"):
            Player.monitor_enabled = False

    def _monitor_machine_vars(self, client):
        # Setup machine variables to be monitored (if necessary)
        if not self.machine.bcp.transport.get_transports_for_handler("_machine_vars"):
            self.machine.machine_var_monitor = True
            self.machine.register_monitor('machine_vars', self._machine_var_change)

        # Send initial machine variable values
        self._send_machine_vars(client)

        # Establish handler for machine variable changes
        self.machine.bcp.transport.add_handler_to_transport("_machine_vars", client)

    def _monitor_machine_vars_stop(self, client):
        self.machine.bcp.transport.remove_transport_from_handle("_machine_vars", client)

        # If there are no more clients monitoring machine variables, stop monitoring
        if not self.machine.bcp.transport.get_transports_for_handler("_machine_vars"):
            self.machine.machine_var_monitor = False

    def _send_machine_vars(self, client):
        self.machine.bcp.transport.send_to_client(
            client, bcp_command='settings', settings=Util.convert_to_simply_type(self.machine.settings.get_settings()))
        for var_name, settings in self.machine.machine_vars.items():
            self.machine.bcp.transport.send_to_client(client, bcp_command='machine_variable',
                                                      name=var_name,
                                                      value=settings['value'])

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

    def _monitor_modes(self, client):
        """Begin monitoring all mode events (start, stop) via the specified client."""
        if not self.machine.bcp.transport.get_transports_for_handler("_modes"):
            self.machine.mode_controller.register_start_method(self._mode_start, 'mode')

        self.machine.bcp.transport.add_handler_to_transport("_modes", client)

        self.machine.bcp.transport.send_to_client(
            client=client,
            bcp_command="mode_list",
            running_modes=sorted([(m.name, m.priority) for m in self.machine.modes if m.active]))

    def _monitor_modes_stop(self, client):
        """Stop monitoring all mode events (start, stop) via the specified client."""
        self.machine.bcp.transport.remove_transport_from_handle("_modes", client)

        if not self.machine.bcp.transport.get_transports_for_handler("_modes"):
            self.machine.mode_controller.remove_start_method(self._mode_start, 'mode')

    def _mode_start(self, config, priority, mode, **kwargs):
        """Send 'mode_start' to the monitoring clients."""
        del config
        del kwargs
        self.machine.bcp.transport.send_to_clients_with_handler(
            handler="_modes",
            bcp_command="mode_start",
            name=mode.name,
            running_modes=sorted([(m.name, m.priority) for m in self.machine.modes if m.active or m == mode]),
            priority=priority)

        # Return the method and mode name to call when the mode stops (self-registering)
        return self._mode_stop, mode.name

    def _mode_stop(self, mode, **kwargs):
        """Send 'mode_stop' to the monitoring clients."""
        del kwargs
        self.machine.bcp.transport.send_to_clients_with_handler(
            handler="_modes",
            bcp_command="mode_stop",
            running_modes=sorted([(m.name, m.priority) for m in self.machine.modes if m.active]),
            name=mode)

    def _monitor_core_events(self, client):
        """Begin monitoring all core events (ball, player turn, etc.) via the specified client."""
        if not self.machine.bcp.transport.get_transports_for_handler("_core_events"):
            self.machine.events.add_handler('ball_started', self._ball_started)
            self.machine.events.add_handler('ball_ended', self._ball_ended)
            self.machine.events.add_handler('player_turn_started', self._player_turn_start)
            self.machine.events.add_handler('player_added', self._player_added)

        self.machine.bcp.transport.add_handler_to_transport("_core_events", client)

    def _monitor_core_events_stop(self, client):
        """Stop monitoring all core events (ball, player turn, etc.) via the specified client."""
        self.machine.bcp.transport.remove_transport_from_handle("_core_events", client)

        if not self.machine.bcp.transport.get_transports_for_handler("_core_events"):
            self.machine.events.remove_handler_by_event('ball_started', self._ball_started)
            self.machine.events.remove_handler_by_event('ball_ended', self._ball_ended)
            self.machine.events.remove_handler_by_event('player_turn_started', self._player_turn_start)
            self.machine.events.remove_handler_by_event('player_added', self._player_added)

    def _monitor_status_request(self, client):
        """Begin monitoring status_request messages via the specified client."""
        self.machine.bcp.transport.add_handler_to_transport("_status_request", client)

    def _monitor_status_request_stop(self, client):
        """Stop monitoring status_request messages via the specified client."""
        self.machine.bcp.transport.remove_transport_from_handle("_status_request", client)

    def _ball_started(self, ball, player, **kwargs):
        del kwargs
        self.machine.bcp.transport.send_to_clients_with_handler(
            handler="_core_events",
            bcp_command="ball_start",
            player_num=player,
            ball=ball)

    def _ball_ended(self, **kwargs):
        del kwargs
        self.machine.bcp.transport.send_to_clients_with_handler(
            handler="_core_events",
            bcp_command="ball_end")

    def _player_turn_start(self, number, player, **kwargs):
        del player
        del kwargs
        self.machine.bcp.transport.send_to_clients_with_handler(
            handler="_core_events",
            bcp_command="player_turn_start",
            player_num=number)

    def _player_added(self, num, player, **kwargs):
        del player
        del kwargs
        self.machine.bcp.transport.send_to_clients_with_handler(
            handler="_core_events",
            bcp_command="player_added",
            player_num=num)

    @asyncio.coroutine
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
                callback = self.bcp_receive_commands[cmd]
            except TypeError as e:
                self.machine.bcp.transport.send_to_client(client, "error", cmd=cmd, error=str(e), kwargs=kwargs)
            else:
                yield from callback(client=client, **kwargs)

        else:
            self.warning_log("Received invalid BCP command: %s from client: %s", cmd, client.name)

    @asyncio.coroutine
    def _bcp_receive_error(self, client, **kwargs):
        """Handle a BCP error message from a remote BCP host indicating that a command from MPF was not recognized.

        This method only posts a warning to the log. It doesn't do anything else
        at this point.
        """
        self.warning_log('Received Error command from host with parameters: %s, from client %s',
                         kwargs, str(client))

    def send_driver_event(self, **kwargs):
        """Notify all observers about driver event."""
        self.machine.bcp.transport.send_to_clients_with_handler("_monitor_drivers", "driver_event", **kwargs)

    @asyncio.coroutine
    def _bcp_receive_reset_complete(self, client, **kwargs):
        """Handle a BCP reset_complete message from a remote BCP host indicating their reset process has completed."""
        del kwargs
        self.debug_log("Received reset_complete from client: %s %s", client.name)
        self._client_reset_complete_status[client] = True

        # Check if reset_complete status is True from all clients
        if all(status is True for item, status in self._client_reset_complete_status.items()):
            if self._client_reset_queue:
                self._client_reset_queue.clear()
                self._client_reset_queue = None
            self._client_reset_complete_status.clear()
            self.debug_log("Received reset_complete from all clients. Clearing wait from queue event.")

    def bcp_reset(self, queue, **kwargs):
        """Send the 'reset' command to the remote BCP host."""
        del kwargs

        # Will hold the queue event until all clients respond with a "reset_complete" command
        clients = self.machine.bcp.transport.get_all_clients()
        self._client_reset_complete_status.clear()
        for client in clients:
            if not client.name:
                continue
            self._client_reset_complete_status[client] = False

        if self._client_reset_complete_status:
            queue.wait()
            self._client_reset_queue = queue

            # Send the reset command
            self.debug_log("Sending reset to all clients (will now wait for reset_complete "
                           "to be received from all clients).")
            self.machine.bcp.transport.send_to_all_clients("reset")

    @asyncio.coroutine
    def _bcp_receive_switch(self, client, name, state, **kwargs):
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

    @asyncio.coroutine
    def _evaluate_placeholder(self, client, placeholder, parameters=None, **kwargs):
        """Evaluate and return placeholder."""
        del kwargs
        if parameters is None:
            parameters = []
        placeholder_obj = self.machine.placeholder_manager.build_raw_template(placeholder, None)
        try:
            value = placeholder_obj.evaluate(parameters=parameters)
        except AssertionError as e:
            self.machine.bcp.transport.send_to_client(client=client, bcp_command='evaluate_placeholder',
                                                      error=str(e))
            return

        self.machine.bcp.transport.send_to_client(client=client, bcp_command='evaluate_placeholder', value=value,
                                                  error=False)

    @asyncio.coroutine
    def _bcp_receive_register_trigger(self, client, event, **kwargs):
        """Register a trigger for a client."""
        del kwargs
        self.add_registered_trigger_event_for_client(client, event)

    @asyncio.coroutine
    def _bcp_receive_deregister_trigger(self, client, event, **kwargs):
        """Deregister a trigger for a client."""
        del kwargs
        self.remove_registered_trigger_event_for_client(client, event)

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

    def bcp_trigger_client(self, client, name, **kwargs):
        """Send BCP 'trigger' to a specific client."""
        # ignore events which already came from bcp to prevent loops
        if "_from_bcp" in kwargs:
            return

        self.machine.bcp.transport.send_to_client(client=client, bcp_command='trigger', name=name, **kwargs)

    @asyncio.coroutine
    def _bcp_receive_trigger(self, client, name, callback=None, **kwargs):
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
