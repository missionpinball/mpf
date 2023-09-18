"""A platform to control lights via OSC."""
try:
    from pythonosc.dispatcher import Dispatcher
    from pythonosc.osc_server import AsyncIOOSCUDPServer
    from pythonosc.udp_client import SimpleUDPClient
except ImportError:
    # pythonosc is not a requirement for MPF so we fail with a nice error when loading
    Dispatcher = None
    AsyncIOOSCUDPServer = None
    SimpleUDPClient = None

from typing import Dict

from mpf.platforms.interfaces.switch_platform_interface import SwitchPlatformInterface
from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface, LightPlatformSoftwareFade
from mpf.core.platform import LightsPlatform, SwitchPlatform, SwitchConfig


class OscLight(LightPlatformSoftwareFade):

    """A light on OSC."""

    def __init__(self, number, loop, software_fade_ms, client):
        """initialize light."""
        super().__init__(number, loop, software_fade_ms)
        self.client = client    # type: SimpleUDPClient

    def get_board_name(self):
        """Return board name."""
        return "OSC light"

    def set_brightness(self, brightness: float):
        """Set brightness of OSC light."""
        self.client.send_message("/light/" + self.number, brightness)

    def is_successor_of(self, other):
        """Return true if the other light has the previous number."""
        raise AssertionError("Not possible in OSC")

    def get_successor_number(self):
        """Return next number."""
        raise AssertionError("Not possible in OSC")

    def __lt__(self, other):
        """Order lights by string."""
        return self.number < other.number


class OscSwitch(SwitchPlatformInterface):

    """A switch in the OSC platform."""

    def get_board_name(self):
        """Return board name."""
        return "OSC Switch"


class OscPlatform(LightsPlatform, SwitchPlatform):

    """A platform to control lights via OSC."""

    __slots__ = ["config", "client", "switches", "dispatcher", "server"]

    def __init__(self, machine):
        """Initialize OSC platform."""
        super().__init__(machine)
        self.configure_logging("OSC")
        self.config = None
        self.client = None      # type: SimpleUDPClient
        self.server = None
        self.switches = {}      # type: Dict[str, OscSwitch]
        if not SimpleUDPClient:
            raise AssertionError("python-osc is not installed. Please run 'pip3 install python-osc'.")

    # noinspection PyCallingNonCallable
    async def initialize(self):
        """initialize platform."""
        self.config = self.machine.config['osc']
        self.machine.config_validator.validate_config("osc", self.config)
        self.client = SimpleUDPClient(self.config['remote_ip'], self.config['remote_port'])

        dispatcher = Dispatcher()
        dispatcher.map("/sw/*", self._handle_switch)
        dispatcher.map("/event/*", self._handle_event)
        server = AsyncIOOSCUDPServer((self.config['listen_ip'], self.config['listen_port']), dispatcher,
                                     self.machine.clock.loop)
        self.server, _ = await server.create_serve_endpoint()

        for event in self.config['events_to_send']:
            self.machine.events.add_handler(event, self._send_event, _event_name=event)

    def stop(self):
        """Stop server."""
        self.server.close()

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Parse light number to three RGB channels."""
        del subtype
        return [
            {
                "number": number + "/red"
            },
            {
                "number": number + "/green"
            },
            {
                "number": number + "/blue"
            },
        ]

    def configure_light(self, number: str, subtype: str, config, platform_settings: dict) -> LightPlatformInterface:
        """Configure an OSC light."""
        del config
        return OscLight(number, self.machine.clock.loop,
                        int(1 / self.machine.config['mpf']['default_light_hw_update_hz'] * 1000), self.client)

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict) -> "SwitchPlatformInterface":
        """Config an OSC switch."""
        switch = OscSwitch(config, str(number), self)
        self.switches[str(number)] = switch
        return switch

    async def get_hw_switch_states(self) -> Dict[str, bool]:
        """Return all switches as false."""
        result = {}
        for switch in self.switches.values():
            result[switch.number] = False
        return result

    def _handle_switch(self, address, *args):
        """Handle switch change from OSC."""
        try:
            _, _, switch_name = address.split("/")
        except ValueError:
            self.error_log("Got OSC switch change for invalid address: %s", address)
            return

        if len(args) != 1:
            self.error_log("Got OSC switch change with too many arguments: %s", args)
            return

        if not isinstance(args[0], (bool, int)):
            self.error_log("Got OSC switch change with invalid state: %s", args[0])
            return

        if switch_name not in self.switches:
            self.error_log("Got OSC switch change for switch %s which is not configured as OSC switch.", switch_name)
            return

        self.machine.switch_controller.process_switch_by_num(switch_name, bool(args[0]), self, logical=True)

    def _send_event(self, _event_name, **kwargs):
        """Send event to OSC client."""
        params = []
        for key, value in sorted(kwargs.items(), key=lambda t: t[0]):
            params.append(key)
            # OSC supports int, float and string only
            if isinstance(value, (int, str, float)):
                params.append(value)
            else:
                params.append(str(value))
        self.client.send_message("/event/{}".format(_event_name), params)

    def _handle_event(self, address, *args):
        """Handle event from OSC."""
        try:
            _, _, event_name = address.split("/")
        except ValueError:
            self.error_log("Got OSC event for invalid address: %s", address)
            return

        if len(args) % 2 != 0:
            self.error_log("Got OSC event with an uneven number of arguments: %s. Arguments need to be pairs "
                           "key1, value1, key2, value2 and so on.", args)
            return

        kwargs = {}
        for i in range(0, len(args), 2):
            kwargs[args[i]] = args[i + 1]

        self.machine.events.post(event_name, **kwargs)
