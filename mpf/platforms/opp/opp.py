"""OPP Hardware interface.

Contains the hardware interface and drivers for the Open Pinball Project
platform hardware, including the solenoid, input, incandescent, and neopixel
boards.
"""
import logging
import asyncio

from mpf.platforms.base_serial_communicator import BaseSerialCommunicator

from mpf.platforms.opp.opp_coil import OPPSolenoidCard
from mpf.platforms.opp.opp_incand import OPPIncandCard
from mpf.platforms.opp.opp_neopixel import OPPNeopixelCard
from mpf.platforms.opp.opp_switch import OPPInputCard
from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf
from mpf.devices.driver import ConfiguredHwDriver
from mpf.core.platform import MatrixLightsPlatform, LedPlatform, SwitchPlatform, DriverPlatform

# Minimum firmware versions needed for this module
MIN_FW = 0x00000100
BAD_FW_VERSION = 0x01020304


# pylint: disable-msg=too-many-instance-attributes
class HardwarePlatform(MatrixLightsPlatform, LedPlatform, SwitchPlatform, DriverPlatform):

    """Platform class for the OPP hardware.

    Args:
        machine: The main ``MachineController`` instance.

    """

    def __init__(self, machine):
        """Initialise OPP platform."""
        super(HardwarePlatform, self).__init__(machine)
        self.log = logging.getLogger('OPP')
        self.log.info("Configuring OPP hardware.")

        self.opp_connection = {}    # type: {OPPSerialCommunicator}
        self.serial_connections = set()
        self.opp_incands = []
        self.incandDict = dict()
        self.opp_solenoid = []
        self.solDict = dict()
        self.opp_inputs = []
        self.inpDict = dict()
        self.inpAddrDict = dict()
        self.read_input_msg = {}
        self.opp_neopixels = []
        self.neoCardDict = dict()
        self.neoDict = dict()
        self.numGen2Brd = 0
        self.gen2AddrArr = {}
        self.badCRC = 0
        self.minVersion = 0xffffffff
        self._poll_task = None
        self._light_update_task = None

        self.features['tickless'] = True

        self.config = self.machine.config['opp']
        self.machine.config_validator.validate_config("opp", self.config)

        self.machine_type = (
            self.machine.config['hardware']['driverboards'].lower())

        if self.machine_type == 'gen1':
            self.log.debug("Configuring the original OPP boards")
            raise AssertionError("Original OPP boards not currently supported.")
        elif self.machine_type == 'gen2':
            self.log.debug("Configuring the OPP Gen2 boards")
        else:
            raise AssertionError('Invalid driverboards type: {}'.format(self.machine_type))

        # Only including responses that should be received
        self.opp_commands = {
            ord(OppRs232Intf.INV_CMD): self.inv_resp,
            ord(OppRs232Intf.EOM_CMD): self.eom_resp,
            ord(OppRs232Intf.GET_GEN2_CFG): self.get_gen2_cfg_resp,
            ord(OppRs232Intf.READ_GEN2_INP_CMD): self.read_gen2_inp_resp_initial,
            ord(OppRs232Intf.GET_GET_VERS_CMD): self.vers_resp,
        }

    def initialize(self):
        """Initialise connections to OPP hardware."""
        self._connect_to_hardware()
        self.opp_commands[ord(OppRs232Intf.READ_GEN2_INP_CMD)] = self.read_gen2_inp_resp
        self._poll_task = self.machine.clock.loop.create_task(self._poll_sender())
        self._poll_task.add_done_callback(self._done)

    def stop(self):
        """Stop hardware and close connections."""
        if self._poll_task:
            self._poll_task.cancel()

        if self._light_update_task:
            self._light_update_task.cancel()

        for connections in self.serial_connections:
            connections.stop()

    def __repr__(self):
        """String representation."""
        return '<Platform.OPP>'

    def process_received_message(self, chain_serial, msg):
        """Send an incoming message from the OPP hardware to the proper method for servicing.

        Args:
            chain_serial: Serial of the chain which received the message.
            msg: Message to parse.
        """
        if len(msg) >= 1:
            if ((msg[0] >= ord(OppRs232Intf.CARD_ID_GEN2_CARD)) and
                    (msg[0] < (ord(OppRs232Intf.CARD_ID_GEN2_CARD) + 0x20))):
                if len(msg) >= 2:
                    cmd = msg[1]
                else:
                    cmd = OppRs232Intf.ILLEGAL_CMD
            # Look for EOM or INV commands
            elif msg[0] == ord(OppRs232Intf.INV_CMD) or msg[0] == ord(OppRs232Intf.EOM_CMD):
                cmd = msg[0]
            else:
                cmd = OppRs232Intf.ILLEGAL_CMD
        else:
            # No messages received, fake an EOM
            cmd = OppRs232Intf.EOM_CMD

        # Can't use try since it swallows too many errors for now
        if cmd in self.opp_commands:
            self.opp_commands[cmd](chain_serial, msg)
        else:
            self.log.warning("Received unknown serial command?%s. (This is "
                             "very worrisome.)", "".join(" 0x%02x" % b for b in msg))

            # TODO: This means synchronization is lost.  Send EOM characters
            #  until they come back

    def _connect_to_hardware(self):
        """Connect to each port from the config.

        This process will cause the OPPSerialCommunicator to figure out which chains they've connected to
        and to register themselves.
        """
        for port in self.config['ports']:
            self.serial_connections.add(OPPSerialCommunicator(
                platform=self, port=port, baud=self.config['baud']))

    def register_processor_connection(self, serial_number, communicator):
        """Register the processors to the platform.

        Args:
            serial_number: Serial number of chain.
            communicator: Instance of OPPSerialCommunicator
        """
        self.opp_connection[serial_number] = communicator

    def send_to_processor(self, chain_serial, msg):
        """Send message to processor with specific serial number.

        Args:
            chain_serial: Serial of the processor.
            msg: Message to send.
        """
        self.opp_connection[chain_serial].send(msg)

    def update_incand(self):
        """Update all the incandescents connected to OPP hardware.

        This is done once per game loop if changes have been made.

        It is currently assumed that the oversampling will guarantee proper communication
        with the boards.  If this does not end up being the case, this will be changed
        to update all the incandescents each loop.

        Note:  This could be made much more efficient by supporting a command
        that simply sets the state of all 32 of the LEDs as either on or off.
        """
        for incand in self.opp_incands:
            whole_msg = bytearray()
            # Check if any changes have been made
            if (incand.oldState ^ incand.newState) != 0:
                # Update card
                incand.oldState = incand.newState
                msg = bytearray()
                msg.append(incand.addr)
                msg.extend(OppRs232Intf.INCAND_CMD)
                msg.extend(OppRs232Intf.INCAND_SET_ON_OFF)
                msg.append((incand.newState >> 24) & 0xff)
                msg.append((incand.newState >> 16) & 0xff)
                msg.append((incand.newState >> 8) & 0xff)
                msg.append(incand.newState & 0xff)
                msg.extend(OppRs232Intf.calc_crc8_whole_msg(msg))
                whole_msg.extend(msg)

            if len(whole_msg) != 0:
                whole_msg.extend(OppRs232Intf.EOM_CMD)
                send_cmd = bytes(whole_msg)

                self.send_to_processor(incand.chain_serial, send_cmd)
                self.log.debug("Update incand cmd:%s", "".join(" 0x%02x" % b for b in send_cmd))

    @classmethod
    def get_coil_config_section(cls):
        """Return coil config section."""
        return "opp_coils"

    def get_hw_switch_states(self):
        """Get initial hardware switch states."""
        hw_states = dict()
        for opp_inp in self.opp_inputs:
            curr_bit = 1
            for index in range(0, 32):
                if (curr_bit & opp_inp.mask) != 0:
                    if (curr_bit & opp_inp.oldState) == 0:
                        hw_states[opp_inp.chain_serial + '-' + opp_inp.cardNum + '-' + str(index)] = 1
                    else:
                        hw_states[opp_inp.chain_serial + '-' + opp_inp.cardNum + '-' + str(index)] = 0
                curr_bit <<= 1
        return hw_states

    def inv_resp(self, chain_serial, msg):
        """Parse inventory response.

        Args:
            chain_serial: Serial of the chain which received the message.
            msg: Message to parse.
        """
        # TODO: use chain_serial/move to serial communicator
        self.log.debug("Received Inventory Response:%s", "".join(" 0x%02x" % b for b in msg))

        index = 1
        self.gen2AddrArr[chain_serial] = []
        while msg[index] != ord(OppRs232Intf.EOM_CMD):
            if (msg[index] & ord(OppRs232Intf.CARD_ID_TYPE_MASK)) == ord(OppRs232Intf.CARD_ID_GEN2_CARD):
                self.numGen2Brd += 1
                self.gen2AddrArr[chain_serial].append(msg[index])
            index += 1
        self.log.debug("Found %d Gen2 OPP boards.", self.numGen2Brd)

    @staticmethod
    def eom_resp(chain_serial, msg):
        """Process an EOM.

        Args:
            chain_serial: Serial of the chain which received the message.
            msg: Message to parse.
        """
        # An EOM command can be used to resynchronize communications if message synch is lost
        pass

    def _parse_gen2_board(self, chain_serial, msg, read_input_msg):
        has_neo = False
        wing_index = 0
        sol_mask = 0
        inp_mask = 0
        incand_mask = 0
        while wing_index < OppRs232Intf.NUM_G2_WING_PER_BRD:
            if msg[2 + wing_index] == ord(OppRs232Intf.WING_SOL):
                sol_mask |= (0x0f << (4 * wing_index))
                inp_mask |= (0x0f << (8 * wing_index))
            elif msg[2 + wing_index] == ord(OppRs232Intf.WING_INP):
                inp_mask |= (0xff << (8 * wing_index))
            elif msg[2 + wing_index] == ord(OppRs232Intf.WING_INCAND):
                incand_mask |= (0xff << (8 * wing_index))
            elif msg[2 + wing_index] == ord(OppRs232Intf.WING_NEO):
                has_neo = True
            wing_index += 1
        if incand_mask != 0:
            self.opp_incands.append(OPPIncandCard(chain_serial, msg[0], incand_mask, self.incandDict))
        if sol_mask != 0:
            self.opp_solenoid.append(
                OPPSolenoidCard(chain_serial, msg[0], sol_mask, self.solDict, self))
        if inp_mask != 0:
            # Create the input object, and add to the command to read all inputs
            self.opp_inputs.append(OPPInputCard(chain_serial, msg[0], inp_mask, self.inpDict,
                                   self.inpAddrDict))

            # Add command to read all inputs to read input message
            inp_msg = bytearray()
            inp_msg.append(msg[0])
            inp_msg.extend(OppRs232Intf.READ_GEN2_INP_CMD)
            inp_msg.append(0)
            inp_msg.append(0)
            inp_msg.append(0)
            inp_msg.append(0)
            inp_msg.extend(OppRs232Intf.calc_crc8_whole_msg(inp_msg))
            read_input_msg.extend(inp_msg)

        if has_neo:
            self.opp_neopixels.append(OPPNeopixelCard(chain_serial, msg[0], self.neoCardDict, self))

    def get_gen2_cfg_resp(self, chain_serial, msg):
        """Process cfg response.

        Args:
            chain_serial: Serial of the chain which received the message.
            msg: Message to parse.
        """
        # Multiple get gen2 cfg responses can be received at once
        self.log.debug("Received Gen2 Cfg Response:%s", "".join(" 0x%02x" % b for b in msg))
        curr_index = 0
        read_input_msg = bytearray()
        while True:
            # check that message is long enough
            if len(msg) < curr_index + 6:
                self.log.warning("Msg is too short: %s.", "".join(" 0x%02x" % b for b in msg))
                self.opp_connection[chain_serial].lost_synch()
            # Verify the CRC8 is correct
            crc8 = OppRs232Intf.calc_crc8_part_msg(msg, curr_index, 6)
            if msg[curr_index + 6] != ord(crc8):
                self.badCRC += 1
                self.log.warning("Msg contains bad CRC:%s.", "".join(" 0x%02x" % b for b in msg))
                break
            else:
                self._parse_gen2_board(chain_serial, msg[curr_index:curr_index + 6], read_input_msg)

            if msg[curr_index + 7] == ord(OppRs232Intf.EOM_CMD):
                break
            elif msg[curr_index + 8] == ord(OppRs232Intf.GET_GEN2_CFG):
                curr_index += 7
            else:
                self.log.warning("Malformed GET_GEN2_CFG response:%s.",
                                 "".join(" 0x%02x" % b for b in msg))
                self.opp_connection[chain_serial].lost_synch()
                break

        read_input_msg.extend(OppRs232Intf.EOM_CMD)
        self.read_input_msg[chain_serial] = bytes(read_input_msg)

    def vers_resp(self, chain_serial, msg):
        """Process version response.

        Args:
            chain_serial: Serial of the chain which received the message.
            msg: Message to parse.
        """
        # Multiple get version responses can be received at once
        self.log.debug("Received Version Response:%s", "".join(" 0x%02x" % b for b in msg))
        end = False
        curr_index = 0
        while not end:
            # Verify the CRC8 is correct
            crc8 = OppRs232Intf.calc_crc8_part_msg(msg, curr_index, 6)
            if msg[curr_index + 6] != ord(crc8):
                self.badCRC += 1
                hex_string = "".join(" 0x%02x" % b for b in msg)
                self.log.warning("Msg contains bad CRC:%s.", hex_string)
                end = True
            else:
                version = (msg[curr_index + 2] << 24) | \
                    (msg[curr_index + 3] << 16) | \
                    (msg[curr_index + 4] << 8) | \
                    msg[curr_index + 5]
                self.log.debug("Firmware version: %d.%d.%d.%d", msg[curr_index + 2],
                               msg[curr_index + 3], msg[curr_index + 4],
                               msg[curr_index + 5])
                if version < self.minVersion:
                    self.minVersion = version
                if version == BAD_FW_VERSION:
                    raise AssertionError("Original firmware sent only to Brian before adding "
                                         "real version numbers. The firmware must be updated before "
                                         "MPF will work.")
            if not end:
                if msg[curr_index + 7] == ord(OppRs232Intf.EOM_CMD):
                    end = True
                elif msg[curr_index + 8] == ord(OppRs232Intf.GET_GET_VERS_CMD):
                    curr_index += 7
                else:
                    hex_string = "".join(" 0x%02x" % b for b in msg)
                    self.log.warning("Malformed GET_VERS_CMD response:%s.", hex_string)
                    end = True
                    self.opp_connection[chain_serial].lost_synch()

    def read_gen2_inp_resp_initial(self, chain_serial, msg):
        """Read initial switch states.

        Args:
            chain_serial: Serial of the chain which received the message.
            msg: Message to parse.
        """
        # Verify the CRC8 is correct
        if len(msg) < 6:
            raise AssertionError("Received too short initial input response: " + "".join(" 0x%02x" % b for b in msg))
        crc8 = OppRs232Intf.calc_crc8_part_msg(msg, 0, 6)
        if msg[6] != ord(crc8):
            self.badCRC += 1
            self.log.warning("Msg contains bad CRC:%s.", "".join(" 0x%02x" % b for b in msg))
        else:
            opp_inp = self.inpAddrDict[chain_serial + '-' + str(msg[0])]
            new_state = (msg[2] << 24) | \
                (msg[3] << 16) | \
                (msg[4] << 8) | \
                msg[5]

            opp_inp.oldState = new_state

    def read_gen2_inp_resp(self, chain_serial, msg):
        """Read switch changes.

        Args:
            chain_serial: Serial of the chain which received the message.
            msg: Message to parse.
        """
        # Single read gen2 input response.  Receive function breaks them down

        # Verify the CRC8 is correct
        if len(msg) < 6:
            self.log.warning("Msg too shortC: %s.", "".join(" 0x%02x" % b for b in msg))
            self.opp_connection[chain_serial].lost_synch()
            return

        crc8 = OppRs232Intf.calc_crc8_part_msg(msg, 0, 6)
        if msg[6] != ord(crc8):
            self.badCRC += 1
            self.log.warning("Msg contains bad CRC:%s.", "".join(" 0x%02x" % b for b in msg))
        else:
            opp_inp = self.inpAddrDict[chain_serial + '-' + str(msg[0])]
            new_state = (msg[2] << 24) | \
                (msg[3] << 16) | \
                (msg[4] << 8) | \
                msg[5]

            # Update the state which holds inputs that are active
            changes = opp_inp.oldState ^ new_state
            if changes != 0:
                curr_bit = 1
                for index in range(0, 32):
                    if (curr_bit & changes) != 0:
                        if (curr_bit & new_state) == 0:
                            self.machine.switch_controller.process_switch_by_num(
                                state=1,
                                num=opp_inp.chain_serial + '-' + opp_inp.cardNum + '-' + str(index),
                                platform=self)
                        else:
                            self.machine.switch_controller.process_switch_by_num(
                                state=0,
                                num=opp_inp.chain_serial + '-' + opp_inp.cardNum + '-' + str(index),
                                platform=self)
                    curr_bit <<= 1
            opp_inp.oldState = new_state

    def reconfigure_driver(self, driver, use_hold: bool):
        """Reconfigure a driver.

        Args:
            driver: Driver object.
            use_hold: Whether this driver stays enabled after a trigger or not.
        """
        # If hold is 0, set the auto clear bit
        if not use_hold:
            cmd = ord(OppRs232Intf.CFG_SOL_AUTO_CLR)
            driver.hw_driver.can_be_pulsed = True
            hold = 0
        else:
            cmd = 0
            driver.hw_driver.can_be_pulsed = False
            hold = self.get_hold_value(driver)
            if not hold:
                raise AssertionError("Hold may not be 0")

        # TODO: implement separate hold power (0-f) and minimum off time (0-7)
        minimum_off = self.get_minimum_off_time(driver)

        if driver.hw_driver.use_switch:
            cmd += ord(OppRs232Intf.CFG_SOL_USE_SWITCH)

        _, solenoid = driver.config['number'].split('-')
        pulse_len = self._get_pulse_ms_value(driver)

        msg = bytearray()
        msg.append(driver.hw_driver.solCard.addr)
        msg.extend(OppRs232Intf.CFG_IND_SOL_CMD)
        msg.append(int(solenoid))
        msg.append(cmd)
        msg.append(pulse_len)
        msg.append(hold + (minimum_off << 4))
        msg.extend(OppRs232Intf.calc_crc8_whole_msg(msg))
        msg.extend(OppRs232Intf.EOM_CMD)
        final_cmd = bytes(msg)

        self.log.debug("Writing individual config: %s", "".join(" 0x%02x" % b for b in final_cmd))
        self.send_to_processor(driver.hw_driver.solCard.chain_serial, final_cmd)

    def _get_dict_index(self, input_str):
        try:
            chain_str, card_str, number_str = input_str.split("-")
        except ValueError:
            chain_str = '0'
            try:
                card_str, number_str = input_str.split("-")
            except ValueError:
                card_str = '0'
                number_str = input_str

        if chain_str not in self.config['chains']:
            if len(self.config['ports']) > 1:
                raise AssertionError("Chain {} is unconfigured".format(chain_str))
            else:
                # when there is only one port, use only available chain
                chain_serial = list(self.serial_connections)[0].chain_serial
        else:
            chain_serial = self.config['chains'][chain_str]

        return chain_serial + "-" + card_str + "-" + number_str

    def configure_driver(self, config: dict):
        """Configure a driver.

        Args:
            config: Config dict.
        """
        if not self.opp_connection:
            raise AssertionError("A request was made to configure an OPP solenoid, "
                                 "but no OPP connection is available")

        number = self._get_dict_index(config['number'])

        if number not in self.solDict:
            raise AssertionError("A request was made to configure an OPP solenoid "
                                 "with number {} which doesn't exist".format(config['number']))

        # Use new update individual solenoid command
        opp_sol = self.solDict[number]
        if not config['pulse_ms']:
            config['pulse_ms'] = self.machine.config['mpf']['default_pulse_ms']
        opp_sol.config = config
        self.log.debug("Config driver %s, %s, %s", number,
                       opp_sol.config['pulse_ms'], opp_sol.config['hold_power'])

        hold = self.get_hold_value(opp_sol)
        self.reconfigure_driver(ConfiguredHwDriver(opp_sol, {}), hold != 0)

        return opp_sol

    def configure_switch(self, config: dict):
        """Configure a switch.

        Args:
            config: Config dict.
        """
        # A switch is termed as an input to OPP
        if not self.opp_connection:
            raise AssertionError("A request was made to configure an OPP switch, "
                                 "but no OPP connection is available")

        number = self._get_dict_index(config['number'])

        if number not in self.inpDict:
            raise AssertionError("A request was made to configure an OPP switch "
                                 "with number %s which doesn't exist", number)

        return self.inpDict[number]

    def configure_led(self, config: dict, channels: int):
        """Configure LED.

        Args:
            config: Config dict.
            channels: Number of channels. OPP supports up to three.
        """
        if channels > 3:
            raise AssertionError("OPP only supports RGB LEDs")
        if not self.opp_connection:
            raise AssertionError("A request was made to configure an OPP LED, "
                                 "but no OPP connection is available")

        number = self._get_dict_index(config['number'])

        chain_serial, card, pixel_num = number.split('-')
        index = chain_serial + '-' + card
        if index not in self.neoCardDict:
            raise AssertionError("A request was made to configure an OPP neopixel "
                                 "with card number %s which doesn't exist", card)

        neo = self.neoCardDict[index]
        pixel = neo.add_neopixel(int(pixel_num), self.neoDict)

        return pixel

    def configure_matrixlight(self, config):
        """Configure a direct incandescent bulb.

        Args:
            config: Config dict.
        """
        if not self.opp_connection:
            raise AssertionError("A request was made to configure an OPP matrix "
                                 "light (incand board), but no OPP connection "
                                 "is available")

        number = self._get_dict_index(config['number'])

        if number not in self.incandDict:
            raise AssertionError("A request was made to configure a OPP matrix "
                                 "light (incand board), with number %s "
                                 "which doesn't exist", number)

        if not self._light_update_task:
            self._light_update_task = self.machine.clock.loop.create_task(self._update_lights())
            self._light_update_task.add_done_callback(self._done)
        return self.incandDict[number]

    @staticmethod
    def _done(future):
        """Evaluate result of task.

        Will raise exceptions from within task.
        """
        future.result()

    @asyncio.coroutine
    def _poll_sender(self):
        """Poll switches."""
        while True:
            for chain_serial in self.read_input_msg:
                self.send_to_processor(chain_serial, self.read_input_msg[chain_serial])
                yield from self.opp_connection[chain_serial].writer.drain()
                # the line above saturates the link and seems to overhelm the hardware. limit it to 100Hz
                yield from asyncio.sleep(.01, loop=self.machine.clock.loop)

    @asyncio.coroutine
    def _update_lights(self):
        """Update matrix lights."""
        while True:
            self.update_incand()
            for connection in self.opp_connection.values():
                yield from connection.writer.drain()
            # limit to 50Hz
            yield from asyncio.sleep(.02, loop=self.machine.clock.loop)

    @classmethod
    def _verify_coil_and_switch_fit(cls, switch, coil):
        chain_serial, card, solenoid = coil.hw_driver.number.split('-')
        sw_chain_serial, sw_card, sw_num = switch.hw_switch.number.split('-')
        matching_sw = ((int(solenoid) & 0x0c) << 1) | (int(solenoid) & 0x03)
        if chain_serial != sw_chain_serial or card != sw_card or matching_sw != int(sw_num):
            raise AssertionError('Invalid switch being configured for driver. Driver = %s '
                                 'Switch = %s' % (coil.hw_driver.number, switch.hw_switch.number))

    def set_pulse_on_hit_rule(self, enable_switch, coil):
        """Set pulse on hit rule on driver.

        Pulses a driver when a switch is hit. When the switch is released the pulse continues. Typically used for
        autofire coils such as pop bumpers.
        """
        # OPP always does the full pulse
        self._write_hw_rule(enable_switch, coil, False)

    def set_pulse_on_hit_and_release_rule(self, enable_switch, coil):
        """Set pulse on hit and release rule to driver.

        Pulses a driver when a switch is hit. When the switch is released the pulse is canceled. Typically used on
        the main coil for dual coil flippers without eos switch.
        """
        # OPP always does the full pulse. So this is not 100% correct
        self.set_pulse_on_hit_rule(enable_switch, coil)

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch, coil):
        """Set pulse on hit and enable and relase rule on driver.

        Pulses a driver when a switch is hit. Then enables the driver (may be with pwm). When the switch is released
        the pulse is canceled and the driver gets disabled. Typically used for single coil flippers.
        """
        # OPP always does the full pulse. Therefore, this is mostly right.
        if not self.get_hold_value(coil):
            raise AssertionError("Set allow_enable if you want to enable a coil without hold_power")

        self._write_hw_rule(enable_switch, coil, True)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch, disable_switch, coil):
        """Set pulse on hit and enable and release and disable rule on driver.

        Pulses a driver when a switch is hit. Then enables the driver (may be with pwm). When the switch is released
        the pulse is canceled and the driver gets disabled. When the second disable_switch is hit the pulse is canceled
        and the driver gets disabled. Typically used on the main coil for dual coil flippers with eos switch.
        """
        raise AssertionError("Not implemented in OPP currently")

    @classmethod
    def get_hold_value(cls, coil):
        """Get OPP hold value (0-15)."""
        if coil.config['hold_power16']:
            return coil.config['hold_power16']
        elif coil.config['hold_power']:
            if coil.config['hold_power'] >= 8:
                # OPP supports a maximum 15/16ms hold power
                return 15
            else:
                # hold_power is 0-8 and OPP supports 0-15
                return coil.config['hold_power'] * 2
        elif coil.config['allow_enable']:
            return 15
        else:
            return 0

    @classmethod
    def get_minimum_off_time(cls, coil):
        """Return minimum off factor.

        The hardware applies this factor to pulse_ms to prevent the coil from burning.
        """
        if not coil.config['recycle']:
            return 0
        elif coil.config['recycle_factor']:
            return coil.config['recycle_factor']
        else:
            # default to two times pulse_ms
            return 2

    def _get_pulse_ms_value(self, coil):
        if coil.config['pulse_ms']:
            return coil.config['pulse_ms']
        else:
            # use mpf default_pulse_ms
            return self.machine.config['mpf']['default_pulse_ms']

    def _write_hw_rule(self, switch_obj, driver_obj, use_hold):
        if switch_obj.invert:
            raise AssertionError("Cannot handle inverted switches")

        self._verify_coil_and_switch_fit(switch_obj, driver_obj)

        self.log.debug("Setting HW Rule. Driver: %s, Driver settings: %s",
                       driver_obj.hw_driver.number, driver_obj.config)

        driver_obj.hw_driver.use_switch = True
        self.reconfigure_driver(driver_obj, use_hold)

    def clear_hw_rule(self, switch, coil):
        """Clear a hardware rule.

        This is used if you want to remove the linkage between a switch and
        some driver activity. For example, if you wanted to disable your
        flippers (so that a player pushing the flipper buttons wouldn't cause
        the flippers to flip), you'd call this method with your flipper button
        as the *sw_num*.

        """
        self.log.debug("Clearing HW Rule for switch: %s, coils: %s", switch.hw_switch.number,
                       coil.hw_driver.number)

        coil.hw_driver.use_switch = False
        self.reconfigure_driver(coil, not coil.hw_driver.can_be_pulsed)


class OPPSerialCommunicator(BaseSerialCommunicator):

    """Manages a Serial connection to the first processor in a OPP serial chain."""

    # pylint: disable=too-many-arguments
    def __init__(self, platform: HardwarePlatform, port, baud):
        """Initialise Serial Connection to OPP Hardware."""
        self.partMsg = b""
        self.chain_serial = None
        self._lost_synch = False

        super().__init__(platform, port, baud)

    @asyncio.coroutine
    def _identify_connection(self):
        """Identify which processor this serial connection is talking to."""
        # keep looping and wait for an ID response
        count = 0
        resp = b''
        # read and discard all messages in buffer
        self.writer.write(OppRs232Intf.EOM_CMD)
        yield from asyncio.sleep(.01, loop=self.machine.clock.loop)
        yield from self.reader.read(1000)
        while True:
            if (count % 10) == 0:
                self.log.debug("Sending EOM command to port '%s'",
                               self.port)
            count += 1
            self.writer.write(OppRs232Intf.EOM_CMD)
            yield from asyncio.sleep(.01, loop=self.machine.clock.loop)
            resp = yield from self.reader.read(30)
            if resp.startswith(OppRs232Intf.EOM_CMD):
                break
            if count == 100:
                raise AssertionError('No response from OPP hardware: {}'.format(self.port))

        self.log.debug("Got ID response: %s", "".join(" 0x%02x" % b for b in resp))
        # TODO: implement real ID here
        self.chain_serial = self.port

        # Send inventory command to figure out number of cards
        msg = bytearray()
        msg.extend(OppRs232Intf.INV_CMD)
        msg.extend(OppRs232Intf.EOM_CMD)
        cmd = bytes(msg)

        self.log.debug("Sending inventory command: %s", "".join(" 0x%02x" % b for b in cmd))
        self.writer.write(cmd)

        resp = yield from self.readuntil(b'\xff')

        # resp will contain the inventory response.
        self.platform.process_received_message(self.chain_serial, resp)

        # Now send get gen2 configuration message to find populated wing boards
        self.send_get_gen2_cfg_cmd()
        resp = yield from self.readuntil(b'\xff', 6)

        # resp will contain the gen2 cfg reponses.  That will end up creating all the
        # correct objects.
        self.platform.process_received_message(self.chain_serial, resp)

        # get the version of the firmware
        self.send_vers_cmd()
        resp = yield from self.readuntil(b'\xff', 6)
        self.platform.process_received_message(self.chain_serial, resp)

        # see if version of firmware is new enough
        if self.platform.minVersion < MIN_FW:
            raise AssertionError("Firmware version mismatch. MPF requires"
                                 " the OPP Gen2 processor to be firmware {}, but yours is {}".
                                 format(self._create_vers_str(MIN_FW),
                                        self._create_vers_str(self.platform.minVersion)))

        # get initial value for inputs
        self.writer.write(self.platform.read_input_msg[self.chain_serial])
        cards = len([x for x in self.platform.opp_inputs if x.chain_serial == self.chain_serial])
        while True:
            resp = yield from self.readuntil(b'\xff')
            cards -= self._parse_msg(resp)
            if cards <= 0:
                break

        self.platform.register_processor_connection(self.chain_serial, self)

    def send_get_gen2_cfg_cmd(self):
        """Send get gen2 configuration message to find populated wing boards."""
        whole_msg = bytearray()
        for card_addr in self.platform.gen2AddrArr[self.chain_serial]:
            msg = bytearray()
            msg.append(card_addr)
            msg.extend(OppRs232Intf.GET_GEN2_CFG)
            msg.append(0)
            msg.append(0)
            msg.append(0)
            msg.append(0)
            msg.extend(OppRs232Intf.calc_crc8_whole_msg(msg))
            whole_msg.extend(msg)

        whole_msg.extend(OppRs232Intf.EOM_CMD)
        cmd = bytes(whole_msg)
        self.log.debug("Sending get Gen2 Cfg command: %s", "".join(" 0x%02x" % b for b in cmd))
        self.writer.write(cmd)

    def send_vers_cmd(self):
        """Send get firmware version message."""
        whole_msg = bytearray()
        for card_addr in self.platform.gen2AddrArr[self.chain_serial]:
            msg = bytearray()
            msg.append(card_addr)
            msg.extend(OppRs232Intf.GET_GET_VERS_CMD)
            msg.append(0)
            msg.append(0)
            msg.append(0)
            msg.append(0)
            msg.extend(OppRs232Intf.calc_crc8_whole_msg(msg))
            whole_msg.extend(msg)

        whole_msg.extend(OppRs232Intf.EOM_CMD)
        cmd = bytes(whole_msg)
        self.log.debug("Sending get version command: %s", "".join(" 0x%02x" % b for b in cmd))
        self.writer.write(cmd)

    @classmethod
    def _create_vers_str(cls, version_int):
        return ("%02d.%02d.%02d.%02d" % (((version_int >> 24) & 0xff),
                                         ((version_int >> 16) & 0xff), ((version_int >> 8) & 0xff),
                                         (version_int & 0xff)))

    def lost_synch(self):
        """Mark connection as desynchronised."""
        self._lost_synch = True

    def _parse_msg(self, msg):
        self.partMsg += msg
        strlen = len(self.partMsg)
        messaged_found = 0
        # Split into individual responses
        while strlen >= 7:
            if self._lost_synch:
                while strlen > 0:
                    # wait for next gen2 card message
                    if (self.partMsg[0] & 0xe0) == 0x20:
                        self._lost_synch = False
                        break
                    self.partMsg = self.partMsg[1:]
                    strlen -= 1
                # continue because we could have less then 7 bytes in the buffer
                continue

            # Check if this is a gen2 card address
            if (self.partMsg[0] & 0xe0) == 0x20:
                # Only command expect to receive back is
                if self.partMsg[1] == ord(OppRs232Intf.READ_GEN2_INP_CMD):
                    self.platform.process_received_message(self.chain_serial, self.partMsg[:7])
                    messaged_found += 1
                    self.partMsg = self.partMsg[7:]
                    strlen -= 7
                else:
                    # Lost synch
                    self.partMsg = self.partMsg[2:]
                    strlen -= 2
                    self._lost_synch = True

            elif self.partMsg[0] == ord(OppRs232Intf.EOM_CMD):
                self.partMsg = self.partMsg[1:]
                strlen -= 1
            else:
                # Lost synch
                self.partMsg = self.partMsg[1:]
                strlen -= 1
                self._lost_synch = True

        return messaged_found
