"""Pinproc object for tests."""

class FakePinProcModule:

    DriverCount = 256

    EventTypeAccelerometerIRQ = 11
    EventTypeAccelerometerX = 8
    EventTypeAccelerometerY = 9
    EventTypeAccelerometerZ = 10
    EventTypeBurstSwitchClosed = 7
    EventTypeBurstSwitchOpen = 6
    EventTypeDMDFrameDisplayed = 5
    EventTypeSwitchClosedDebounced = 1
    EventTypeSwitchClosedNondebounced = 3
    EventTypeSwitchOpenDebounced = 2
    EventTypeSwitchOpenNondebounced = 4

    MachineTypeCustom = 1
    MachineTypeInvalid = 0
    MachineTypePDB = 7
    MachineTypeSternSAM = 6
    MachineTypeSternWhitestar = 5
    MachineTypeWPC = 3
    MachineTypeWPC95 = 4
    MachineTypeWPCAlphanumeric = 2

    SwitchCount = 255
    SwitchNeverDebounceFirst = 192
    SwitchNeverDebounceLast = 255

    def __init__(self):
        self.pinproc = FakePinProc()

    def driver_state_pulse(self, driver, milliseconds):
        driver["state"] = 1
        driver["timeslots"] = 0
        driver["waitForFirstTimeSlot"] = False
        driver["outputDriveTime"] = milliseconds
        driver["patterOnTime"] = 0
        driver["patterOffTime"] = 0
        driver["patterEnable"] = False
        driver["futureEnable"] = False
        return driver

    def driver_state_disable(self, driver):
        driver["state"] = 0
        driver["timeslots"] = 0
        driver["waitForFirstTimeSlot"] = False
        driver["outputDriveTime"] = 0
        driver["patterOnTime"] = 0
        driver["patterOffTime"] = 0
        driver["patterEnable"] = False
        driver["futureEnable"] = False
        return driver

    def driver_state_patter(self, driver, millisecondsOn, millisecondsOff, originalOnTime, now):
        driver["state"] = True
        driver["timeslots"] = 0
        driver["waitForFirstTimeSlot"] = not now
        driver["outputDriveTime"] = originalOnTime
        driver["patterOnTime"] = millisecondsOn
        driver["patterOffTime"] = millisecondsOff
        driver["patterEnable"] = True
        driver["futureEnable"] = False
        return driver

    def driver_pulsed_patter(self, driver, millisecondsOn, millisecondsOff, milliseconds_overall_patter_time, now):
        driver["state"] = True
        driver["timeslots"] = 0
        driver["waitForFirstTimeSlot"] = not now
        driver["outputDriveTime"] = milliseconds_overall_patter_time
        driver["patterOnTime"] = millisecondsOn
        driver["patterOffTime"] = millisecondsOff
        driver["patterEnable"] = True
        driver["futureEnable"] = False
        return driver

    def normalize_machine_type(self, type):
        return 7

    def PinPROC(self, machine_type):
        return self.pinproc


class FakePinProc:

    """Behaves like pypinproc."""

    def __init__(self):
        self._memory = {
            0x00: {         # manager
                0x00: 0,            # chip id
                0x01: 0x00020006,   # version
                0x03: 0x01FF,       # dip switches
            },
            0x02: {         # switch controller
                0x1000: 0xA3,       # SW-16 Address 0 Reg 0
                0x1001: 0x00,       # SW-16 Address 0 Reg 1
                0x1040: 0xA3,       # SW-16 Address 1 Reg 0
                0x1041: 0x13,       # SW-16 Address 1 Reg 1
                0x1080: 0xA4,       # SW-16 Address 2 Reg 0
                0x1081: 0x00,       # SW-16 Address 2 Reg 1
            }
        }
        self._switches = [0, 1] + [0] * 100
        self._events = []

    def read_data(self, module, address):
        if module not in self._memory or address not in self._memory[module]:
            return 0
        return self._memory[module][address]

    def write_data(self, module, address, data):
        if module not in self._memory:
            self._memory[module] = {}
        self._memory[module][address] = data

    def switch_get_states(self):
        return self._switches

    def flush(self):
        pass

    def switch_update_rule(self, *args):
        return True

    def driver_update_group_config(self, *args):
        return True

    def driver_update_global_config(self, *args):
        return True

    def driver_update_state(self, *args):
        return True

    def driver_pulse(self, *args):
        return True

    def driver_schedule(self, *args):
        return True

    def driver_patter(self, *args):
        return True

    def driver_disable(self, *args):
        return True

    def reset(self, *args):
        self._events = []
        return True

    def watchdog_tickle(self):
        pass

    def close(self):
        pass

    def get_events(self):
        events = self._events
        self._events = []
        return events
