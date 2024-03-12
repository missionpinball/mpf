# mpf/platforms/fast/communicators/rgb.py

from packaging import version

from mpf.core.utility_functions import Util
from mpf.platforms.fast.communicators.base import FastSerialCommunicator

MIN_FW = version.parse('0.87') # override in subclass

class FastRgbCommunicator(FastSerialCommunicator):

    """Handles the serial communication for legacy FAST RGB processors.

    Includes the Nano Controller and FP-EXP-0800 LED controller.
    """

    IGNORED_MESSAGES = ['RX:P']

    def __init__(self, platform, processor, config):
        """Initialize the RGB platform and process boot message."""
        super().__init__(platform, processor, config)

        self.message_processors['!B:'] = self._process_boot_msg

    async def init(self):
        await self.send_and_wait_for_response_processed('ID:', 'ID:', max_retries=-1)  # Loop here until we get a response

    def _process_boot_msg(self, msg):
        """Process bootloader message."""
        self.log.debug("Got Bootloader message: !B:%s", msg)
        if msg in ('00', '02'):
            if self.config['ignore_reboot']:
                self.machine.events.post("fast_rgb_rebooted", msg=msg)
                self.log.error("FAST RGB processor rebooted. Ignoring.")
            else:
                self.log.error("FAST RGB processor rebooted.")
                self.machine.stop("FAST RGB processor rebooted")

    def update_leds(self):
        """Update all the LEDs connected to the RGB processor of a FAST Nano controller.

        This is done once per game loop for efficiency (i.e. all LEDs are sent as a single
        update rather than lots of individual ones).

        """
        dirty_leds = [led for led in self.platform.fast_rgb_leds.values() if led.dirty]

        if dirty_leds:
            msg = 'RS:' + ','.join(["%s%s" % (led.number, led.current_color) for led in dirty_leds])
            self.send_and_forget(msg)

    def start_tasks(self):
        """Start listening for commands and schedule watchdog."""
        self.reset()

        if self.config['led_hz'] > 30:
            self.config['led_hz'] = 30

        self.tasks.append(self.machine.clock.schedule_interval(
                          self.update_leds, 1 / self.config['led_hz']))

    async def soft_reset(self, **kwargs):
        """Reset the NET processor."""
        del kwargs
        #await self.send_and_wait_for_response('RA:000000', 'RX:P')
        self.send_and_forget("RA:000000")

    def reset(self):
        """Reset the RGB processor."""
        # self.send_and_forget('RF:0')  # TODO confirm if the RGB supports RF. I think not?
        self.send_and_forget('RA:000000')
        # self.send_and_forget(f"RF:{Util.int_to_hex_string(self.config['led_fade_time'])}")

    def stopping(self):
        self.reset()
