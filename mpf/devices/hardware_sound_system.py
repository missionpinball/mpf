"""Hardware sound system."""
from mpf.core.system_wide_device import SystemWideDevice
from mpf.platforms.interfaces.hardware_sound_platform_interface import HardwareSoundPlatformInterface


class HardwareSoundSystem(SystemWideDevice):

    """Hardware sound system using in EM and SS machines."""

    config_section = 'hardware_sound_systems'
    collection = 'hardware_sound_systems'
    class_label = 'hardware_sound_system'

    def __init__(self, machine, name):
        """Initialise hardware sound system."""
        super().__init__(machine, name)
        self.hw_device = None       # type: HardwareSoundPlatformInterface
        self.platform = None
        self._volume = 1.0

    def _initialize(self):
        """Configure hardware."""
        self.platform = self.machine.get_platform_sections(
            'hardware_sound_system', self.config['platform'])
        self.hw_device = self.platform.configure_hardware_sound_system()

    def play(self, sound_number: int):
        """Play a sound."""
        self.hw_device.play_sound(sound_number)

    def play_file(self, file: str, platform_options):
        """Play a sound file."""
        self.hw_device.play_sound_file(file, platform_options)

    def text_to_speech(self, text: str, platform_options):
        """Text to speech output."""
        self.hw_device.text_to_speech(text, platform_options)

    def set_volume(self, volume: float):
        """Set volume."""
        self._volume = float(volume)
        self.hw_device.set_volume(self._volume)

    def increase_volume(self, volume: float):
        """Increase volume."""
        self._volume += float(volume)
        self.hw_device.set_volume(self._volume)

    def decrease_volume(self, volume: float):
        """Increase volume."""
        self._volume -= float(volume)
        self.hw_device.set_volume(self._volume)

    def stop_all_sounds(self):
        """Stop all sounds."""
        self.hw_device.stop_all_sounds()
