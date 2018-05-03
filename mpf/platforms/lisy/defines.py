"""Interface defines for LISY."""


class LisyDefines:

    """LISY messages."""

    InfoGetConnectedLisyHardware = 0
    InfoLisyVersion = 1
    InfoGetApiVersion = 2
    InfoGetNumberOfLamps = 3
    InfoGetNumberOfSolenoids = 4
    InfoGetNumberOfSounds = 5
    InfoGetNumberOfDisplays = 6
    InfoGetDisplayDetails = 7
    InfoGetGameInfo = 8

    LampsGetStatusOfLamps = 10
    LampsSetLampOn = 11
    LampsSetLampOff = 12

    SolenoidsGetStatusOfSolenoid = 20
    SolenoidsSetSolenoidToOn = 21
    SolenoidsSetSolenoidToOff = 22
    SolenoidsPulseSolenioid = 23
    SolenoidsSetSolenoidPulseTime = 24

    DisplaysSetDisplay0To = 30
    DisplaysSetDisplay1To = 31
    DisplaysSetDisplay2To = 32
    DisplaysSetDisplay3To = 33
    DisplaysSetDisplay4To = 34
    DisplaysSetDisplay5To = 35
    DisplaysSetDisplay6To = 36

    SwitchesGetStatusOfSwitch = 40
    SwitchesGetChangedSwitches = 41

    SoundPlaySound = 50
    SoundStopAllSounds = 51
    SoundPlaySoundFile = 52
    SoundTextToSpeech = 53
    SoundSetVolume = 54

    GeneralReset = 100
    GeneralWatchdog = 101
