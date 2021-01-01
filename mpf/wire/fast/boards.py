


from mpf.wire.base import Board, Connector, Pin, System
from ruamel.yaml import YAML
from sys import stdout

class FastPFB(Board):
    def __init__(self):
        super().__init__("PFB")
        self.addConnector("J1", [    # Coin door switch
            ("SW", 5),
            ("KEY", -1),
            ("GND", 0)
        ])
        self.addConnector("J2", [    # Coil power enable
            ("+", 5),
            ("-", 0),
            ("KEY", -1)
        ])
        self.addConnector("J3", [    # PSU In
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
        self.addConnector("J4", [    # Power Out
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
    def __init__(self, name):
        super().__init__(name)

    def fastNetConnector(self):
        return [("RJ45",1)]

    def getNetIn(self):
        pass

    def getNetOut(self):
        pass


class FastIOBoard(FastNetBoard):
    def __init__(self, name):
        super().__init__(name)
        pinRef = dict()


    def fastConnectorBlock(self, prefix, size, vclass, offset, keyLoc, firstGround):
        pins = []
        nonKeys = 0
        for pin in range(size):
            if pin == keyLoc:
                pins.append(("KEY",-1))
            elif pin >= firstGround:
                pins.append(("GND",0))
            else:
                pins.append((prefix+(str(nonKeys+offset)), vclass))
                nonKeys += 1
        return pins

    def getSwitchPin(self, id):
        pass


class FastIO3208(FastIOBoard):
    def __init__(self):
        super().__init__("IO 3208")
        self.addConnector("J1", self.fastNetConnector())
        self.addConnector("J2", self.fastNetConnector())
        self.addConnector("J3", self.fastConnectorBlock("Sw", 11, 12, 8, 3, 9))
        self.addConnector("J4", self.fastConnectorBlock("Dr", 12, 48, 0, 5, 9))
        self.addConnector("J6", self.fastConnectorBlock("Sw", 11, 12, 16, 2, 9))
        self.addConnector("J8", self.fastConnectorBlock("Sw", 11, 12, 0, 4, 9))
        self.addConnector("J9", self.fastConnectorBlock("Sw", 11, 12, 24, 1, 9))

    def getNetOut(self):
        return self["J1"][0]

    def getNetIn(self):
        return self["J2"][0]

    def getSwitchPin(self, id):
        if id < 4:
            return self["J8"][id]
        elif id < 8:
            return self["J8"][id+1]
        elif id < 11:
            return self["J3"][id-8]
        elif id < 16:
            return self["J3"][id-7]
        elif id < 18:
            return self["J6"][id-16]
        elif id < 24:
            return self["J6"][id-15]
        elif id == 24:
            return self["J9"][0]
        elif id < 32:
            return self["J9"][id-23]
        else:
            pass

    def getDriverPin(self, id):
        if id < 5:
            return self["J4"][id]
        elif id < 8:
            return self["J4"][id+1]
        else:
            pass




class FastIO1616(FastIOBoard):
    def __init__(self):
        super().__init__("IO 1616")
        self.addConnector("J1", self.fastNetConnector())
        self.addConnector("J2", self.fastNetConnector())
        self.addConnector("J3", self.fastConnectorBlock("Dr", 12, 48, 0, 4, 9))
        self.addConnector("J4", self.fastConnectorBlock("Dr", 12, 48, 8, 5, 9))
        self.addConnector("J7", self.fastConnectorBlock("Sw", 11, 12, 0, 4, 9))
        self.addConnector("J8", self.fastConnectorBlock("Sw", 11, 12, 8, 3, 9))

    def getNetOut(self):
        return self["J1"][0]

    def getNetIn(self):
        return self["J2"][0]


class FastIO0804(FastIOBoard):
    def __init__(self):
        super().__init__("IO 0807")
        self.addConnector("J1", self.fastNetConnector())
        self.addConnector("J2", self.fastNetConnector())
        self.addConnector("J3", self.fastConnectorBlock("Dr", 7, 48, 0, 4, 5))
        self.addConnector("J4", self.fastConnectorBlock("SW", 11, 12, 0, 4, 9))

    def getNetOut(self):
        return self["J1"][0]

    def getNetIn(self):
        return self["J2"][0]

    def getSwitchPin(self, i):
        if i < 4:
            return self["J4"][i]
        elif i < 8:
            return self["J4"][i+1]
        else:
            pass

    def getDriverPin(self, i):
        assert i <= 4
        return self["J3"][i]


class FastNC(FastNetBoard):
    def __init__(self):
        super().__init__("NC")
        ledConnector = [("GND", 0), ("DO", 1), ("5v", 5)]
        self.addConnector("J1", ledConnector)
        self.addConnector("J2", ledConnector)
        self.addConnector("J4", ledConnector)
        self.addConnector("J5", ledConnector)
        self.addConnector("J7", [
            ("12v", 12),
            ("12v", 12),
            ("5v", 5),
            ("5v", 5),
            ("GND", 0),
            ("KEY", -1),
            ("GND", 0)
        ])
        self.addConnector("J10", self.fastNetConnector())
        self.addConnector("J11", self.fastNetConnector())

    def getNetOut(self):
        return self["J10"][0]

    def getNetIn(self):
        return self["J11"][0]


class SerialLED(Board):
    def __init__(self, name):
        super().__init__("WS2812 " + name)
        self.addConnector("", [
            ("DOUT",1),
            ("DIN",1),
            ("VCC",1),
            ("NC",-1),
            ("VDD",5),
            ("GND",0)])

class Switch(Board):
    def __init__(self, name):
        super().__init__("SW " + name)
        self.addConnector("", [
            ("+", 12),
            ("-", 12)])

class Coil(Board):
    def __init__(self, name):
        super().__init__("DR " + name)
        self.addConnector("", [
            ("+", 48),
            ("-", 48)])



class FastSystem(System):
    def __init__(self):
        super().__init__()
        # We at least will need a power board and nano controller
        self.pfb = FastPFB()
        self.nc = FastNC()
        self.addBoard(self.pfb)
        self.addBoard(self.nc)
        self.connect(self.pfb["J4"][4], self.nc["J7"][2])
        self.connect(self.pfb["J4"][5], self.nc["J7"][3])
        self.connect(self.pfb["J4"][7], self.nc["J7"][0])
        self.connect(self.pfb["J4"][8], self.nc["J7"][4])
        self.connect(self.pfb["J4"][9], self.nc["J7"][6])


def wireLights(machine, s):
    LEDBoards = dict()
    for l in machine.lights:
        newBoard = SerialLED(l.name)

        numSpec = l.config["number"]
        if "-" in numSpec:
            parts = numSpec.split("-")
            realNum = (int(parts[0])*64) + (int(parts[1]))
        else:
            realNum = int(numSpec)
        LEDBoards[realNum] = newBoard
        s.addBoard(newBoard)

    channels = [(0, 63, "J1"),
                (64, 127, "J2"),
                (128, 191, "J4"),
                (192, 255, "J5")]

    for (start, end, ncport) in channels:
        # Daisy chain lights in channel
        # Sequentiality check for lights in channel
        for l in range(start+1,end+1):
            used = False
            if l in LEDBoards.keys():
                used = True
                cur = LEDBoards[l]
                if l-1 not in LEDBoards.keys():
                    print("Can't wire light", l, "because there is no previous light to connect it to.")
                    break
                prev = LEDBoards[l-1]
                s.connect(prev[""][0], cur[""][1])  # Wire data in sequence
                s.connect(prev[""][4], cur[""][4])  # Daisy chain power
                s.connect(prev[""][5], cur[""][5])  # Daisy chain ground
            if used:                      # If there were some lights on channel
                if start not in LEDBoards.keys():
                    print("Can't wire a FAST lighting channel because there is no light number", start, "to begin it.")
                    break
                startBoard = LEDBoards[start]  # Get first light
                s.connect(s.nc[ncport][1], startBoard[""][1])  # Data
                s.connect(s.nc[ncport][2], startBoard[""][4])  # Power
                s.connect(s.nc[ncport][0], startBoard[""][5])  # Ground


def determineBoards(machine, s):
    # Used if switches and drivers specify board numbers.

    # Sort switches and drivers by board
    maxSwitchBoard = 0
    fastBoardsSwitches = dict()
    for l in machine.switches:
        sw = Switch(l.name)
        s.addBoard(sw)
        numSpec = l.config["number"]
        parts = numSpec.split("-")
        boardNo = int(parts[0])
        if boardNo > maxSwitchBoard:
            maxSwitchBoard = boardNo
        switchNo = int(parts[1])
        if boardNo not in fastBoardsSwitches.keys():
            fastBoardsSwitches[boardNo] = dict()
        fastBoardsSwitches[boardNo][switchNo] = sw

    maxDriverBoard = 0
    fastBoardsDrivers = dict()
    for l in machine.coils:
        cl = Coil(l.name)
        s.addBoard(cl)
        numSpec = l.config["number"]
        parts = numSpec.split("-")
        boardNo = int(parts[0])
        if boardNo > maxDriverBoard:
            maxDriverBoard = boardNo
        driverNo = int(parts[1])
        if boardNo not in fastBoardsDrivers.keys():
            fastBoardsDrivers[boardNo] = dict()
        fastBoardsDrivers[boardNo][driverNo] = cl

    # Check for board consistency
    maxBoard = max(maxSwitchBoard, maxDriverBoard)
    for x in range(maxBoard+1):
        if x not in fastBoardsSwitches and x not in fastBoardsDrivers:
            print("I/O board numbers aren't consecutive. An empty board number",x,"would be needed!")

    fastBoards = dict()

    # Work out type of each board and add
    for board in range(maxBoard+1):
        switchesOnBoard = len(fastBoardsSwitches[board])
        driversOnBoard = len(fastBoardsDrivers[board])
        print("Board",board,"has",switchesOnBoard,"switches and",driversOnBoard,"drivers.")
        if switchesOnBoard > 32:
            print("Too many switches on board", board, ". No FAST board can support more than 32.")
            return
        if driversOnBoard > 16:
            print("Too many drivers on board", board, ". No FAST board can support more than 16.")
            return
        if switchesOnBoard > 16:
            if driversOnBoard > 8:
                print("Bad board", board, ". The only FAST board with more than 16 switches is the 3208, which",
                      "supports only 8 drivers.")
                return
            else:
                b = FastIO3208()
                s.addBoard(b)
                fastBoards[board] = b
                continue
        if switchesOnBoard <= 8:
            if driversOnBoard <= 4:
                b = FastIO0804()
                s.addBoard(b)
                fastBoards[board] = b
                continue
        b = FastIO1616()
        s.addBoard(b)
        fastBoards[board] = b

    # Build loop network
    for board in range(1,maxBoard+1):
        s.connect(fastBoards[board-1].getNetOut(), fastBoards[board].getNetIn())
    s.connect(fastBoards[0].getNetIn(), s.nc.getNetOut())
    s.connect(fastBoards[maxBoard].getNetOut(), s.nc.getNetIn())

    # Wire up switches and drivers to board
    for board in range(maxBoard+1):
        if board in fastBoardsSwitches.keys():
            for (pin, switch) in fastBoardsSwitches[board].items():
                s.connect(fastBoards[board].getSwitchPin(pin), switch[""][1])

        if board in fastBoardsDrivers.keys():
            for (pin, driver) in fastBoardsDrivers[board].items():
                s.connect(fastBoards[board].getDriverPin(pin), driver[""][1])

    # Daisy chain switch power
    for board in range(maxBoard+1):
        if board in fastBoardsSwitches.keys():
            switchesOnBoard = list(fastBoardsSwitches[board].values())
            for switch in range(1, len(switchesOnBoard)):
                s.connect(switchesOnBoard[switch][""][0], switchesOnBoard[switch-1][""][0])




def wire(machine):
    s = FastSystem()
    wireLights(machine, s)
    inconsistentErr = "Can't wire: all switch and driver numbers must be in the same format, (board-index) or " +\
                      "raw number, not a mixture of both."

    switchesSpecifyBoards = None
    for l in machine.switches:
        numSpec = l.config["number"]
        if switchesSpecifyBoards is None:
            switchesSpecifyBoards = ("-" in numSpec)
        else:
            if ("-" in numSpec) != switchesSpecifyBoards:
                print(inconsistentErr)
                return

    driversSpecifyBoards = None
    for l in machine.coils:
        numSpec = l.config["number"]
        if driversSpecifyBoards is None:
            driversSpecifyBoards = ("-" in numSpec)
        else:
            if ("-" in numSpec) != switchesSpecifyBoards:
                print(inconsistentErr)
                return

    if switchesSpecifyBoards != driversSpecifyBoards:
        print(inconsistentErr)
        return

    if switchesSpecifyBoards:
        determineBoards(machine, s)



    yaml = YAML()
    yaml.default_flow_style = False
    yaml.dump(s.dump(), stdout)





