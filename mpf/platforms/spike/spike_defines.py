"""Spike defines."""
from typing import List


class SpikeNodebus:

    """Spike message defines."""

    __slots__ = []  # type: List[str]

    Poll = 0x00
    GetBridgeVersion = 0x03
    GetBridgeState = 0x05
    SetResponseTime = 0x06
    SetBackboxLight = 0x09      # Spike 2
    SetInputMask = 0x09         # unused
    SetBackboxPWMFreqDiv = 0x0b     # Spike 2
    GetInputState = 0x11        # unused
    GetInputMask = 0x12         # unused
    GetLEDMask = 0x13           # Spike 2
    SetNumLEDsInputs = 0x14     # Spike 2
    SSPWrite = 0x20             # unused
    SSPRead = 0x21              # unused
    StepperStatus = 0x30        # unused
    StepperSet = 0x31           # unused
    StepperConfig = 0x32        # unused
    StepperHome = 0x34          # unused
    StepperInfo = 0x38          # unused
    CoilFireRelease = 0x40
    CoilSetReflex = 0x41
    CoilGetPWMFreq = 0x42       # unused; len: 1?
    CoilSetPriority = 0x43      # unused
    CoilGetPriority = 0x43      # unused; dunno if this is right
    CoilSetOCIgnoreMap = 0x44   # Spike 1
    CoilSetOCBehavior = 0x44    # Spike 2; Same as CoilSetOCIgnoreMap
    OCGetFault = 0x4a           # Spike 2
    SetAC = 0x50                # unused; len: 4
    MotorConfigure = 0x51       # unused; len: 12; 10 bytes of motor config
    MotorStatus = 0x52          # unused
    MotorHome = 0x53            # unused; len: 6
    MotorAway = 0x54            # unused; len: 6
    MotorGo = 0x55              # unused; len: 8
    MotorStop = 0x56            # Spike 2
    MotorConfigure2 = 0x57      # Spike 2; NODEBUS_DoMotorConfigure uses this when param4 is set
    ConfigQuadrature = 0x60     # unused
    ConfigInput = 0x70          # unused
    SetLEDMask = 0x72           # Spike 2
    SetSyncTime = 0x73          # Spike 2
    SetLed = 0x80               # can set one or multiple LEDs
    SetTraffic = 0xF0
    SetRGBMulti = 0xC0          # Spike 2; name unknown; part of NODEBUS_SetLEDMultiple when LED > 0x40
    SetRGB = 0xC1               # Spike 2
    RGBSuspend = 0xC3           # Spike 2
    RGBResume = 0xC4            # Spike 2
    SetRGBPalette = 0xCF        # Spike 2
    SetRGBSweep = 0xC2          # Spike 2
    Reset = 0xF1
    LCDSet = 0xF2               # unused
    SendKey = 0xF3              # does something with CRC32
    SendData = 0xF4             # unused; not sure
    GetChecksum = 0xF5          # verify firmware somehow
    GetDebug = 0xF6             # unused; maybe also EraseFlash
    WriteFlash = 0xF7           # unused; maybe also wrong
    GetBootStatus = 0xF8        # unused
    GetFullBoardId = 0xF9       # unused; len: 2, reads 0x10 bytes back
    GetCoilReflexInfo = 0xF9    # unused; len: 2, reads 0x10 bytes back
    GetCoilCurrent = 0xFA
    GetStackFree = 0xFA         # Spike 2; Probably part of the response of GetCoilCurrent
    DisableOC = 0xFB            # unused
    GetBoardId = 0xFD           # unused; len: 1, probably reads 0x0C bytes back
    GetVersion = 0xFE
    GetStatus = 0xFF
