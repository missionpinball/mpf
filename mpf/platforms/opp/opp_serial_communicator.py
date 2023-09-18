"""OPP serial communicator."""
import asyncio

from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf

from mpf.platforms.base_serial_communicator import BaseSerialCommunicator, HEX_FORMAT

MYPY = False
if MYPY:    # pragma: no cover
    from mpf.platforms.opp.opp import OppHardwarePlatform   # pylint: disable-msg=cyclic-import,unused-import

# Minimum firmware versions needed for this module
MIN_FW = 0x00000100
BAD_FW_VERSION = 0x01020304


class OPPSerialCommunicator(BaseSerialCommunicator):

    """Manages a Serial connection to the first processor in a OPP serial chain."""

    __slots__ = ["part_msg", "chain_serial", "_lost_synch"]

    # pylint: disable=too-many-arguments
    def __init__(self, platform: "OppHardwarePlatform", port, baud, overwrite_serial) -> None:
        """initialize Serial Connection to OPP Hardware."""
        self.part_msg = b""
        self.chain_serial = overwrite_serial    # type: str
        self._lost_synch = False

        super().__init__(platform, port, baud)
        self.platform = platform    # hint the right type

    async def _read_id(self):
        msg = bytearray([0x20, 0x00, 0x00, 0x00, 0x00, 0x00])
        msg.extend(OppRs232Intf.calc_crc8_whole_msg(msg))
        msg.extend(OppRs232Intf.EOM_CMD)
        self.send(bytes(msg))

        resp = await self.read(8)
        if resp[7] != ord(OppRs232Intf.EOM_CMD):
            raise AssertionError("Failed to read ID from {}. Missing EOM.".format(self.port))

        if ord(OppRs232Intf.calc_crc8_whole_msg(resp[0:6])) != resp[6]:
            raise AssertionError("Failed to read ID from {}. Wrong CRC.".format(self.port))

        if resp[0] != 0x20:
            raise AssertionError("Failed to read ID from {}. Wrong Board ID.".format(self.port))

        if resp[1] != 0:
            raise AssertionError("Failed to read ID from {}. Wrong CMD.".format(self.port))

        return (resp[2] << 24) + (resp[3] << 16) + (resp[4] << 8) + resp[5]

    async def _identify_connection(self):
        """Identify which processor this serial connection is talking to."""
        # keep looping and wait for an ID response
        count = 0
        # read and discard all messages in buffer
        self.send(OppRs232Intf.EOM_CMD)
        await asyncio.sleep(.01)
        await self.read(1000)
        while True:
            if (count % 10) == 0:
                self.log.debug("Sending EOM command to port '%s'",
                               self.port)
            count += 1
            self.send(OppRs232Intf.EOM_CMD)
            await asyncio.sleep(.01)
            resp = await self.read(30)
            if resp.startswith(OppRs232Intf.EOM_CMD):
                break
            if count == 100:
                raise AssertionError('No response from OPP hardware: {}'.format(self.port))

        self.log.debug("Got ID response: %s", "".join(HEX_FORMAT % b for b in resp))
        if self.chain_serial is None:
            # get ID from hardware if it is not overwritten
            self.chain_serial = str(await self._read_id())

        if self.chain_serial in self.platform.opp_connection:
            raise AssertionError("Duplicate chain serial {} on ports: {} and {}. Each OPP board has to have a "
                                 "unique ID. You can overwrite this using the chains "
                                 "setting.".format(self.chain_serial, self.port,
                                                   self.platform.opp_connection[self.chain_serial]))

        # Send inventory command to figure out number of cards
        msg = bytearray()
        msg.extend(OppRs232Intf.INV_CMD)
        msg.extend(OppRs232Intf.EOM_CMD)
        cmd = bytes(msg)

        self.log.debug("Sending inventory command: %s", "".join(HEX_FORMAT % b for b in cmd))
        self.send(cmd)

        resp = await self.readuntil(b'\xff')

        # resp will contain the inventory response.
        self.platform.process_received_message(self.chain_serial, resp)

        # Now send get gen2 configuration message to find populated wing boards
        self.send_get_gen2_cfg_cmd()
        resp = await self.readuntil(b'\xff', 6)

        # resp will contain the gen2 cfg responses.  That will end up creating all the
        # correct objects.
        self.platform.process_received_message(self.chain_serial, resp)

        # get the version of the firmware
        self.send_vers_cmd()
        resp = await self.readuntil(b'\xff', 6)
        self.platform.process_received_message(self.chain_serial, resp)

        # see if version of firmware is new enough
        if self.platform.min_version[self.chain_serial] < MIN_FW:
            raise AssertionError("Firmware version mismatch. MPF requires"
                                 " the OPP Gen2 processor to be firmware {}, but yours is {}".
                                 format(self._create_vers_str(MIN_FW),
                                        self._create_vers_str(self.platform.min_version[self.chain_serial])))

        # get initial value for inputs
        self.log.debug("Getting initial inputs states for %s", self.chain_serial)
        self.send(self.platform.read_input_msg[self.chain_serial])
        cards = len([x for x in self.platform.opp_inputs if x.chain_serial == self.chain_serial])
        while True:
            resp = await self.readuntil(b'\xff')
            cards -= self._parse_msg(resp)
            if cards <= 0:
                break
            self.log.debug("Waiting for another %s cards", cards)

        self.log.info("Init of OPP board %s done", self.chain_serial)
        self.platform.register_processor_connection(self.chain_serial, self)

    def send_get_gen2_cfg_cmd(self):
        """Send get gen2 configuration message to find populated wing boards."""
        whole_msg = bytearray()
        for card_addr in self.platform.gen2_addr_arr[self.chain_serial]:
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
        self.log.debug("Sending get Gen2 Cfg command: %s", "".join(HEX_FORMAT % b for b in cmd))
        self.send(cmd)

    def send_vers_cmd(self):
        """Send get firmware version message."""
        whole_msg = bytearray()
        for card_addr in self.platform.gen2_addr_arr[self.chain_serial]:
            msg = bytearray()
            msg.append(card_addr)
            msg.extend(OppRs232Intf.GET_VERS_CMD)
            msg.append(0)
            msg.append(0)
            msg.append(0)
            msg.append(0)
            msg.extend(OppRs232Intf.calc_crc8_whole_msg(msg))
            whole_msg.extend(msg)

        whole_msg.extend(OppRs232Intf.EOM_CMD)
        cmd = bytes(whole_msg)
        self.log.debug("Sending get version command: %s", "".join(HEX_FORMAT % b for b in cmd))
        self.send(cmd)

    @classmethod
    def _create_vers_str(cls, version_int):     # pragma: no cover
        return ("%02d.%02d.%02d.%02d" % (((version_int >> 24) & 0xff),
                                         ((version_int >> 16) & 0xff), ((version_int >> 8) & 0xff),
                                         (version_int & 0xff)))

    def lost_synch(self):
        """Mark connection as desynchronised."""
        self._lost_synch = True

    def _parse_msg(self, msg):
        self.part_msg += msg
        strlen = len(self.part_msg)
        message_found = 0
        # Split into individual responses
        while strlen > 2:
            if self._lost_synch:
                while strlen > 0:
                    # wait for next gen2 card message
                    if (self.part_msg[0] & 0xe0) == 0x20:
                        self._lost_synch = False
                        break
                    self.part_msg = self.part_msg[1:]
                    strlen -= 1
            # Check if this is a gen2 card address
            elif (self.part_msg[0] & 0xe0) == 0x20:
                # Check if read input
                if self.part_msg[1] == ord(OppRs232Intf.READ_GEN2_INP_CMD):
                    if strlen >= 7:
                        self.platform.process_received_message(self.chain_serial, self.part_msg[:7])
                        message_found += 1
                        self.part_msg = self.part_msg[7:]
                        strlen -= 7
                    else:
                        # message not complete yet
                        break
                # Check if read matrix input
                elif self.part_msg[1] == ord(OppRs232Intf.READ_MATRIX_INP):
                    if strlen >= 11:
                        self.platform.process_received_message(self.chain_serial, self.part_msg[:11])
                        message_found += 1
                        self.part_msg = self.part_msg[11:]
                        strlen -= 11
                    else:
                        # message not complete yet
                        break
                else:
                    # Lost synch
                    self.part_msg = self.part_msg[2:]
                    strlen -= 2
                    self._lost_synch = True

            elif self.part_msg[0] == ord(OppRs232Intf.EOM_CMD):
                self.part_msg = self.part_msg[1:]
                strlen -= 1
            else:
                # Lost synch
                self.part_msg = self.part_msg[1:]
                strlen -= 1
                self._lost_synch = True

        return message_found
