
from typing import List, Tuple


class Board:
    def __init__(self, type: str):
        self.connectors = dict()  # Type: Dict[str, Connector]
        self.type = type
        self.ordinal = 0

    def addConnector(self, name: str, pinspecs: list):
        newCon = Connector(name, pinspecs, self)
        self.connectors[name] = newCon

    def __repr__(self):
        s = "Board " + self.type + ":\n"
        for c in self.connectors.values():
            s = s + str(c) + "\n"
        return s

    def __getitem__(self, key):
        return self.connectors[key]

    def dump(self):
        # Boards are not separate entities in wireviz, so just combine all connectors
        o = dict()
        for c in self.connectors.values():
            o.update(c.dump())
        return o



class Connector:
    def __init__(self, name: str, pinspecs: list, board: Board):
        self.name = name
        self.pins = []       # type: List[Pin]
        self.board = board
        for od, (name, vc) in enumerate(pinspecs):
            self.pins.append(Pin(name, vc, self, od))

    def __repr__(self):
        s = self.name + ":\n"
        for pi,p in enumerate(self.pins):
            s = s + str(pi) + ":" + str(p) + "\n"
        return s

    def __getitem__(self, key):
        return self.pins[key]

    def getDumpName(self):
        return self.board.type + " " + str(self.board.ordinal) + " " + self.name

    def dump(self):
        realName = self.getDumpName()
        pinLabels = []
        for p in self.pins:
            pinLabels.append(p.name)

        return {realName: {"pincount": len(self.pins), "pinlabels": pinLabels}}


class Pin:
    def __init__(self, name: str, vclass: int, connector: Connector, ordinal: int):
        self.name = name
        self.vclass = vclass
        self.connector = connector
        self.ordinal = ordinal

    def __repr__(self):
        return self.name + " " + str(self.vclass)


class Wire:
    def __init__(self, src: Pin, dest: Pin):
        if (src.vclass != dest.vclass):
            print("Connecting pins of different vclasses!")
            print(src, dest)
        self.src = src
        self.dest = dest


class System:
    def __init__(self):
        self.boards = []  # Type: List[Board]
        self.wires = []   # Type: List[Wire]

    def addBoard(self, board: Board):
        o = 0
        for b in self.boards:
            if b.type == board.type:
                o += 1
        board.ordinal = o
        self.boards.append(board)

    def connect(self, src: Pin, dest: Pin):
        assert src.connector.board in self.boards
        assert dest.connector.board in self.boards
        for w in self.wires:
            if (w.src == src) and (w.dest == dest):
                return
            if (w.dest == src) and (w.src == dest):
                return
        nw = Wire(src, dest)
        self.wires.append(nw)

    def dump(self):
        conDict = dict()
        for board in self.boards:
            conDict.update(board.dump())

        pairs = []  # Type: List[Tuple[Connector]]
        for wire in self.wires:
            if (wire.src.connector, wire.dest.connector) not in pairs:
                if (wire.dest.connector, wire.src.connector) not in pairs:
                    pairs.append((wire.src.connector, wire.dest.connector))

        wireDict = dict()
        conList = []

        wireOrdinal = 0
        for (srcc, destc) in pairs:
            activeWires = []   # Type: List[Wire]
            for wire in self.wires:
                if (wire.src.connector == srcc) and (wire.dest.connector == destc):
                    activeWires.append(wire)
                if (wire.src.connector == destc) and (wire.dest.connector == srcc):
                    activeWires.append(wire)
            compoundWireName = "W" + str(wireOrdinal)
            wireOrdinal += 1

            srcPinList = []
            wireList = []
            destPinList = []
            colorList = []
            wireColor = {
                12: "YE",
                5: "RD",
                48: "BU",
                0: "BK",
                -2: "WH",
                1: "WH",
                -1: "PK"
            }
            for x,awire in enumerate(activeWires):
                srcPinList.append(awire.src.ordinal+1)
                wireList.append(x+1)
                destPinList.append(awire.dest.ordinal+1)
                colorList.append(wireColor[awire.src.vclass])
            cableDict = [{srcc.getDumpName(): srcPinList}, {compoundWireName: wireList},
                       {destc.getDumpName(): destPinList}]
            conList.append(cableDict)

            wireDict.update({compoundWireName: {"wirecount": len(activeWires), "colors": colorList}})

        return {"connectors": conDict, "cables": wireDict, "connections": conList}



