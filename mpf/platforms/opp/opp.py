"""OPP Hardware interface.

Contains the hardware interface and drivers for the Open Pinball Project
platform hardware, including the solenoid, input, incandescent, and neopixel
boards.
"""
import asyncio

from mpf.platforms.interfaces.driver_platform_interface import PulseSettings, HoldSettings

from mpf.platforms.opp.opp_coil import OPPSolenoidCard
from mpf.platforms.opp.opp_incand import OPPIncandCard
from mpf.platforms.opp.opp_neopixel import OPPNeopixelCard
from mpf.platforms.opp.opp_serial_communicator import OPPSerialCommunicator, BAD_FW_VERSION
from mpf.platforms.opp.opp_switch import OPPInputCard
from mpf.platforms.opp.opp_switch import OPPMatrixCard
from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf
from mpf.core.platform import SwitchPlatform, DriverPlatform, LightsPlatform, SwitchSettings, DriverSettings, \
    DriverConfig, SwitchConfig

MYPY = False
if MYPY:   # pragma: no cover
    from typing import Dict, List, Set, Union   # pylint: disable-msg=cyclic-import,unused-import
    from mpf.platforms.opp.opp_coil import OPPSolenoid  # pylint: disable-msg=cyclic-import,unused-import
    from mpf.platforms.opp.opp_incand import OPPIncand  # pylint: disable-msg=cyclic-import,unused-import
    from mpf.platforms.opp.opp_neopixel import OPPNeopixel  # pylint: disable-msg=cyclic-import,unused-import
    from mpf.platforms.opp.opp_switch import OPPSwitch  # pylint: disable-msg=cyclic-import,unused-import


# pylint: disable-msg=too-many-instance-attributes
class OppHardwarePlatform(LightsPlatform, SwitchPlatform, DriverPlatform):

    """Platform class for the OPP hardware.

    Args:
        machine: The main ``MachineController`` instance.

    """

    __slots__ = ["opp_connection", "serial_connections", "opp_incands", "incand_dict", "opp_solenoid", "sol_dict",
                 "opp_inputs", "inp_dict", "inp_addr_dict", "matrix_inp_addr_dict", "read_input_msg", "opp_neopixels",
                 "neo_card_dict", "neo_dict", "num_gen2_brd", "gen2_addr_arr", "bad_crc", "min_version", "_poll_task",
                 "config", "_poll_response_received", "machine_type", "opp_commands", "_incand_task"]

    def __init__(self, machine) -> None:
        """Initialise OPP platform."""
        super().__init__(machine)
        self.opp_connection = {}            # type: Dict[str, OPPSerialCommunicator]
        self.serial_connections = set()     # type: Set[OPPSerialCommunicator]
        self.opp_incands = []               # type: List[OPPIncandCard]
        self.incand_dict = dict()           # type: Dict[str, OPPIncand]
        self.opp_solenoid = []              # type: List[OPPSolenoidCard]
        self.sol_dict = dict()              # type: Dict[str, OPPSolenoid]
        self.opp_inputs = []                # type: List[Union[OPPInputCard, OPPMatrixCard]]
        self.inp_dict = dict()              # type: Dict[str, OPPSwitch]
        self.inp_addr_dict = dict()         # type: Dict[str, OPPInputCard]
        self.matrix_inp_addr_dict = dict()  # type: Dict[str, OPPMatrixCard]
        self.read_input_msg = {}            # type: Dict[str, bytearray]
        self.opp_neopixels = []             # type: List[OPPNeopixelCard]
        self.neo_card_dict = dict()         # type: Dict[str, OPPNeopixelCard]
        self.neo_dict = dict()              # type: Dict[str, OPPNeopixel]
        self.num_gen2_brd = 0
        self.gen2_addr_arr = {}             # type: Dict[str, Dict[int, int]]
        self.bad_crc = 0
        self.min_version = 0xffffffff
        self._poll_task = {}                # type: Dict[str, asyncio.Task]
        self._incand_task = None            # type: asyncio.Task

        self.features['tickless'] = True

        self.config = self.machine.config_validator.validate_config("opp", self.machine.config['opp'])
        self._configure_device_logging_and_debug("OPP", self.config)
        self._poll_response_received = {}   # type: Dict[str, asyncio.Event]

        self.machine_type = (
            self.machine.config['hardware']['driverboards'].lower())

        if self.machine_type == 'gen1':
            raise AssertionError("Original OPP boards not currently supported.")
        if self.machine_type == 'gen2':
            self.log.debug("Configuring the OPP Gen2 boards")
        else:
            self.raise_config_error('Invalid driverboards type: {}'.format(self.machine_type), 15)

        # Only including responses that should be received
        self.opp_commands = {
            ord(OppRs232Intf.INV_CMD): self.inv_resp,
            ord(OppRs232Intf.EOM_CMD): self.eom_resp,
            ord(OppRs232Intf.GET_GEN2_CFG): self.get_gen2_cfg_resp,
            ord(OppRs232Intf.READ_GEN2_INP_CMD): self.read_gen2_inp_resp_initial,
            ord(OppRs232Intf.GET_VERS_CMD): self.vers_resp,
            ord(OppRs232Intf.READ_MATRIX_INP): self.read_matrix_inp_resp_initial,
        }

    async def initialize(self):
        """Initialise connections to OPP hardware."""
        await self._connect_to_hardware()
        self.opp_commands[ord(OppRs232Intf.READ_GEN2_INP_CMD)] = self.read_gen2_inp_resp
        self.opp_commands[ord(OppRs232Intf.READ_MATRIX_INP)] = self.read_matrix_inp_resp

    async def start(self):
        """Start polling and listening for commands."""
        # start polling
        for chain_serial in self.read_input_msg:
            self._poll_task[chain_serial] = self.machine.clock.loop.create_task(self._poll_sender(chain_serial))
            self._poll_task[chain_serial].add_done_callback(self._done)

        # start listening for commands
        for connection in self.serial_connections:
            await connection.start_read_loop()

        self._incand_task = self.machine.clock.schedule_interval(self.update_incand,
                                                                 1 / self.config['incand_update_hz'])

    def stop(self):
        """Stop hardware and close connections."""
        for task in self._poll_task.values():
            task.cancel()

        self._poll_task = {}

        if self._incand_task:
            self._incand_task.cancel()
            self._incand_task = None

        for connections in self.serial_connections:
            connections.stop()

        self.serial_connections = []

    def __repr__(self):
        """Return string representation."""
        return '<Platform.OPP>'

    def process_received_message(self, chain_serial, msg):
        """Send an incoming message from the OPP hardware to the proper method for servicing.

        Args:
            chain_serial: Serial of the chain which received the message.
            msg: Message to parse.
        """
        if len(msg) >= 1:
            # Verify valid Gen2 address
            if (msg[0] & 0xe0) == 0x20:
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
            self.opp_connection[chain_serial].lost_synch()

    @staticmethod
    def _get_numbers(mask):
        number = 0
        ref = 1
        result = []
        while mask > ref:
            if mask & ref:
                result.append(number)
            number += 1
            ref = ref << 1

        return result

    def get_info_string(self):
        """Dump infos about boards."""
        if not self.serial_connections:
            return "No connection to any CPU board."

        infos = "Connected CPUs:\n"
        for connection in self.serial_connections:
            infos += " - Port: {} at {} baud\n".format(connection.port, connection.baud)
            for board_id, board_firmware in self.gen2_addr_arr[connection.chain_serial].items():
                if board_firmware is None:
                    infos += " -> Board: 0x{:02x} Firmware: broken\n".format(board_id)
                else:
                    infos += " -> Board: 0x{:02x} Firmware: 0x{:02x}\n".format(board_id, board_firmware)

        infos += "\nIncand cards:\n"
        for incand in self.opp_incands:
            infos += " - CPU: {} Board: 0x{:02x} Card: {} Numbers: {}\n".format(incand.chain_serial, incand.addr,
                                                                                incand.card_num,
                                                                                self._get_numbers(incand.mask))

        infos += "\nInput cards:\n"
        for inputs in self.opp_inputs:
            infos += " - CPU: {} Board: 0x{:02x} Card: {} Numbers: {}\n".format(inputs.chain_serial, inputs.addr,
                                                                                inputs.card_num,
                                                                                self._get_numbers(inputs.mask))

        infos += "\nSolenoid cards:\n"
        for outputs in self.opp_solenoid:
            infos += " - CPU: {} Board: 0x{:02x} Card: {} Numbers: {}\n".format(outputs.chain_serial, outputs.addr,
                                                                                outputs.card_num,
                                                                                self._get_numbers(outputs.mask))

        infos += "\nLEDs:\n"
        for leds in self.opp_neopixels:
            infos += " - CPU: {} Board: 0x{:02x} Card: {}\n".format(leds.chain_serial, leds.addr, leds.card_num)

        return infos

    async def _connect_to_hardware(self):
        """Connect to each port from the config.

        This process will cause the OPPSerialCommunicator to figure out which chains they've connected to
        and to register themselves.
        """
        for port in self.config['ports']:
            comm = OPPSerialCommunicator(platform=self, port=port, baud=self.config['baud'])
            await comm.connect()
            self.serial_connections.add(comm)

        for chain_serial, versions in self.gen2_addr_arr.items():
            for chain_id, version in versions.items():
                if self.min_version != version:
                    self.raise_config_error("Version mismatch. Board {}-{} has version {:d}.{:d}.{:d}.{:d} which is not"
                                            " the minimal version"
                                            "{:d}.{:d}.{:d}.{:d}".format(chain_serial, chain_id, (version >> 24) & 0xFF,
                                                                         (version >> 16) & 0xFF, (version >> 8) & 0xFF,
                                                                         version & 0xFF,
                                                                         (self.min_version >> 24) & 0xFF,
                                                                         (self.min_version >> 16) & 0xFF,
                                                                         (self.min_version >> 8) & 0xFF,
                                                                         self.min_version & 0xFF), 1)

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

        It is currently assumed that the UART oversampling will guarantee proper
        communication with the boards.  If this does not end up being the case,
        this will be changed to update all the incandescents each loop.
        """
        for incand in self.opp_incands:
            whole_msg = bytearray()
            # Check if any changes have been made
            if (incand.old_state ^ incand.new_state) != 0:
                # Update card
                incand.old_state = incand.new_state
                msg = bytearray()
                msg.append(incand.addr)
                msg.extend(OppRs232Intf.INCAND_CMD)
                msg.extend(OppRs232Intf.INCAND_SET_ON_OFF)
                msg.append((incand.new_state >> 24) & 0xff)
                msg.append((incand.new_state >> 16) & 0xff)
                msg.append((incand.new_state >> 8) & 0xff)
                msg.append(incand.new_state & 0xff)
                msg.extend(OppRs232Intf.calc_crc8_whole_msg(msg))
                whole_msg.extend(msg)

            if whole_msg:
                # Note:  No need to send EOM at end of cmds
                send_cmd = bytes(whole_msg)

                self.send_to_processor(incand.chain_serial, send_cmd)
                self.log.debug("Update incand cmd:%s", "".join(" 0x%02x" % b for b in send_cmd))

    @classmethod
    def get_coil_config_section(cls):
        """Return coil config section."""
        return "opp_coils"

    async def get_hw_switch_states(self):
        """Get initial hardware switch states.

        This changes switches from active low to active high
        """
        hw_states = dict()
        for opp_inp in self.opp_inputs:
            if not opp_inp.is_matrix:
                curr_bit = 1
                for index in range(0, 32):
                    if (curr_bit & opp_inp.mask) != 0:
                        if (curr_bit & opp_inp.old_state) == 0:
                            hw_states[opp_inp.chain_serial + '-' + opp_inp.card_num + '-' + str(index)] = 1
                        else:
                            hw_states[opp_inp.chain_serial + '-' + opp_inp.card_num + '-' + str(index)] = 0
                    curr_bit <<= 1
            else:
                for index in range(0, 64):
                    if ((1 << index) & opp_inp.old_state) == 0:
                        hw_states[opp_inp.chain_serial + '-' + opp_inp.card_num + '-' + str(index + 32)] = 1
                    else:
                        hw_states[opp_inp.chain_serial + '-' + opp_inp.card_num + '-' + str(index + 32)] = 0

        return hw_states

    def inv_resp(self, chain_serial, msg):
        """Parse inventory response.

        Args:
            chain_serial: Serial of the chain which received the message.
            msg: Message to parse.
        """
        self.log.debug("Received Inventory Response: %s for %s", "".join(" 0x%02x" % b for b in msg), chain_serial)

        index = 1
        self.gen2_addr_arr[chain_serial] = {}
        while msg[index] != ord(OppRs232Intf.EOM_CMD):
            if (msg[index] & ord(OppRs232Intf.CARD_ID_TYPE_MASK)) == ord(OppRs232Intf.CARD_ID_GEN2_CARD):
                self.num_gen2_brd += 1
                self.gen2_addr_arr[chain_serial][msg[index]] = None
            else:
                self.log.warning("Invalid inventory response %s for %s.", msg[index], chain_serial)
            index += 1
        self.log.debug("Found %d Gen2 OPP boards on %s.", self.num_gen2_brd, chain_serial)

    @staticmethod
    def eom_resp(chain_serial, msg):
        """Process an EOM.

        Args:
            chain_serial: Serial of the chain which received the message.
            msg: Message to parse.
        """
        # An EOM command can be used to resynchronize communications if message synch is lost

    def _parse_gen2_board(self, chain_serial, msg, read_input_msg):
        has_neo = False
        has_matrix = False
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
            elif msg[2 + wing_index] == ord(OppRs232Intf.WING_SW_MATRIX_OUT):
                has_matrix = True
            elif msg[2 + wing_index] == ord(OppRs232Intf.WING_NEO):
                has_neo = True
            elif msg[2 + wing_index] == ord(OppRs232Intf.WING_HI_SIDE_INCAND):
                incand_mask |= (0xff << (8 * wing_index))
            wing_index += 1
        if incand_mask != 0:
            self.opp_incands.append(OPPIncandCard(chain_serial, msg[0], incand_mask, self.incand_dict, self.machine))
        if sol_mask != 0:
            self.opp_solenoid.append(
                OPPSolenoidCard(chain_serial, msg[0], sol_mask, self.sol_dict, self))
        if inp_mask != 0:
            # Create the input object, and add to the command to read all inputs
            self.opp_inputs.append(OPPInputCard(chain_serial, msg[0], inp_mask, self.inp_dict,
                                                self.inp_addr_dict))

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

        if has_matrix:
            # Create the matrix object, and add to the command to read all matrix inputs
            self.opp_inputs.append(OPPMatrixCard(chain_serial, msg[0], self.inp_dict,
                                                 self.matrix_inp_addr_dict))

            # Add command to read all matrix inputs to read input message
            inp_msg = bytearray()
            inp_msg.append(msg[0])
            inp_msg.extend(OppRs232Intf.READ_MATRIX_INP)
            inp_msg.append(0)
            inp_msg.append(0)
            inp_msg.append(0)
            inp_msg.append(0)
            inp_msg.append(0)
            inp_msg.append(0)
            inp_msg.append(0)
            inp_msg.append(0)
            inp_msg.extend(OppRs232Intf.calc_crc8_whole_msg(inp_msg))
            read_input_msg.extend(inp_msg)
        if has_neo:
            self.opp_neopixels.append(OPPNeopixelCard(chain_serial, msg[0], self.neo_card_dict, self))

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
            # check that message is long enough, must include crc8
            if len(msg) < curr_index + 7:
                self.log.warning("Msg is too short: %s.", "".join(" 0x%02x" % b for b in msg))
                self.opp_connection[chain_serial].lost_synch()
                break
            # Verify the CRC8 is correct
            crc8 = OppRs232Intf.calc_crc8_part_msg(msg, curr_index, 6)
            if msg[curr_index + 6] != ord(crc8):
                self.bad_crc += 1
                self.log.warning("Msg contains bad CRC:%s.", "".join(" 0x%02x" % b for b in msg))
                break
            self._parse_gen2_board(chain_serial, msg[curr_index:curr_index + 6], read_input_msg)

            if (len(msg) > curr_index + 7) and (msg[curr_index + 7] == ord(OppRs232Intf.EOM_CMD)):
                break
            elif (len(msg) > curr_index + 8) and (msg[curr_index + 8] == ord(OppRs232Intf.GET_GEN2_CFG)):
                curr_index += 7
            else:
                self.log.warning("Malformed GET_GEN2_CFG response:%s.",
                                 "".join(" 0x%02x" % b for b in msg))
                self.opp_connection[chain_serial].lost_synch()
                break

        read_input_msg.extend(OppRs232Intf.EOM_CMD)
        self.read_input_msg[chain_serial] = bytes(read_input_msg)
        self._poll_response_received[chain_serial] = asyncio.Event(loop=self.machine.clock.loop)
        self._poll_response_received[chain_serial].set()

    def vers_resp(self, chain_serial, msg):
        """Process version response.

        Args:
            chain_serial: Serial of the chain which received the message.
            msg: Message to parse.
        """
        # Multiple get version responses can be received at once
        self.log.debug("Received Version Response:%s", "".join(" 0x%02x" % b for b in msg))
        curr_index = 0
        while True:
            # check that message is long enough, must include crc8
            if len(msg) < curr_index + 7:
                self.log.warning("Msg is too short: %s.", "".join(" 0x%02x" % b for b in msg))
                self.opp_connection[chain_serial].lost_synch()
                break
            # Verify the CRC8 is correct
            crc8 = OppRs232Intf.calc_crc8_part_msg(msg, curr_index, 6)
            if msg[curr_index + 6] != ord(crc8):
                self.bad_crc += 1
                self.log.warning("Msg contains bad CRC:%s.", "".join(" 0x%02x" % b for b in msg))
                break
            version = (msg[curr_index + 2] << 24) | \
                (msg[curr_index + 3] << 16) | \
                (msg[curr_index + 4] << 8) | \
                msg[curr_index + 5]
            self.log.debug("Firmware version: %d.%d.%d.%d", msg[curr_index + 2],
                           msg[curr_index + 3], msg[curr_index + 4],
                           msg[curr_index + 5])
            if msg[curr_index] not in self.gen2_addr_arr[chain_serial]:
                self.log.warning("Got firmware response for %s but not in inventory at %s", msg[curr_index],
                                 chain_serial)
            else:
                self.gen2_addr_arr[chain_serial][msg[curr_index]] = version

            if version < self.min_version:
                self.min_version = version
            if version == BAD_FW_VERSION:
                raise AssertionError("Original firmware sent only to Brian before adding "
                                     "real version numbers. The firmware must be updated before "
                                     "MPF will work.")
            if (len(msg) > curr_index + 7) and (msg[curr_index + 7] == ord(OppRs232Intf.EOM_CMD)):
                break
            elif (len(msg) > curr_index + 8) and (msg[curr_index + 8] == ord(OppRs232Intf.GET_VERS_CMD)):
                curr_index += 7
            else:
                self.log.warning("Malformed GET_VERS_CMD response:%s.", "".join(" 0x%02x" % b for b in msg))
                self.opp_connection[chain_serial].lost_synch()
                break

    def read_gen2_inp_resp_initial(self, chain_serial, msg):
        """Read initial switch states.

        Args:
            chain_serial: Serial of the chain which received the message.
            msg: Message to parse.
        """
        # Verify the CRC8 is correct
        if len(msg) < 7:
            raise AssertionError("Received too short initial input response: " + "".join(" 0x%02x" % b for b in msg))
        crc8 = OppRs232Intf.calc_crc8_part_msg(msg, 0, 6)
        if msg[6] != ord(crc8):
            self.bad_crc += 1
            self.log.warning("Msg contains bad CRC:%s.", "".join(" 0x%02x" % b for b in msg))
        else:
            if chain_serial + '-' + str(msg[0]) not in self.inp_addr_dict:
                self.log.warning("Got input response for invalid card at initial request: %s. Msg: %s.", msg[0],
                                 "".join(" 0x%02x" % b for b in msg))
                return

            opp_inp = self.inp_addr_dict[chain_serial + '-' + str(msg[0])]
            new_state = (msg[2] << 24) | \
                (msg[3] << 16) | \
                (msg[4] << 8) | \
                msg[5]

            opp_inp.old_state = new_state

    def read_gen2_inp_resp(self, chain_serial, msg):
        """Read switch changes.

        Args:
            chain_serial: Serial of the chain which received the message.
            msg: Message to parse.
        """
        # Single read gen2 input response.  Receive function breaks them down

        # Verify the CRC8 is correct
        if len(msg) < 7:
            self.log.warning("Msg too short: %s.", "".join(" 0x%02x" % b for b in msg))
            self.opp_connection[chain_serial].lost_synch()
            return

        crc8 = OppRs232Intf.calc_crc8_part_msg(msg, 0, 6)
        if msg[6] != ord(crc8):
            self.bad_crc += 1
            self.log.warning("Msg contains bad CRC:%s.", "".join(" 0x%02x" % b for b in msg))
        else:
            if chain_serial + '-' + str(msg[0]) not in self.inp_addr_dict:
                self.log.warning("Got input response for invalid card: %s. Msg: %s.", msg[0],
                                 "".join(" 0x%02x" % b for b in msg))
                return

            opp_inp = self.inp_addr_dict[chain_serial + '-' + str(msg[0])]
            new_state = (msg[2] << 24) | \
                (msg[3] << 16) | \
                (msg[4] << 8) | \
                msg[5]

            # Update the state which holds inputs that are active
            changes = opp_inp.old_state ^ new_state
            if changes != 0:
                curr_bit = 1
                for index in range(0, 32):
                    if (curr_bit & changes) != 0:
                        if (curr_bit & new_state) == 0:
                            self.machine.switch_controller.process_switch_by_num(
                                state=1,
                                num=opp_inp.chain_serial + '-' + opp_inp.card_num + '-' + str(index),
                                platform=self)
                        else:
                            self.machine.switch_controller.process_switch_by_num(
                                state=0,
                                num=opp_inp.chain_serial + '-' + opp_inp.card_num + '-' + str(index),
                                platform=self)
                    curr_bit <<= 1
            opp_inp.old_state = new_state

        # we can continue to poll
        self._poll_response_received[chain_serial].set()

    def read_matrix_inp_resp_initial(self, chain_serial, msg):
        """Read initial matrix switch states.

        Args:
            chain_serial: Serial of the chain which received the message.
            msg: Message to parse.
        """
        # Verify the CRC8 is correct
        if len(msg) < 11:
            raise AssertionError("Received too short initial input response: " + "".join(" 0x%02x" % b for b in msg))
        crc8 = OppRs232Intf.calc_crc8_part_msg(msg, 0, 10)
        if msg[10] != ord(crc8):
            self.bad_crc += 1
            self.log.warning("Msg contains bad CRC:%s.", "".join(" 0x%02x" % b for b in msg))
        else:
            if chain_serial + '-' + str(msg[0]) not in self.matrix_inp_addr_dict:
                self.log.warning("Got input response for invalid matrix card at initial request: %s. Msg: %s.", msg[0],
                                 "".join(" 0x%02x" % b for b in msg))
                return
            opp_inp = self.matrix_inp_addr_dict[chain_serial + '-' + str(msg[0])]
            opp_inp.old_state = ((msg[2] << 56) | (msg[3] << 48) | (msg[4] << 40) | (msg[5] << 32) |
                                 (msg[6] << 24) | (msg[7] << 16) | (msg[8] << 8) | msg[9])

    # pylint: disable-msg=too-many-nested-blocks
    def read_matrix_inp_resp(self, chain_serial, msg):
        """Read matrix switch changes.

        Args:
            chain_serial: Serial of the chain which received the message.
            msg: Message to parse.
        """
        # Single read gen2 input response.  Receive function breaks them down

        # Verify the CRC8 is correct
        if len(msg) < 11:
            self.log.warning("Msg too short: %s.", "".join(" 0x%02x" % b for b in msg))
            self.opp_connection[chain_serial].lost_synch()
            return

        crc8 = OppRs232Intf.calc_crc8_part_msg(msg, 0, 10)
        if msg[10] != ord(crc8):
            self.bad_crc += 1
            self.log.warning("Msg contains bad CRC:%s.", "".join(" 0x%02x" % b for b in msg))
        else:
            if chain_serial + '-' + str(msg[0]) not in self.matrix_inp_addr_dict:
                self.log.warning("Got input response for invalid matrix card: %s. Msg: %s.", msg[0],
                                 "".join(" 0x%02x" % b for b in msg))
                return
            opp_inp = self.matrix_inp_addr_dict[chain_serial + '-' + str(msg[0])]
            new_state = ((msg[2] << 56) | (msg[3] << 48) | (msg[4] << 40) | (msg[5] << 32) |
                         (msg[6] << 24) | (msg[7] << 16) | (msg[8] << 8) | msg[9])

            changes = opp_inp.old_state ^ new_state
            if changes != 0:
                curr_bit = 1
                for index in range(32, 96):
                    if (curr_bit & changes) != 0:
                        if (curr_bit & new_state) == 0:
                            self.machine.switch_controller.process_switch_by_num(
                                state=1,
                                num=opp_inp.chain_serial + '-' + opp_inp.card_num + '-' + str(index),
                                platform=self)
                        else:
                            self.machine.switch_controller.process_switch_by_num(
                                state=0,
                                num=opp_inp.chain_serial + '-' + opp_inp.card_num + '-' + str(index),
                                platform=self)
                    curr_bit <<= 1
            opp_inp.old_state = new_state

        # we can continue to poll
        self._poll_response_received[chain_serial].set()

    def _get_dict_index(self, input_str):
        if not isinstance(input_str, str):
            self.raise_config_error("Invalid number format for OPP. Number should be card-number or chain-card-number "
                                    "(e.g. 0-1)", 2)

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
                self.raise_config_error("Chain {} is unconfigured".format(chain_str), 3)
            else:
                # when there is only one port, use only available chain
                chain_serial = list(self.serial_connections)[0].chain_serial
        else:
            chain_serial = self.config['chains'][chain_str]

        return chain_serial + "-" + card_str + "-" + number_str

    def configure_driver(self, config: DriverConfig, number: str, platform_settings: dict):
        """Configure a driver.

        Args:
            config: Config dict.
        """
        if not self.opp_connection:
            self.raise_config_error("A request was made to configure an OPP solenoid, "
                                    "but no OPP connection is available", 4)

        number = self._get_dict_index(number)

        if number not in self.sol_dict:
            self.raise_config_error("A request was made to configure an OPP solenoid "
                                    "with number {} which doesn't exist".format(number), 5)

        # Use new update individual solenoid command
        opp_sol = self.sol_dict[number]
        opp_sol.config = config
        opp_sol.platform_settings = platform_settings
        self.log.debug("Configure driver %s", number)
        default_pulse = PulseSettings(config.default_pulse_power, config.default_pulse_ms)
        default_hold = HoldSettings(config.default_hold_power)
        opp_sol.reconfigure_driver(default_pulse, default_hold)

        # Removing the default input is not necessary since the
        # CFG_SOL_USE_SWITCH is not being set

        return opp_sol

    def configure_switch(self, number: str, config: SwitchConfig, platform_config: dict):
        """Configure a switch.

        Args:
            config: Config dict.
        """
        del platform_config
        del config
        # A switch is termed as an input to OPP
        if not self.opp_connection:
            self.raise_config_error("A request was made to configure an OPP switch, "
                                    "but no OPP connection is available", 6)

        number = self._get_dict_index(number)

        if number not in self.inp_dict:
            self.raise_config_error("A request was made to configure an OPP switch "
                                    "with number {} which doesn't exist".format(number), 7)

        return self.inp_dict[number]

    def parse_light_number_to_channels(self, number: str, subtype: str):
        """Parse number and subtype to channel."""
        if subtype == "matrix":
            return [
                {
                    "number": self._get_dict_index(number)
                }
            ]
        if not subtype or subtype == "led":
            return [
                {
                    "number": self._get_dict_index(number) + "-0"
                },
                {
                    "number": self._get_dict_index(number) + "-1"
                },
                {
                    "number": self._get_dict_index(number) + "-2"
                },
            ]

        self.raise_config_error("Unknown subtype {}".format(subtype), 8)
        return []

    def configure_light(self, number, subtype, platform_settings):
        """Configure a led or matrix light."""
        if not self.opp_connection:
            self.raise_config_error("A request was made to configure an OPP light, "
                                    "but no OPP connection is available", 9)
        if not subtype or subtype == "led":
            chain_serial, card, pixel_num, index_str = number.split('-')
            index = chain_serial + '-' + card
            if index not in self.neo_card_dict:
                self.raise_config_error("A request was made to configure an OPP neopixel "
                                        "with card number {} which doesn't exist".format(card), 10)

            neo = self.neo_card_dict[index]
            channel = neo.add_channel(int(pixel_num), self.neo_dict, index_str)
            return channel
        if subtype == "matrix":
            if number not in self.incand_dict:
                self.raise_config_error("A request was made to configure a OPP matrix "
                                        "light (incand board), with number {} "
                                        "which doesn't exist".format(number), 11)

            return self.incand_dict[number]

        self.raise_config_error("Unknown subtype {}".format(subtype), 12)
        return None

    def light_sync(self):
        """Update lights.

        Currently we only update neo pixels. Incands are updated separately in a task to provide better batching.
        """
        for light in self.neo_dict.values():
            if light.dirty:
                light.update_color()

    @staticmethod
    def _done(future):  # pragma: no cover
        """Evaluate result of task.

        Will raise exceptions from within task.
        """
        future.result()

    async def _poll_sender(self, chain_serial):
        """Poll switches."""
        while True:
            # wait for previous poll response
            timeout = 1 / self.config['poll_hz'] * 25
            try:
                await asyncio.wait_for(self._poll_response_received[chain_serial].wait(), timeout,
                                       loop=self.machine.clock.loop)
            except asyncio.TimeoutError:
                self.log.warning("Poll took more than %sms for %s", timeout * 1000, chain_serial)
            else:
                self._poll_response_received[chain_serial].clear()
            # send poll
            self.send_to_processor(chain_serial, self.read_input_msg[chain_serial])
            await self.opp_connection[chain_serial].writer.drain()
            # the line above saturates the link and seems to overwhelm the hardware. limit it to 100Hz
            await asyncio.sleep(1 / self.config['poll_hz'], loop=self.machine.clock.loop)

    def _verify_coil_and_switch_fit(self, switch, coil):
        chain_serial, card, solenoid = coil.hw_driver.number.split('-')
        sw_chain_serial, sw_card, sw_num = switch.hw_switch.number.split('-')
        if self.min_version >= 0x00020000:
            if chain_serial != sw_chain_serial or card != sw_card:
                self.raise_config_error('Invalid switch being configured for driver. Driver = {} '
                                        'Switch = {}. Driver and switch have to be on the same '
                                        'board.'.format(coil.hw_driver.number, switch.hw_switch.number), 13)
        else:
            matching_sw = ((int(solenoid) & 0x0c) << 1) | (int(solenoid) & 0x03)
            if chain_serial != sw_chain_serial or card != sw_card or matching_sw != int(sw_num):
                self.raise_config_error('Invalid switch being configured for driver. Driver = {} '
                                        'Switch = {}. For Firmware < 0.2.0 they have to be on the same board and '
                                        'have the same number'.format(coil.hw_driver.number, switch.hw_switch.number),
                                        14)

    def set_pulse_on_hit_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit rule on driver.

        Pulses a driver when a switch is hit. When the switch is released the pulse continues. Typically used for
        autofire coils such as pop bumpers.
        """
        self._write_hw_rule(enable_switch, coil, use_hold=False, can_cancel=False)

    def set_pulse_on_hit_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and release rule to driver.

        Pulses a driver when a switch is hit. When the switch is released the pulse is canceled. Typically used on
        the main coil for dual coil flippers without eos switch.
        """
        self._write_hw_rule(enable_switch, coil, use_hold=False, can_cancel=True)

    def set_pulse_on_hit_and_enable_and_release_rule(self, enable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and enable and relase rule on driver.

        Pulses a driver when a switch is hit. Then enables the driver (may be with pwm). When the switch is released
        the pulse is canceled and the driver gets disabled. Typically used for single coil flippers.
        """
        self._write_hw_rule(enable_switch, coil, use_hold=True, can_cancel=True)

    def set_pulse_on_hit_and_enable_and_release_and_disable_rule(self, enable_switch: SwitchSettings,
                                                                 disable_switch: SwitchSettings, coil: DriverSettings):
        """Set pulse on hit and enable and release and disable rule on driver.

        Pulses a driver when a switch is hit. Then enables the driver (may be with pwm). When the switch is released
        the pulse is canceled and the driver gets disabled. When the second disable_switch is hit the pulse is canceled
        and the driver gets disabled. Typically used on the main coil for dual coil flippers with eos switch.
        """
        raise AssertionError("Not implemented in OPP currently")

    def _write_hw_rule(self, switch_obj: SwitchSettings, driver_obj: DriverSettings, use_hold, can_cancel=False):
        if switch_obj.invert:
            raise AssertionError("Cannot handle inverted switches")

        if driver_obj.hold_settings and not use_hold:
            raise AssertionError("Invalid call")

        self._verify_coil_and_switch_fit(switch_obj, driver_obj)

        self.log.debug("Setting HW Rule. Driver: %s", driver_obj.hw_driver.number)

        driver_obj.hw_driver.switches.append(switch_obj.hw_switch.number)
        driver_obj.hw_driver.set_switch_rule(driver_obj.pulse_settings, driver_obj.hold_settings, driver_obj.recycle,
                                             can_cancel)
        _, _, switch_num = switch_obj.hw_switch.number.split("-")
        switch_num = int(switch_num)
        self._add_switch_coil_mapping(switch_num, driver_obj.hw_driver)

    def _remove_switch_coil_mapping(self, switch_num, driver: "OPPSolenoid"):
        """Remove mapping between switch and coil."""
        if self.min_version < 0x00020000:
            return

        _, _, coil_num = driver.number.split('-')
        msg = bytearray()
        msg.append(driver.sol_card.addr)
        msg.extend(OppRs232Intf.SET_SOL_INP_CMD)
        msg.append(int(switch_num))
        msg.append(int(coil_num) + ord(OppRs232Intf.CFG_SOL_INP_REMOVE))
        msg.extend(OppRs232Intf.calc_crc8_whole_msg(msg))
        msg.extend(OppRs232Intf.EOM_CMD)
        final_cmd = bytes(msg)

        self.log.debug("Unmapping input %s and coil %s", switch_num, coil_num)
        self.send_to_processor(driver.sol_card.chain_serial, final_cmd)

    def _add_switch_coil_mapping(self, switch_num, driver: "OPPSolenoid"):
        """Add mapping between switch and coil."""
        if self.min_version < 0x00020000:
            return
        _, _, coil_num = driver.number.split('-')
        msg = bytearray()
        msg.append(driver.sol_card.addr)
        msg.extend(OppRs232Intf.SET_SOL_INP_CMD)
        msg.append(int(switch_num))
        msg.append(int(coil_num))
        msg.extend(OppRs232Intf.calc_crc8_whole_msg(msg))
        msg.extend(OppRs232Intf.EOM_CMD)
        final_cmd = bytes(msg)

        self.log.debug("Mapping input %s and coil %s", switch_num, coil_num)
        self.send_to_processor(driver.sol_card.chain_serial, final_cmd)

    def clear_hw_rule(self, switch: SwitchSettings, coil: DriverSettings):
        """Clear a hardware rule.

        This is used if you want to remove the linkage between a switch and
        some driver activity. For example, if you wanted to disable your
        flippers (so that a player pushing the flipper buttons wouldn't cause
        the flippers to flip), you'd call this method with your flipper button
        as the *sw_num*.

        """
        if switch.hw_switch.number in coil.hw_driver.switches:
            self.log.debug("Clearing HW Rule for switch: %s, coils: %s", switch.hw_switch.number,
                           coil.hw_driver.number)
            coil.hw_driver.switches.remove(switch.hw_switch.number)
            _, _, switch_num = switch.hw_switch.number.split("-")
            switch_num = int(switch_num)
            self._remove_switch_coil_mapping(switch_num, coil.hw_driver)

        # disable rule if there are no more switches
        # Technically not necessary unless the solenoid parameters are
        # changing.  MPF may not know when initial kick and hold values
        # are changed, so this might need to be called each time.
        if not coil.hw_driver.switches:
            coil.hw_driver.remove_switch_rule()
