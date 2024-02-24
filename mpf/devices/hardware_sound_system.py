"""Hardware sound system."""
from collections import defaultdict

from mpf.core.system_wide_device import SystemWideDevice
from mpf.platforms.interfaces.hardware_sound_platform_interface import HardwareSoundPlatformInterface


class HardwareSoundSystem(SystemWideDevice):

    """Hardware sound system using in EM and SS machines."""

    config_section = 'hardware_sound_systems'
    collection = 'hardware_sound_systems'
    class_label = 'hardware_sound_system'

    __slots__ = ["hw_device", "_volume"]

    def __init__(self, machine, name):
        """initialize hardware sound system."""
        super().__init__(machine, name)
        self.hw_device = None       # type: HardwareSoundPlatformInterface
        self.platform = None
        self._volume = defaultdict(lambda: 1.0)

    async def _initialize(self):
        """Configure hardware."""
        await super()._initialize()
        self.platform = self.machine.get_platform_sections(
            'hardware_sound_system', self.config['platform'])
        self.platform.assert_has_feature("hardware_sound_systems")
        self.hw_device = self.platform.configure_hardware_sound_system(self.config['platform_settings'])

    def play(self, sound_number: int, track: int = 1):
        """Play a sound."""
        self.hw_device.play_sound(sound_number, track)

    def play_file(self, file: str, platform_options, track: int = 1):
        """Play a sound file."""
        self.hw_device.play_sound_file(file, platform_options, track)

    def text_to_speech(self, text: str, platform_options, track: int = 1):
        """Text to speech output."""
        self.hw_device.text_to_speech(text, platform_options, track)

    def set_volume(self, volume: float, track: int = 1):
        """Set volume."""
        self._volume[track] = float(volume)
        self.hw_device.set_volume(self._volume[track], track)

    def increase_volume(self, volume: float, track: int = 1):
        """Increase volume."""
        self._volume[track] += float(volume)
        self.hw_device.set_volume(self._volume[track], track)

    def decrease_volume(self, volume: float, track: int = 1):
        """Increase volume."""
        self._volume[track] -= float(volume)
        self.hw_device.set_volume(self._volume[track], track)

    def stop_all_sounds(self, track: int = 1):
        """Stop all sounds on track."""
        self.hw_device.stop_all_sounds(track)
