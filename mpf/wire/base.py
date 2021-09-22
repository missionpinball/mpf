"""Base classes and utilities for wiring."""
from typing import Dict, List, Tuple, TypeVar, Callable

wire_colors = {
    12: "YE",
    5: "RD",
    48: "BU",
    0: "BK",
    -2: "WH",
    1: "WH",
    -1: "PK"
}

PinSpecs = List[Tuple[str, int]]


class Board:

    """A board with connectors. This is not an element in wireviz, but useful to track."""

    def __init__(self, board_type: str):
        """Create a board with the given type."""
        # Note: board_type is used because "type" is reserved.
        self.connectors: Dict[str, Connector] = dict()
        self.board_type = board_type
        self.ordinal = 0

    def add_connector(self, name: str, pinspecs: PinSpecs):
        """Add a new connector to this board, with the listed set of pins."""
        new_connector = Connector(name, pinspecs, self)
        self.connectors[name] = new_connector

    def __repr__(self):
        """Output simple string representation of board for debugging."""
        s = "Board " + self.board_type + ":\n"
        for c in self.connectors.values():
            s = s + str(c) + "\n"
        return s

    def __getitem__(self, key):
        """Allow indexing to be used to access connectors dictionary."""
        return self.connectors[key]

    def dump(self) -> dict:
        """Output this board in a form suitable for passing to yaml output."""
        # Boards are not separate entities in wireviz, so just combine all connectors
        o = dict()
        for c in self.connectors.values():
            o.update(c.dump())
        return o


class Connector:

    """A single connector on a board."""

    def __init__(self, name: str, pinspecs: PinSpecs, board: Board):
        """Create a connector with the given name and pin specifications on the given board.

        Easier to use board.add_connector().
        """
        self.name = name
        self.pins: List[Pin] = []
        self.board = board
        for od, (pin_name, vc) in enumerate(pinspecs):
            self.pins.append(Pin(pin_name, vc, self, od))

    def __repr__(self):
        """Output simple string representation of connector for debugging."""
        s = self.name + ":\n"
        for pi, p in enumerate(self.pins):
            s = s + str(pi) + ":" + str(p) + "\n"
        return s

    def __getitem__(self, key):
        """Allow indexing to be used to access pins."""
        return self.pins[key]

    def get_display_name(self) -> str:
        """Get the name of this connector to be shown in wireviz."""
        if self.name != "":
            return self.board.board_type + " " + str(self.board.ordinal) + " " + self.name
        return self.board.board_type

    def dump(self) -> dict:
        """Output this connector in a form suitable for passing ot yaml output."""
        display_name = self.get_display_name()
        pin_labels: List[str] = []
        for p in self.pins:
            pin_labels.append(p.name)

        return {display_name: {"pincount": len(self.pins), "pinlabels": pin_labels}}


class Pin:

    """A pin on a connector.

    In the case of a connector such as USB or RJ45, where the pin assignments
    aren't relevant, may represent the whole connector.
    """

    def __init__(self, name: str, vclass: int, connector: Connector, ordinal: int):
        """Initialize a pin with given name and voltage class, on the given board.

        This should probably be done through addConnector() since the pin's position is needed.
        """
        self.name = name
        self.vclass = vclass
        self.connector = connector
        self.ordinal = ordinal

    def __repr__(self):
        """Return simple string debug output for pin."""
        return self.name + " " + str(self.vclass)


class Wire:

    """Represents a wire connecting two pins.

    In reality electrical wires don't have a 'direction', but wireviz puts sources on the
    left and destinations on the right, so we track them.
    """

    def __init__(self, src: Pin, dest: Pin):
        """Initialize a wire connecting the two specified pins.

        This isn't a lot of use outside of a System, so you probably want to use System.connect().
        """
        if src.vclass != dest.vclass:
            print("Connecting pins of different vclasses!")
            print(src, dest)
        self.src = src
        self.dest = dest

    def __eq__(self, other):
        """Wires that connect the same pins are equal, regardless of order."""
        if other is not Wire:
            return False
        return self.connects_pins(other.src, other.dest)

    def connects_pins(self, a: Pin, b: Pin) -> bool:
        """Return if the wire connects these two pins (in either direction)."""
        if self.src == a and self.dest == b:
            return True
        if self.src == b and self.dest == a:
            return True
        return False

    def connects_connectors(self, a: Connector, b: Connector) -> bool:
        """Return if the wire connects these two connectors (in either direction and any pin)."""
        if self.src.connector == a and self.dest.connector == b:
            return True
        if self.src.connector == b and self.dest.connector == a:
            return True
        return False


class SerialLED(Board):

    """A basic serial LED."""

    def __init__(self, name):
        """Initialize the LED with the WS2812 pinout."""
        super().__init__("WS2812 " + name)
        self.add_connector("", [
            ("DOUT", 5),
            ("DIN", 5),
            ("VCC", 5),
            ("NC", -1),
            ("VDD", 5),
            ("GND", 0)])


class Switch(Board):

    """A basic switch."""

    def __init__(self, name):
        """Initialize the switch with + and - sides."""
        super().__init__("SW " + name)
        self.add_connector("", [
            ("+", 5),
            ("-", 5)])


class Coil(Board):

    """A basic coil/driver."""

    def __init__(self, name):
        """Initialize the coil with + and - sides.

        TODO: Flipper coils may have multiple negative sides for hold and flip.
        """
        super().__init__("DR " + name)
        self.add_connector("", [
            ("+", 48),
            ("-", 48)])


# pylint: disable=invalid-name
T = TypeVar("T")


class System:

    """A system of wires, boards and connectors."""

    def __init__(self):
        """Initialize an empty system."""
        self.boards: List[Board] = []
        self.wires: List[Wire] = []

    def add_board(self, board: Board):
        """Add a board to the system."""
        # Set ordinal based on number of existing boards of same type.
        o = sum([1 for b in self.boards if b.board_type == board.board_type])
        board.ordinal = o
        self.boards.append(board)

    def connect(self, src: Pin, dest: Pin):
        """Add a wire between two pins."""
        assert src.connector.board in self.boards
        assert dest.connector.board in self.boards
        nw = Wire(src, dest)
        if nw not in self.wires:
            self.wires.append(nw)

    def daisy_chain_list(self, items: List[T], get_in: Callable[[T], Pin], get_out: Callable[[T], Pin]):
        """Daisy chains connections between arbitrary items that can calculate pins.

        :param items The list of items, of any type.
        :param get_in Function to apply to an item to get the input pin.
        :param get_out Function to apply to an item to get the output pin.
        """
        if len(items) < 2:
            return
        for index in range(1, len(items)):
            self.connect(get_out(items[index - 1]), get_in(items[index]))

# pylint: disable=too-many-arguments
    def daisy_chain_dict(self, items: Dict[int, T], get_in: Callable[[T], Pin], get_out: Callable[[T], Pin],
                         start: int, ladder: bool) -> bool:
        """Like daisy_chain_list but takes a dict and checks it for sequentiality in the process of daisy chaining.

        Used for directly daisy chaining elements with specified numbers.
        :param items The dictionary from numbers to items, of any type.
        :param get_in Function to apply to an item to get the input pin.
        :param get_out Function to apply to an item to get the output pin.
        :param start Number to start accessing the dictionary from.
        :param ladder If true, alternate chain connections are flipped to create a vertical ladder in wireviz.
        :return True if all items in the dictionary were sequentially numbered. If not, the chain stops
                     at the first gap.
        """
        if len(items) < 2:
            return True
        if start not in items:
            return False
        even = False
        for index in range(start + 1, start + len(items)):
            if index not in items:
                return False
            if even or not ladder:
                self.connect(get_out(items[index - 1]), get_in(items[index]))
            else:
                self.connect(get_in(items[index]), get_out(items[index - 1]))
            even = not even
        return True

    # pylint: disable=too-many-locals
    def dump(self) -> dict:
        """Output this system in a format suitable for yaml output."""
        # Output all connectors
        connectors_dict = dict()       # Connectors dictionary for YAML
        for board in self.boards:
            connectors_dict.update(board.dump())

        # Calculate list of all pairs of connectors (NB not pins) connected by wires
        pairs: List[Tuple[Connector, Connector]] = []
        for wire in self.wires:
            if (wire.src.connector, wire.dest.connector) not in pairs and \
                    (wire.dest.connector, wire.src.connector) not in pairs:
                pairs.append((wire.src.connector, wire.dest.connector))

        wire_dict = dict()              # Wires dictionary for YAML
        connection_list: list = []      # Connections list for YAML
        wire_ordinal = 0                # Serial number for next wire

        for (srcc, destc) in pairs:
            # Find all wires that connect each pair
            wires_this_pair: List[Wire] = [wire for wire in self.wires if wire.connects_connectors(srcc, destc)]

            # Connect them into a single multi-thread "wire" for wireviz
            # Calculate name for the wire based on current ordinal
            compound_wire_name = "W" + str(wire_ordinal)
            wire_ordinal += 1

            # Wireviz requires three lists per wire set, matched in order: source pins, wire thread numbers,
            # destination pins
            src_pin_list = []
            wire_list = []
            dest_pin_list = []

            # Wire colours for wire specifier
            color_list = []

            for x, awire in enumerate(wires_this_pair):
                src_pin_list.append(awire.src.ordinal + 1)
                wire_list.append(x + 1)
                dest_pin_list.append(awire.dest.ordinal + 1)
                color_list.append(wire_colors[awire.src.vclass])

            # Weird wireviz format for the cables block: a list of single entry dictionaries of lists
            connection_dict = [{srcc.get_display_name(): src_pin_list}, {compound_wire_name: wire_list},
                               {destc.get_display_name(): dest_pin_list}]
            connection_list.append(connection_dict)

            # Add entry to wires block
            wire_dict.update({compound_wire_name: {"wirecount": len(wires_this_pair), "colors": color_list}})

        return {"connectors": connectors_dict, "cables": wire_dict, "connections": connection_list}
