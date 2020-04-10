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
        """Initialise light."""
        super().__init__(number, loop, software_fade_ms)
        self.client = client    # type: SimpleUDPClient

    def get_board_name(self):
        """Return board name."""
        return "OSC light"

    def set_brightness(self, brightness: float):
        """Set brightness of OSC light."""
        self.client.send_message(self.number, brightness)


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

    async def initialize(self):
        """Initialise platform."""
        self.config = self.machine.config['osc']
        self.machine.config_validator.validate_config("osc", self.config)
        self.client = SimpleUDPClient(self.config['ip'], self.config['port'])

        dispatcher = Dispatcher()
        dispatcher.map("/sw/*", self._handle_switch)
        server = AsyncIOOSCUDPServer((self.config['server_ip'], self.config['server_port']), dispatcher,
                                     self.machine.clock.loop)
        self.server, _ = await server.create_serve_endpoint()

    def stop(self):
        """Stop server."""
        self.server.close()

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Parse light number to a single channel."""
        del subtype
        return [
            {
                "number": number
            }
        ]

    def configure_light(self, number: str, subtype: str, platform_settings: dict) -> LightPlatformInterface:
        """Configure an OSC light."""
        return OscLight(number, self.machine.clock.loop,
                        int(1 / self.machine.config['mpf']['default_light_hw_update_hz'] * 1000), self.client)

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict) -> "SwitchPlatformInterface":
        """Config an OSC switch."""
        switch = OscSwitch(config, str(number))
        self.switches[str(number)] = switch
        return switch

    async def get_hw_switch_states(self) -> Dict[str, bool]:
        """Return all switches as false."""
        result = {}
        for switch in self.switches.values():
            result[switch.number] = False
        return result

    def _handle_switch(self, address, *args):
        """Handle Switch change from OSC."""
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
