from packaging import version

from mpf.platforms.fast.communicators.base import FastSerialCommunicator
from mpf.platforms.fast.fast_audio import FASTAudioInterface


class FastAudCommunicator(FastSerialCommunicator):

    """Handles the serial communication to the FAST platform."""

    # Notes on this class, versus the FASTAudioInterface class in mpf/platforms/fast/fast_audio.py:

    # FastAudCommunicator should just focus on actually talking to the hardware. It will deal in hardware
    # levels 0-63, and handle decoding/encoding the config bitmask, etc.
    # FastAudioInterface should handle the higher level stuff, like volume scaling, and the general
    # interface into the rest of MPF (reading configs, interacting with events, etc.)

    MIN_FW = version.parse('0.10')
    IGNORED_MESSAGES = ['AV:', 'AS:', 'AH:', 'AM:']

    # __slots__ = []

    def __init__(self, platform, processor, config):

        super().__init__(platform, processor, config)

    async def init(self):
        self.platform.audio_interface = FASTAudioInterface(self.platform, self)
        # set volumes
        # send settings

    async def clear_board_serial_buffer(self):
        pass

    async def soft_reset(self):
        # rewrite current volumes and config
        pass

    def set_volume(self, amp, volume):
        pass

    def get_volume(self, amp):
        pass

    def enable_amp(self, amp):
        pass

    def disable_amp(self, amp):
        pass

    def set_phones_level(self, mode, send_now=True):
        # phones or line
        pass

    def set_phones_behavior(self, behavior, send_now=True):
        # mute or ignore
        pass

    def send_config_to_board(self):
        pass

    def save_settings_to_firmware(self):
        pass

    def set_watchdog(self, timeout):
        pass

    def get_phones_status(self):
        pass

    def get_power_status(self):
        pass

    def pulse_output_pin(self, pin, ms):
        pass
