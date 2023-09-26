# mpf/platforms/fast/communicators/net_nano.py

from packaging import version

from mpf.platforms.fast.communicators.net_neuron import FastNetNeuronCommunicator


class FastNetNanoCommunicator(FastNetNeuronCommunicator):

    MIN_FW = version.parse('1.05')
    IO_MIN_FW = version.parse('1.05')
    IGNORED_MESSAGES = ['WD:P', 'TN:P']
    MAX_IO_BOARDS = 9
    MAX_SWITCHES = 108
    MAX_DRIVERS = 48
    TRIGGER_CMD = 'TN'
    DRIVER_CMD = 'DN'
    SWITCH_CMD = 'SN'

    async def configure_hardware(self):
        pass # Not used on a Nano

    def _process_sa(self, msg):
        # Nano has slightly different variation of this value, get it into a format the base can process
        _, _, _, raw_switch_data = msg.split(',')
        super()._process_sa(f'00,{raw_switch_data}')

    def _process_boot_message(self, msg):
        if msg == '00':  # rebooting
            self.machine.stop("FAST NET Nano rebooted")

        if msg == '02':  # reboot done
            self._process_reboot_done()
            # TODO what else? Mark all configs as dirty? Log and warn if this was unexpected?
            # TODO add ignore_reboot option to config