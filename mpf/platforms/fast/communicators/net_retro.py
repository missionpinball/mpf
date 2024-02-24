# mpf/platforms/fast/communicators/net_retro.py

from mpf.platforms.fast.communicators.net_neuron import FastNetNeuronCommunicator

class FastNetRetroCommunicator(FastNetNeuronCommunicator):

    MAX_SWITCHES = 96  # prev version was 128
    MAX_DRIVERS = 48   # prev version was 64
    IGNORED_MESSAGES = ['WD:P', 'TL:P', 'L1:P', 'GI:P']

    async def query_io_boards(self):

         # No external I/O boards on a Retro Controller, so create one to represent the onboard switches & drivers

        self.io_loop = ['retro']  # Manually create the internal I/O board since it's not in the config
        self.config['io_loop']['retro'] = {'model': 'FP-RETRO-I/O',
                                           'order': 0,
                                           }


        # Simplest way is just to fake a response to the NN: query
        # NN:<NODE_ID>,<NODE_NAME>,<NODE_FIRMWARE>,<DRIVER_COUNT>,<SWITCH_COUNT>,<EXTRADATA_IN>,<EXTRADATA_OUT>
        self._process_nn(f'00,FP-RETRO-I/O,{self.remote_firmware},{self.MAX_DRIVERS:02X},{self.MAX_SWITCHES:02X},0,0,0,0,0,0')
