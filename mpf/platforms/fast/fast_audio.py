"""Hardware sound system."""
from enum import Enum
from math import ceil
from mpf.core.utility_functions import Util
from mpf.platforms.interfaces.hardware_sound_platform_interface import HardwareSoundPlatformInterface

class FastAudioDevices(Enum):

    """Track values for audio targets."""

    SPEAKER = 1
    SUBWOOFER = 2
    HEADPHONES = 3


class FastLcdButtons(Enum):

    """Map LCD pins to control events."""

    MENU = 1
    SELECT = 2
    PLUS = 3
    MINUS = 4
    POWER = 5
    SOURCE = 6


class FASTAudio(HardwareSoundPlatformInterface):

    """Hardware sound system using the FAST Audio board."""

    __slots__ = ["lcd_keys", "platform", "send", "track_keys"]

    def __init__(self, platform, sender, platform_settings={}):
        self.platform = platform
        self.platform.log.info("Creating FAST audio system: %s", self)
        self.platform.log.info(" - sender is %s", sender)
        self.platform.log.info("Platform settings: %s", platform_settings)
        self.send = sender
        self.track_keys = {
            FastAudioDevices.SPEAKER: "AV",
            FastAudioDevices.SUBWOOFER: "AS",
            FastAudioDevices.HEADPHONES: "AH"
        }

        self.lcd_keys = {}
        for key, value in platform_settings.items():
            if key == "lcd_pin_menu":
                self.lcd_keys[FastLcdButtons.MENU] = value
            elif key == "lcd_pin_select":
                self.lcd_keys[FastLcdButtons.SELECT] = value
            elif key == "lcd_pin_power":
                self.lcd_keys[FastLcdButtons.POWER] = value
            elif key == "lcd_pin_plus":
                self.lcd_keys[FastLcdButtons.PLUS] = value
            elif key == "lcd_pin_minus":
                self.lcd_keys[FastLcdButtons.MINUS] = value
            elif key == "lcd_pin_source":
                self.lcd_keys[FastLcdButtons.SOURCE] = value

    def play_sound(self, number: int, track: int = 1):
        """Play a sound."""
        raise NotImplementedError

    def play_sound_file(self, file: str, platform_options: dict, track: int = 1):
        """Play a sound file."""
        raise NotImplementedError

    def text_to_speech(self, text: str, platform_options: dict, track: int = 1):
        """Text to speech output."""
        raise NotImplementedError

    def stop_all_sounds(self, track: int = 1):
        """Play a sound."""
        raise NotImplementedError

    def set_speakers(self, volume: float):
        self.set_volume(FastAudioDevices.SPEAKER, volume)

    def set_headphones(self, volume: float):
        self.set_volume(FastAudioDevices.HEADPHONES, volume)

    def set_subwoofer(self, volume: float):
        self.set_volume(FastAudioDevices.SUBWOOFER, volume)

    def set_volume(self, volume: float, track: int = 1):
        """Set volume."""
        # FAST Audio board supports 64 levels of precision, so convert the float accordingly
        value = Util.int_to_hex_string(ceil(volume * 64))
        msg = f"{self.track_keys[track]}:{Util.int_to_hex_string(value)}"
        self.send_and_forget(msg)

    def press_power(self, ms=None):
        self._press(FastLcdButtons.POWER)

    def press_menu(self, ms=None):
        self._press(FastLcdButtons.MENU)

    def press_plus(self, ms=None):
        self._press(FastLcdButtons.PLUS)

    def press_minus(self, ms=None):
        self._press(FastLcdButtons.MINUS)

    def press_select(self, ms=None):
        self._press(FastLcdButtons.SELECT)

    def press_source(self, ms=None):
        self._press(FastLcdButtons.SOURCE)

    def _press(self, target: FastLcdButtons, ms=10):
        if not target in self.lcd_keys:
            raise ValueError(f"LCD button for {target} is not defined in platform settings ({self.lcd_keys.keys()}")
        self.send_and_forget(f"XO:{self.lcd_keys[target]},{Util.int_to_hex_string(ms)}")
