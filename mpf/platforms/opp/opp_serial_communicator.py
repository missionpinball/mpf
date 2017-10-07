"""OPP serial communicator."""
import asyncio

from mpf.platforms.opp.opp_rs232_intf import OppRs232Intf

from mpf.platforms.base_serial_communicator import BaseSerialCommunicator

MYPY = False
if MYPY:    # pragma: no cover
    from mpf.platforms.opp.opp import OppHardwarePlatform

# Minimum firmware versions needed for this module
MIN_FW = 0x00000100
BAD_FW_VERSION = 0x01020304


class OPPSerialCommunicator(BaseSerialCommunicator):

    """Manages a Serial connection to the first processor in a OPP serial chain."""

    # pylint: disable=too-many-arguments
    def __init__(self, platform: "OppHardwarePlatform", port, baud) -> None:
        """Initialise Serial Connection to OPP Hardware."""
        self.partMsg = b""
        self.chain_serial = None    # type: str
        self._lost_synch = False

        super().__init__(platform, port, baud)

    @asyncio.coroutine
    def _identify_connection(self):
        """Identify which processor this serial connection is talking to."""
        # keep looping and wait for an ID response
        count = 0
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

        # resp will contain the gen2 cfg responses.  That will end up creating all the
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
            msg.extend(OppRs232Intf.GET_VERS_CMD)
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
    def _create_vers_str(cls, version_int):     # pragma: no cover
        return ("%02d.%02d.%02d.%02d" % (((version_int >> 24) & 0xff),
                                         ((version_int >> 16) & 0xff), ((version_int >> 8) & 0xff),
                                         (version_int & 0xff)))

    def lost_synch(self):
        """Mark connection as desynchronised."""
        self._lost_synch = True

    def _parse_msg(self, msg):
        self.partMsg += msg
        strlen = len(self.partMsg)
        message_found = 0
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
                # Check if read input
                if self.partMsg[1] == ord(OppRs232Intf.READ_GEN2_INP_CMD):
                    self.platform.process_received_message(self.chain_serial, self.partMsg[:7])
                    message_found += 1
                    self.partMsg = self.partMsg[7:]
                    strlen -= 7
                # Check if read matrix input
                elif self.partMsg[1] == ord(OppRs232Intf.READ_MATRIX_INP):
                    self.platform.process_received_message(self.chain_serial, self.partMsg[:11])
                    message_found += 1
                    self.partMsg = self.partMsg[11:]
                    strlen -= 11
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

        return message_found
