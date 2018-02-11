"""Shot profiles."""
from mpf.core.mode import Mode

from mpf.core.system_wide_device import SystemWideDevice

from mpf.core.mode_device import ModeDevice


class ShotProfile(ModeDevice, SystemWideDevice):

    """A shot profile."""

    config_section = 'shot_profiles'
    collection = 'shot_profiles'
    class_label = 'shot_profile'

    def device_removed_from_mode(self, mode: Mode) -> None:
        """Remove from mode."""
        pass
