"""Boards and wiring strategy for FAST Pinball."""
from typing import List, Dict, Optional, TypeVar, Any, Callable, Tuple
from mpf.core.machine import MachineController
from mpf.wire.base import Board, Pin, System, PinSpecs, SerialLED, Switch, Coil


class FastPFB(Board):

    """The FAST Power Filter Board."""

    def __init__(self):
        """Set up a power filter board."""
        super().__init__("PFB")
        self.add_connector("J1", [    # Coin door switch
            ("SW", 5),
            ("KEY", -1),
            ("GND", 0)
        ])
        self.add_connector("J2", [    # Coil power enable
            ("+", 5),
            ("-", 0),
            ("KEY", -1)
        ])
        self.add_connector("J3", [    # PSU In
            ("HV+", 48),
            ("HV+", 48),
            ("GND", 0),
            ("GND", 0),
            ("5v", 5),
            ("5v", 5),
            ("12v", 12),
            ("KEY", -1),
            ("GND", 0),
            ("GND", 0),
            ("V1", -2),
            ("V2", -2)
        ])
        self.add_connector("J4", [    # Power Out
            ("HV+", 48),
            ("HV+", 48),
            ("GND", 0),
            ("GND", 0),
            ("5v", 5),
            ("5v", 5),
            ("KEY", -1),
            ("12v", 12),
            ("GND", 0),
            ("GND", 0),
            ("V1", -2),
            ("V2", -2)
        ])


class FastNetBoard(Board):

    """A generic class for boards with FAST networking connectors."""

    @staticmethod
    def fast_net_connector() -> PinSpecs:
        """Return the pin spec to use for a FAST network connector."""
        return [("RJ45", 1)]

    def get_net_in(self) -> Pin:
        """Return this board's network in 'pin' (actually a whole connector with irrelevant pinout)."""

    def get_net_out(self) -> Pin:
        """Return this board's network out 'pin''."""


class FastIOBoard(FastNetBoard):

    """Generic class for FAST IO boards."""

    @staticmethod
    # pylint: disable=too-many-arguments
    def fast_connector_block(prefix: str, size: int, vclass: int, offset: int, key_loc: int, first_ground: int) \
            -> PinSpecs:
        """Return the pinspec for a FAST IO connector.

        :param prefix The name to place before the name of each pin.
        :param size The number of pins on the connector.
        :param vclass The voltage class of pins on the connector.
        :param offset The number of the first switch/driver on the connector.
        :param key_loc The index of the key pin.
        :param first_ground The index of the first ground pin.
        """
        pins = []
        non_key_pins = 0
        for pin in range(size):
            if pin == key_loc:
                pins.append(("KEY", -1))
            elif pin >= first_ground:
                pins.append(("GND", 0))
            else:
                pins.append((prefix + (str(non_key_pins + offset)), vclass))
                non_key_pins += 1
        return pins

    def get_switch_pin(self, switch_id) -> Pin:
        """Return the pin for the numbered switch."""

    def get_driver_pin(self, driver_id) -> Pin:
        """Return the pin for the numbered driver."""

    def get_switch_grounds(self, index) -> List[Pin]:
        """Return a list of all index'th switch ground pins."""

    def get_driver_grounds(self, index) -> List[Pin]:
        """Return a list of all index'th driver ground pins."""


class FastIO3208(FastIOBoard):

    """A Fast IO 3028 board with 32 switches and 8 drivers."""

    def __init__(self):
        """Initialize the board."""
        super().__init__("IO 3208")
        self.add_connector("J1", self.fast_net_connector())
        self.add_connector("J2", self.fast_net_connector())
        self.add_connector("J3", self.fast_connector_block("Sw", 11, 5, 8, 3, 9))
        self.add_connector("J4", self.fast_connector_block("Dr", 12, 48, 0, 5, 9))
        self.add_connector("J6", self.fast_connector_block("Sw", 11, 5, 16, 2, 9))
        self.add_connector("J8", self.fast_connector_block("Sw", 11, 5, 0, 4, 9))
        self.add_connector("J9", self.fast_connector_block("Sw", 11, 5, 24, 1, 9))

    def get_net_out(self) -> Pin:
        """Return the network out port, J1."""
        return self["J1"][0]

    def get_net_in(self) -> Pin:
        """Return the network out port, J0."""
        return self["J2"][0]

    # pylint: disable=too-many-return-statements
    def get_switch_pin(self, switch_id) -> Pin:
        """Return the pin for the numbered switch."""
        if switch_id < 4:
            return self["J8"][switch_id]
        if switch_id < 8:
            return self["J8"][switch_id + 1]
        if switch_id < 11:
            return self["J3"][switch_id - 8]
        if switch_id < 16:
            return self["J3"][switch_id - 7]
        if switch_id < 18:
            return self["J6"][switch_id - 16]
        if switch_id < 24:
            return self["J6"][switch_id - 15]
        if switch_id == 24:
            return self["J9"][0]
        if switch_id < 32:
            return self["J9"][switch_id - 23]
        return None

    def get_driver_pin(self, driver_id) -> Pin:
        """Return the pin for the numbered driver."""
        if driver_id < 5:
            return self["J4"][driver_id]
        if driver_id < 8:
            return self["J4"][driver_id + 1]
        return None

    def get_switch_grounds(self, index: int) -> List[Pin]:
        """Get the index'th switch ground pin from each of 4 connectors."""
        return [self["J3"][9 + index],
                self["J6"][9 + index],
                self["J8"][9 + index],
                self["J9"][9 + index]]

    def get_driver_grounds(self, index: int) -> List[Pin]:
        """Get the index'th driver ground pin for the connector."""
        return [self["J4"][9 + index]]


class FastIO1616(FastIOBoard):

    """A FAST IO 1616 board with 16 switches and 16 drivers."""

    def __init__(self):
        """Initialize the board."""
        super().__init__("IO 1616")
        self.add_connector("J1", self.fast_net_connector())
        self.add_connector("J2", self.fast_net_connector())
        self.add_connector("J3", self.fast_connector_block("Dr", 12, 48, 0, 4, 9))
        self.add_connector("J4", self.fast_connector_block("Dr", 12, 48, 8, 5, 9))
        self.add_connector("J7", self.fast_connector_block("Sw", 11, 5, 0, 4, 9))
        self.add_connector("J8", self.fast_connector_block("Sw", 11, 5, 8, 3, 9))

    def get_net_out(self):
        """Get the network output port, J1."""
        return self["J1"][0]

    def get_net_in(self):
        """Get the network input port, J2."""
        return self["J2"][0]

    def get_switch_grounds(self, index):
        """Get the index'th switch grounds for the two switch connectors."""
        return [self["J7"][9 + index],
                self["J8"][9 + index]]

    def get_driver_grounds(self, index):
        """Get the index'th driver grounds for the two driver connectors."""
        return [self["J3"][9 + index],
                self["J4"][9 + index]]

    def get_switch_pin(self, switch_id):
        """Return the pin for the numbered switch."""
        if switch_id < 4:
            return self["J7"][switch_id]
        if switch_id < 8:
            return self["J7"][switch_id + 1]
        if switch_id < 11:
            return self["J8"][switch_id - 8]
        if switch_id < 16:
            return self["J8"][switch_id - 7]
        return None

    def get_driver_pin(self, driver_id):
        """Return the pin for the numbered driver."""
        if driver_id < 4:
            return self["J3"][driver_id]
        if driver_id < 8:
            return self["J3"][driver_id + 1]
        if driver_id < 13:
            return self["J4"][driver_id - 8]
        if driver_id < 16:
            return self["J4"][driver_id - 7]
        return None


class FastIO0804(FastIOBoard):

    """The FAST IO 0804 board with 8 switches and 4 drivers."""

    def __init__(self):
        """Initialize the board."""
        super().__init__("IO 0807")
        self.add_connector("J1", self.fast_net_connector())
        self.add_connector("J2", self.fast_net_connector())
        self.add_connector("J3", self.fast_connector_block("Dr", 7, 48, 0, 4, 5))
        self.add_connector("J4", self.fast_connector_block("SW", 11, 5, 0, 4, 9))

    def get_net_out(self):
        """Get the network output port, J1."""
        return self["J1"][0]

    def get_net_in(self):
        """Get the network input port, J2."""
        return self["J2"][0]

    def get_switch_pin(self, switch_id):
        """Return the pin for the numbered switch."""
        if switch_id < 4:
            return self["J4"][switch_id]
        if switch_id < 8:
            return self["J4"][switch_id + 1]
        return None

    def get_driver_pin(self, driver_id):
        """Return the pin for the numbered driver."""
        assert driver_id <= 4
        return self["J3"][driver_id]

    def get_switch_grounds(self, index):
        """Return the index'th switch ground pin for the single connector."""
        return [self["J4"][9 + index]]

    def get_driver_grounds(self, index):
        """Return the index'th driver ground pin for the single connector."""
        return [self["J3"][5 + index]]


class FastNC(FastNetBoard):

    """A FAST NANO Controller board."""

    def __init__(self):
        """Initialize the connectors on the NC."""
        super().__init__("NC")
        led_connector: PinSpecs = [("GND", 0), ("DO", 5), ("5v", 5)]
        self.add_connector("J1", led_connector)
        self.add_connector("J2", led_connector)
        self.add_connector("J4", led_connector)
        self.add_connector("J5", led_connector)
        self.add_connector("J7", [
            ("12v", 12),
            ("12v", 12),
            ("5v", 5),
            ("5v", 5),
            ("GND", 0),
            ("KEY", -1),
            ("GND", 0)
        ])
        self.add_connector("J10", self.fast_net_connector())
        self.add_connector("J11", self.fast_net_connector())

    def get_net_out(self):
        """Get the network output port, J10."""
        return self["J10"][0]

    def get_net_in(self):
        """Get the network input port, J11."""
        return self["J11"][0]


class FastSystem(System):

    """A complete FAST pinball based wiring system."""

    def __init__(self):
        """Initialize the system with basic contents."""
        super().__init__()
        # We at least will need a power board and nano controller
        self.pfb = FastPFB()
        self.nc = FastNC()
        self.add_board(self.pfb)
        self.add_board(self.nc)
        # Wire nano controller to power and ground on PFB
        self.connect(self.pfb["J4"][4], self.nc["J7"][2])
        self.connect(self.pfb["J4"][5], self.nc["J7"][3])
        self.connect(self.pfb["J4"][7], self.nc["J7"][0])
        self.connect(self.pfb["J4"][8], self.nc["J7"][4])
        self.connect(self.pfb["J4"][9], self.nc["J7"][6])


def light_numspec_to_ordinal(spec: str) -> int:
    """Turn a lighting specification into a light number.

    The MPF documentation says that FAST lights should be given by serial number only, but at least one
    example uses channel-index notation like for switches, and it seems to be accepted by the rest of MPF,
    so this allows for it.
    """
    if "-" in spec:
        parts = spec.split("-")
        return (int(parts[0]) * 64) + (int(parts[1]))
    return int(spec)


def wire_lights(machine: MachineController, s: FastSystem):
    """Wire lights for given machine definition into FAST system."""
    # Create a SerialLED board for each light on the system.
    led_boards: Dict[int, SerialLED] = dict()
    for light in machine.lights.values():
        new_board = SerialLED(light.name)
        real_num = light_numspec_to_ordinal(light.config["number"])
        if 0 <= real_num <= 255:
            led_boards[real_num] = new_board
            s.add_board(new_board)

    # List of bounds and names of FAST NC LED channels
    channels = [(0, 63, "J1"),
                (64, 127, "J2"),
                (128, 191, "J4"),
                (192, 255, "J5")]

    # Create a daisy chain for each light channel and connect it to the appropriate NC port.
    # TODO: These can be BIG - so big that dot can't render them in any format except SVG. Unfortunately
    #       wireviz will always try to render in all formats, giving an error. Laddering doesn't always help.
    for (start, end, ncport) in channels:
        channel_dict = {x: y for (x, y) in led_boards.items() if start <= x <= end}
        if len(channel_dict) > 0:
            # Using just one variable here will result in power wires not being connected at all if there is a
            # sequence gap, due to short circuit evaluation.
            ok1 = s.daisy_chain_dict(channel_dict, lambda x: x[""][0], lambda x: x[""][1], start, False)
            ok2 = s.daisy_chain_dict(channel_dict, lambda x: x[""][4], lambda x: x[""][4], start, False)
            ok3 = s.daisy_chain_dict(channel_dict, lambda x: x[""][5], lambda x: x[""][5], start, False)
            if not ok1 or not ok2 or not ok3:
                print("Lights numbers on channel", start, "-", end,
                      "aren't consecutive. Stopped at the first missing light.")
            s.connect(s.nc[ncport][1], channel_dict[start][""][1])
            s.connect(s.nc[ncport][2], channel_dict[start][""][4])
            s.connect(s.nc[ncport][0], channel_dict[start][""][5])


# pylint: disable=invalid-name
T = TypeVar("T")


def add_devices_with_board_numbers(devices: Dict[Any, T], s: FastSystem, construct: Callable[[T], Board])\
        -> Tuple[Dict[int, Dict[int, Board]], int]:
    """Build actual boards and board connection indices for all devices on a machine.

    Given a dict of devices from machine with config entries that specify board numbers, add boards for all
    the devices to the system and also build a dict associating each its board and port.
    :param devices The dict of devices. Only values are accessed.
    :param s The system to update.
    :param construct A function to build a Board from the dict values.
    :return A dictionary mapping boards numbers and devices to generated Boards, and the highest number board.
    """
    max_board: int = 0
    device_dict: Dict[int, Dict[int, Board]] = dict()
    for d in devices:
        sw = construct(d.name)
        s.add_board(sw)
        num_spec = d.config["number"]
        parts = num_spec.split("-")
        board_no = int(parts[0])
        if board_no > max_board:
            max_board = board_no
        device_no = int(parts[1])
        if board_no not in device_dict.keys():
            device_dict[board_no] = dict()
        device_dict[board_no][device_no] = sw
    return (device_dict, max_board)


def identify_fast_board(switches: int, drivers: int) -> Optional[FastIOBoard]:
    """Instantiate and return a FAST board capable of accommodating the given number of switches and drivers."""
    if switches > 32 or drivers > 16:
        return None
    if switches > 16:
        return None if drivers > 8 else FastIO3208()
    if drivers <= 4:
        return FastIO0804()
    if switches <= 8:
        return FastIO1616()
    return None


# pylint: disable=too-many-locals
def wire_specified_boards(machine: MachineController, s: FastSystem):
    """Wires a FAST system with specified board numbers."""
    # Used if switches and drivers specify board numbers.

    # Sort switches and drivers by board
    (fast_boards_switches, max_switch_board) = add_devices_with_board_numbers(machine.switches, s, Switch)
    (fast_boards_drivers, max_driver_board) = add_devices_with_board_numbers(machine.coils, s, Coil)

    # Check for board consistency
    max_board = max(max_switch_board, max_driver_board)
    for x in range(max_board + 1):
        if x not in fast_boards_switches and x not in fast_boards_drivers:
            print("I/O board numbers aren't consecutive. An empty board number", x, "would be needed!")
            return

    fast_boards: Dict[int, FastIOBoard] = dict()

    # Work out type of each board and add
    for board in range(max_board + 1):
        switches_on_board = len(fast_boards_switches[board])
        drivers_on_board = len(fast_boards_drivers[board])

        print("Board", board, "has", switches_on_board, "switches and", drivers_on_board, "drivers.")
        board_to_add = identify_fast_board(switches_on_board, drivers_on_board)
        if board_to_add is None:
            print(board, " has a combination of switches and drivers that no FAST IO board supports.")
            return
        s.add_board(board_to_add)
        fast_boards[board] = board_to_add

    # Build loop network
    s.daisy_chain_dict(fast_boards, lambda b: b.get_net_in(), lambda b: b.get_net_out(), 0, False)
    s.connect(s.nc.get_net_out(), fast_boards[0].get_net_in())
    s.connect(fast_boards[max_board].get_net_out(), s.nc.get_net_in())

    # Ground IO board logic connectors
    logic_grounds = [fast_boards[board].get_switch_grounds(0) for board in range(max_board + 1)]
    most_logic_slots = max([len(x) for x in logic_grounds])
    for slot in range(most_logic_slots):
        xth_slot_pins = ([g[slot] for g in logic_grounds if len(g) > slot])
        s.daisy_chain_list(xth_slot_pins, lambda p: p, lambda p: p)
        s.connect(s.pfb["J4"][8 + (slot % 2)], xth_slot_pins[0])

    # Ground HV connectors
    hv_grounds = [fast_boards[board].get_driver_grounds(0) for board in range(max_board + 1)]
    most_driver_slots = max([len(x) for x in hv_grounds])
    for slot in range(most_driver_slots):
        xth_slot_pins = ([g[slot] for g in hv_grounds if len(g) > slot])
        s.daisy_chain_list(xth_slot_pins, lambda p: p, lambda p: p)
        s.connect(s.pfb["J4"][2 + (slot % 2)], xth_slot_pins[0])

    # Wire up switches and drivers to board
    for board in range(max_board + 1):
        if board in fast_boards_switches.keys():
            for (pin, switch) in fast_boards_switches[board].items():
                s.connect(fast_boards[board].get_switch_pin(pin), switch[""][1])

        if board in fast_boards_drivers.keys():
            for (pin, driver) in fast_boards_drivers[board].items():
                s.connect(fast_boards[board].get_driver_pin(pin), driver[""][1])

    # Daisy chain switch and driver power
    for board in range(max_board + 1):
        if board in fast_boards_switches.keys():
            switches_on_board = list(fast_boards_switches[board].values())
            s.daisy_chain_list(switches_on_board, lambda w: w[""][0], lambda w: w[""][0])
            s.connect(s.pfb["J4"][4 + (board % 2)], switches_on_board[0][""][0])

        if board in fast_boards_drivers.keys():
            drivers_on_board = list(fast_boards_drivers[board].values())
            s.daisy_chain_list(drivers_on_board, lambda d: d[""][0], lambda d: d[""][0])
            s.connect(s.pfb["J4"][0 + (board % 2)], drivers_on_board[0][""][0])


def wire(machine: MachineController):
    """Wire a given machine using FAST Pinball boards."""
    s = FastSystem()
    wire_lights(machine, s)
    inconsistent_err = "Can't wire: all switch and driver numbers must be in the same format, (board-index) or " +\
                       "raw number, not a mixture of both."

    switches_specify_boards = None
    for switch in machine.switches.values():
        num_spec = switch.config["number"]
        if switches_specify_boards is None:
            switches_specify_boards = ("-" in num_spec)
        else:
            if ("-" in num_spec) != switches_specify_boards:
                print(inconsistent_err)
                return None

    drivers_specify_boards = None
    for coil in machine.coils.values():
        num_spec = coil.config["number"]
        if drivers_specify_boards is None:
            drivers_specify_boards = ("-" in num_spec)
        else:
            if ("-" in num_spec) != drivers_specify_boards:
                print(inconsistent_err)
                return None

    if switches_specify_boards != drivers_specify_boards:
        print(inconsistent_err)
        return None

    if switches_specify_boards:
        wire_specified_boards(machine, s)
    else:
        # TODO: the problem here is that we need to either guess, or work out from hardware, what types
        #       of boards are used.
        print("Can't currently wire FAST pinball if board numbers are not specified.")

    return s.dump()
