"""Platform to use lights connected to a driver."""
from mpf.platforms.interfaces.light_platform_interface import LightPlatformSoftwareFade, LightPlatformInterface
from mpf.core.platform import LightsPlatform


class DriverLight(LightPlatformSoftwareFade):

    """A coil which is used to drive a light."""

    __slots__ = ["driver"]

    def __init__(self, driver, loop, software_fade_ms):
        """Initialise coil as light."""
        super().__init__(driver.hw_driver.number, loop, software_fade_ms)
        self.driver = driver

    def set_brightness(self, brightness: float):
        """Set pwm to coil."""
        if brightness <= 0:
            self.driver.disable()
        else:
            self.driver.enable(hold_power=brightness)

    def get_board_name(self):
        """Return board name of underlaying driver."""
        return self.driver.hw_driver.get_board_name()


class DriverLightPlatform(LightsPlatform):

    """Lights on drivers."""

    __slots__ = ["_lights"]

    def __init__(self, machine):
        """Initialize platform."""
        super().__init__(machine)
        self._lights = []
        self.features["tickless"] = True

    def stop(self):
        """Stop all fades."""
        for light in self._lights:
            light.stop()

    def configure_light(self, number: str, subtype: str, platform_settings: dict) -> "LightPlatformInterface":
        """Configure a light on a driver."""
        driver = DriverLight(self.machine.coils[number.strip()], self.machine.clock.loop,
                             int(1 / self.machine.config['mpf']['default_light_hw_update_hz'] * 1000))
        self._lights.append(driver)
        return driver

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Parse number."""
        del subtype
        channel_list = [
            {
                "number": number,
                "platform": "drivers"
            }
        ]
        return channel_list
