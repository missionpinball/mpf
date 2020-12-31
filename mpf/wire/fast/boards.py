


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


class FastIOBoard(FastNetBoard):
    def __init__(self, name):
        super().__init__(name)

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


class FastIO1616(FastIOBoard):
    def __init__(self):
        super().__init__("IO 1616")
        self.addConnector("J1", self.fastNetConnector())
        self.addConnector("J2", self.fastNetConnector())
        self.addConnector("J3", self.fastConnectorBlock("Dr", 12, 48, 0, 4, 9))
        self.addConnector("J4", self.fastConnectorBlock("Dr", 12, 48, 8, 5, 9))
        self.addConnector("J7", self.fastConnectorBlock("Sw", 11, 12, 0, 4, 9))
        self.addConnector("J8", self.fastConnectorBlock("Sw", 11, 12, 8, 3, 9))


class FastIO0804(FastIOBoard):
    def __init__(self):
        super().__init__("IO 0807")
        self.addConnector("J1", self.fastNetConnector())
        self.addConnector("J2", self.fastNetConnector())
        self.addConnector("J3", self.fastConnectorBlock("Dr", 7, 48, 0, 4, 5))
        self.addConnector("J4", self.fastConnectorBlock("SW", 11, 12, 0, 4, 9))


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


def wire(machine):
    s = FastSystem()
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






    if len(machine.lights) > 0:
        check = 0
        while check in LEDBoards.keys():
            check += 1
        if check != len(machine.lights):
            print("Problem: Lights on FAST have to be sequential. Light",check,"of",len(machine.lights),"is missing.")

    yaml = YAML()
    yaml.default_flow_style = False
    yaml.dump(s.dump(), stdout)





