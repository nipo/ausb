"""FTDI constants and enumerations"""

import enum
from ausb import exception


class ChipType(enum.IntEnum):
    """FTDI chip type identifiers"""
    FT232AM = 0
    FT232BM = 1
    FT2232D = 2
    FT232R = 3
    FT2232H = 4
    FT4232H = 5
    FT232H = 6
    FT230X = 7


class Parity(enum.IntEnum):
    """UART parity settings"""
    Null = 0
    Odd = 1
    Even = 2
    Mark = 3
    Space = 4


class StopBits(enum.IntEnum):
    """UART stop bit settings"""
    One = 0
    OneAndHalf = 1
    Two = 2


class Bitmode(enum.IntEnum):
    """FTDI bitmode/channel mode settings"""
    Reset = 0
    Bitbang = 1
    Mpsse = 2
    Syncbb = 4
    Mcu = 8
    Opto = 16
    Cbus = 32
    Syncff = 64
    Ft1284 = 128


class Channel(enum.IntEnum):
    """FTDI interface identifiers (for multi-channel chips)"""
    A = 0
    B = 1
    C = 2
    D = 3


class ChannelType(enum.IntEnum):
    """FTDI channel type (from EEPROM configuration)"""
    UART = 0
    FIFO = 1
    OPTO = 2
    CPU = 4
    FT1284 = 8
    RS485 = 16


class Status(enum.IntFlag):
    """FTDI modem status flags (2-byte header in IN packets)"""
    B0    = 0x0001
    B1    = 0x0002
    B2    = 0x0004
    B3    = 0x0008
    CTS   = 0x0010
    DTS   = 0x0020
    RI    = 0x0040
    RLSD  = 0x0080
    DR    = 0x0100
    OE    = 0x0200
    PE    = 0x0400
    FE    = 0x0800
    BI    = 0x1000
    THRE  = 0x2000
    TEMT  = 0x4000
    RFE   = 0x8000


class MpsseIo(enum.IntFlag):
    """MPSSE I/O command flags (combined to form command bytes)"""
    WriteNeg   = 0x01
    Bits       = 0x02
    ReadNeg    = 0x04
    LsbFirst   = 0x08
    Write      = 0x10
    Read       = 0x20
    Tms        = 0x40
    Command    = 0x80


class MpsseCmd(enum.IntEnum):
    """MPSSE command opcodes"""
    SetBitsLow         = 0x80
    GetBitsLow         = 0x81
    SetBitsHigh        = 0x82
    GetBitsHigh        = 0x83
    LoopbackEnable     = 0x84
    LoopbackDisable    = 0x85
    ClkDiv             = 0x86
    SendImmediate      = 0x87
    WaitOnHigh         = 0x88
    WaitOnLow          = 0x89
    ClkDiv5Disable     = 0x8a
    ClkDiv5Enable      = 0x8b
    ThreePhaseEnable   = 0x8c
    ThreePhaseDisable  = 0x8d
    ClkBits            = 0x8e
    ClkBytes           = 0x8f
    ReadShort          = 0x90
    ReadExtended       = 0x91
    WriteShort         = 0x92
    WriteExtended      = 0x93
    ClkWaitHigh        = 0x94
    ClkWaitLow         = 0x95
    AdaptiveEnable     = 0x96
    AdaptiveDisable    = 0x97
    ClkBytesOrHigh     = 0x9c
    ClkBytesOrLow      = 0x9d
    DriveOpenCollector = 0x9e


class Request(enum.IntEnum):
    """FTDI vendor-specific control request codes"""
    Reset           = 0
    ModemCtrl       = 1
    SetFlowCtrl     = 2
    SetBaudRate     = 3
    SetData         = 4
    PollModemStatus = 5
    SetEventChar    = 6
    SetErrorChar    = 7
    SetLatencyTimer = 9
    GetLatencyTimer = 10
    SetBitmode      = 11
    ReadPins        = 12
    ReadEeprom      = 144
    WriteEeprom     = 145
    EraseEeprom     = 146


class ResetCtrl(enum.IntEnum):
    """FTDI reset control values"""
    All        = 0
    PurgeOut   = 1
    PurgeIn    = 2


class ModemCtrl(enum.IntEnum):
    """FTDI modem control values"""
    DisableFlowCtrl = 0
    RtsCtsHs        = (1 << 8)
    DtrDsrHs        = (2 << 8)
    XonXoffHs       = (4 << 8)
    SetDtrMask      = 1
    SetDtrHigh      = (1 | (SetDtrMask << 8))
    SetDtrLow       = (0 | (SetDtrMask << 8))
    SetRtsMask      = 2
    SetRtsHigh      = (2 | (SetRtsMask << 8))
    SetRtsLow       = (0 | (SetRtsMask << 8))


class FtdiError(exception.TransferError):
    """FTDI-specific error"""
    pass
