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

    def _initialize(self):
        """Configure hardware."""
        self.platform = self.machine.get_platform_sections(
            'hardware_sound_system', self.config['platform'])
        self.hw_device = self.platform.configure_hardware_sound_system()

    def play(self, sound_number: int):
        """Play a sound."""
        self.hw_device.play_sound(int(sound_number))

    def stop_all_sounds(self):
        """Stop all sounds."""
        self.hw_device.stop_all_sounds()
