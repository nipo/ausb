"""FTDI chip support for ausb"""

from .constant import (
    ChipType,
    Parity,
    StopBits,
    Bitmode,
    Interface,
    ChannelType,
    Status,
    MpsseIo,
    MpsseCmd,
    Request,
    ResetCtrl,
    ModemCtrl,
    FtdiError,
)

from .device import (
    Ftdi,
    FtdiChannel,
)

from .mpsse import (
    Mpsse,
    MpsseOperation,
    # GPIO operations
    SetBitsLow,
    SetBitsHigh,
    GetBitsLow,
    GetBitsHigh,
    # Clock operations
    ClkDiv,
    ClkDiv5Enable,
    ClkDiv5Disable,
    # Loopback
    LoopbackEnable,
    LoopbackDisable,
    # Three-phase clocking
    ThreePhaseEnable,
    ThreePhaseDisable,
    # Adaptive clocking
    AdaptiveEnable,
    AdaptiveDisable,
    # Wait operations
    WaitOnHigh,
    WaitOnLow,
    # Drive mode
    DriveOpenCollector,
    # Data shift operations
    ShiftOut,
    ShiftIn,
    ShiftInOut,
    TmsShift,
    # Control
    SendImmediate,
)

from .eeprom import (
    Eeprom,
)

from .stream import (
    FtdiStreamReader,
)

__all__ = [
    # Constants
    'ChipType',
    'Parity',
    'StopBits',
    'Bitmode',
    'Interface',
    'ChannelType',
    'Status',
    'MpsseIo',
    'MpsseCmd',
    'Request',
    'ResetCtrl',
    'ModemCtrl',
    'FtdiError',
    # Device
    'Ftdi',
    'FtdiChannel',
    # MPSSE
    'Mpsse',
    'MpsseOperation',
    'SetBitsLow',
    'SetBitsHigh',
    'GetBitsLow',
    'GetBitsHigh',
    'ClkDiv',
    'ClkDiv5Enable',
    'ClkDiv5Disable',
    'LoopbackEnable',
    'LoopbackDisable',
    'ThreePhaseEnable',
    'ThreePhaseDisable',
    'AdaptiveEnable',
    'AdaptiveDisable',
    'WaitOnHigh',
    'WaitOnLow',
    'DriveOpenCollector',
    'ShiftOut',
    'ShiftIn',
    'ShiftInOut',
    'TmsShift',
    'SendImmediate',
    # EEPROM
    'Eeprom',
    # Stream
    'FtdiStreamReader',
]
