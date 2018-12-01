"""A platform to control lights via OSC."""
import asyncio
try:
    from pythonosc.udp_client import SimpleUDPClient
except ImportError:
    SimpleUDPClient = None

from mpf.platforms.interfaces.light_platform_interface import LightPlatformInterface, LightPlatformSoftwareFade

from mpf.core.platform import LightsPlatform


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


class OscPlatform(LightsPlatform):

    """A platform to control lights via OSC."""

    def __init__(self, machine):
        """Initialize OSC platform."""
        super().__init__(machine)
        self.config = None
        self.client = None
        if not SimpleUDPClient:
            raise AssertionError("python-osc is not installed. Please run 'pip3 install python-osc'.")

    @asyncio.coroutine
    def initialize(self):
        """Initialise platform."""
        self.config = self.machine.config['osc']
        self.machine.config_validator.validate_config("osc", self.config)
        self.client = SimpleUDPClient(self.config['ip'], self.config['port'])

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Parse light number to a single channel."""
        del subtype
        return [
            {
                "number": number
            }
        ]

    def configure_light(self, number: str, subtype: str, platform_settings: dict) -> "LightPlatformInterface":
        """Configure an OSC light."""
        return OscLight(number, self.machine.clock.loop,
                        int(1 / self.machine.config['mpf']['default_light_hw_update_hz'] * 1000), self.client)
