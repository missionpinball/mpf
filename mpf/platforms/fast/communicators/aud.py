from packaging import version

from mpf.platforms.fast.communicators.base import FastSerialCommunicator
from mpf.platforms.fast.fast_audio import FASTAudioInterface
from mpf.core.utility_functions import Util


class FastAudCommunicator(FastSerialCommunicator):

    """Handles the serial communication to the FAST platform."""

    # Notes on this class, versus the FASTAudioInterface class in mpf/platforms/fast/fast_audio.py:

    # FastAudCommunicator focuses on actually talking to the hardware. It will deal in hardware
    # levels 0-63, and handle decoding/encoding the config bitmask, etc.
    # FastAudioInterface handles the higher level stuff, like volume scaling, and the general
    # interface into the rest of MPF (reading configs, interacting with events, etc.)

    MIN_FW = version.parse('0.10')
    IGNORED_MESSAGES = ['AV:', 'AS:', 'AH:', 'AM:']

    __slots__ = ["amps", "current_config_byte", "phones_level", "phones_mute", "_watchdog_ms"]

    def __init__(self, platform, processor, config):

        super().__init__(platform, processor, config)
        self.amps = {
            'main':
                {'cmd': 'AV',
                 'volume': '00',
                 'enabled': False,
                 },
            'sub':
                {'cmd': 'AS',
                 'volume': '00',
                 'enabled': False,
                 },
            'headphones':
                {'cmd': 'AH',
                 'volume': '00',
                 'enabled': False,
                 },
            }
        self.current_config_byte = '00'
        self.phones_level = True  # False = line, True = phones
        self.phones_mute = False  # False = ignore phones insertion, True = mute main/sub when phones inserted
        self._watchdog_ms = 0

    async def init(self):
        await self.send_and_wait_for_response_processed('ID:', 'ID:', max_retries=-1)  # Loop here until we get a response
        self.platform.audio_interface = FASTAudioInterface(self.platform, self)

    async def soft_reset(self):
        self.update_config(send_now=True)
        for amp in self.amps:
            self.set_volume(amp, int(self.amps[amp]['volume'], 16))

    def _volume_to_hw(self, volume):
        volume = int(volume)
        assert 0 <= volume <= 63, f"Invalid volume {volume}"
        return f"{volume:02X}"

    def update_config(self, send_now=True):
        byte = '00'
        if self.amps['main']['enabled']:
            byte = Util.set_bit(byte, 0)
        if self.amps['sub']['enabled']:
            byte = Util.set_bit(byte, 1)
        if self.amps['headphones']['enabled']:
            if not self.phones_level:  # line level
                byte = Util.set_bit(byte, 2)
                byte = Util.set_bit(byte, 3)
            else:  # phones level
                if self.phones_mute:
                    byte = Util.set_bit(byte, 3)
                else:
                    byte = Util.set_bit(byte, 2)

        self.current_config_byte = byte

        if send_now:
            self.send_config_to_board()

    def set_volume(self, amp, volume, send_now=True):
        if amp not in self.amps:
            raise AssertionError(f"Invalid amp {amp}")

        volume = self._volume_to_hw(volume)
        self.amps[amp]['volume'] = volume
        if send_now:
            self.send_and_forget(f"{self.amps[amp]['cmd']}:{volume}")

    def get_volume(self, amp):
        return int(self.amps[amp]['volume'], 16)

    def enable_amp(self, amp, send_now=True):
        if amp not in self.amps:
            raise AssertionError(f"Invalid amp {amp}")
        self.amps[amp]['enabled'] = True
        self.update_config(send_now)

    def disable_amp(self, amp, send_now=True):
        if amp not in self.amps:
            raise AssertionError(f"Invalid amp {amp}")
        self.amps[amp]['enabled'] = False
        self.update_config(send_now)

    def set_phones_level(self, mode, send_now=True):
        if mode == 'line':
            self.phones_level = False
        elif mode == 'headphones':
            self.phones_level = True
        else:
            raise AssertionError(f"Invalid phones level {mode}")

        self.update_config(send_now)

    def set_phones_behavior(self, behavior, send_now=True):
        # Will return False if not possible, true if ok
        if not self.phones_level:  # phones are line level, this does not apply
            return False

        if behavior == 'mute':
            self.phones_mute = True
        elif behavior == 'ignore':
            self.phones_mute = False
        else:
            raise AssertionError(f"Invalid phones behavior {behavior}")

        self.update_config(send_now)
        return True

    def send_config_to_board(self):
        self.send_and_forget(f"AM:{self.current_config_byte}")

    def save_settings_to_firmware(self):
        self.send_and_forget("AW:")

    def set_watchdog(self, timeout):
        pass
        # TODO setup task to send watchdog

    def get_phones_status(self):
        pass
        # TODO WD command processing

    def get_power_status(self):
        pass
        # TODO WD command processing

    def pulse_control_pin(self, pin, ms):
        assert 0 <= pin <= 7, f"Invalid pin {pin}"
        self.send_and_forget(f"XO:{pin:02X},{hex(ms)[2:].upper()}")
