"""Interface defines for Pinotaur."""


class PinotaurDefines:

    """Pinotaur messages."""

    GetConnectedHardware = 0x00
    GetFirmwareVersion = 0x01
    GetAPIVersion = 0x02
    GetSimpleLampCount = 0x03
    GetSolenoidCount = 0x04
    GetModernLightCount = 0x09

    GiStatus = 0x0A
    GiChannelOn = 0x0B
    GiChannelOff = 0x0C
    GiAll = 0x0D
    ReportCoilCurrent = 0x0F

    SetCoilIdleCurrentMax = 0x10
    SetHoldTime = 0x11
    SetSolenoidPulsePWM = 0x12
    SetSolenoidHoldPWM = 0x13
    GetStatusSolenoid = 0x14
    DisableSolenoid = 0x16
    PulseSolenoid = 0x17
    SetSolenoidPulseTime = 0x18
    SetSolenoidRecycle = 0x19
    PulseSolenoidPWM = 0x1A
    SolenoidFuturePulse = 0x1B
    SetCurrent = 0x1C

    HardwareRuleSolenoid = 0x1E

    ProfileCoils = 0x1D
    SetupFlipperButton = 0x1E
    SetSolenoidNext = 0x1F

    SetRGBLight = 0x30
    SetRGBBlink = 0x31
    SetRGBPulse = 0x32
    SetRGBStrobe = 0x33

    SetBlinkSpeed = 0x34
    SetStrobeSpeed = 0x35
    SetChaseChild = 0x36
    SetRGBFade = 0x37

    SetBankLimits = 0x3A
    UpdateFrequency = 0x3B
    SetActualRGBCount = 0x3C
    LightFrameDone = 0x3D
    LoadLightShowFrame = 0x3E
    LightShowControl = 0x3F

    SetSwitchRamp = 0x50
    SetSwitchDebounce = 0x51
    SetSwitchClear = 0x52
    SetReportType = 0x57
    GetSwitchStatus = 0x58
    GetChangedSwitches = 0x59
    GetAllSwitches = 0x5A
    SetAutoAction = 0x5B
    ClearAutoAction = 0x5C
    SetUpEOSSwitch = 0x5E
    FlushChanged = 0x5F

    RelayControl = 0x60
    FlipperEnable = 0x61
    FlipperBeastHold = 0x62
    InitReset = 0x64
    WatchDogFlag = 0x65
    ClearCoil911 = 0x66
    SetErrorTolerance48V = 0x67

    StartLight = 0x6A
    StartLightBlinkSpeed = 0x6B
    LaunchLight = 0x6C
    LaunchLightBlinkSpeed = 0x6D

    CheckBootFaultFlag = 0x6F

    ProfileAMotor = 0x40
    GetLastMoveTime = 0x41
    SetServoCurrentLimits = 0x42
    ReadServoCurrent = 0x43
    SetInrushGracePeriod = 0x44
    ActionOnServoStall = 0x45
    ReadLastSafePosition = 0x46
    ReadMotorFaultFlags = 0x47

    MotorBankType = 0x70
    ReadMotorState = 0x71
    MotorGotoSwitch = 0x72
    StopMotor = 0x73
    MoveDCMotor = 0x74
    SetDCMotor = 0x75
    ReadDCMotor = 0x76

    MoveStepperMotor = 0x77
    SetStepperMotorSpeed = 0x78
    ReadStepperMotor = 0x79

    SetServoMotor = 0x7A
    Move180ServoMotor = 0x7B
    MoveContServoMotor = 0x7C
    ReadServoMotor = 0x7D
    DisableServoMotor = 0x7E
    ConfigServoMotors = 0x7F

    GetBanksBCD = 0x20
    SetBanksBCD = 0x21
    EraseNVMRow = 0x25
    ReadNVMRow = 0x28
    SetNVMAddress = 0x2A
    WriteNVMHalfPage = 0x2B
