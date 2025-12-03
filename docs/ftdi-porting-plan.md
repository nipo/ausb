# FTDI Integration into ausb - Porting Plan

**Date:** 2025-12-04
**Status:** ✅ Complete
**Scope:** Port synchronous FTDI driver from crobe to ausb asyncio framework

## Implementation Progress

- [x] **constant.py** - ✅ Complete (2025-12-04)
- [x] **device.py** - ✅ Complete (2025-12-04)
- [x] **stream.py** - ✅ Complete (2025-12-04)
- [x] **eeprom.py** - ✅ Complete (2025-12-04)
- [x] **mpsse.py** - ✅ Complete (2025-12-04)
- [x] **__init__.py** - ✅ Complete (2025-12-04)

## Overview

This document describes the plan to port FTDI chip support (device model, MPSSE engine, EEPROM access) from the synchronous crobe codebase to the ausb asyncio-based USB library.

### Source Code

**Original location:** `/Users/nipo/projects/crobe-wip/crobe/adapter/ftdi/`

**Files:**
- `backend.py` - Device/Handle model, MPSSE engine, constants
- `basic.py` - Adapter interfaces (JTAG, SWD, I2C, SPI, Chipcon)
- `eeprom.py` - EEPROM access
- `mpsse.py` - MpsseOp operation classes (partial implementation)

### Target Structure

**New location:** `ausb/util/ftdi/`

**Files:**
```
ausb/util/ftdi/
├── __init__.py          # Public API exports
├── constant.py          # All enums and constants
├── device.py            # FTDI device/channel handles
├── mpsse.py             # MPSSE async operation engine
├── stream.py            # FtdiStreamReader (status header handling)
└── eeprom.py            # EEPROM access
```

## Design Decisions

### Scope Constraints

1. **In Scope:**
   - FTDI device model (chip detection, features)
   - Channel mode setting (bitmode, latency, GPIO)
   - MPSSE operation engine with async/await
   - EEPROM read/write
   - FTDI-specific StreamReader (2-byte status header)

2. **Out of Scope:**
   - Protocol interfaces (JTAG, SWD, I2C, SPI, Chipcon)
   - Component/model base classes from crobe
   - High-level adapter abstractions

### Key Architectural Choices

#### 1. No BitString Dependency

**Rationale:** MPSSE commands operate in two modes:
- **Byte mode** (bit 1 clear): Full bytes, use `bytes` objects
- **Bit mode** (bit 1 set): Maximum 7 bits, use `(value: int, bit_count: int)` tuples

**Data representation:**
```python
# For byte operations
data: bytes

# For bit operations (≤7 bits)
data: tuple[int, int]  # (value, bit_count) where 1 ≤ bit_count ≤ 7
```

#### 2. Async Operation Model (Option B: "Await Triggers Flush")

**Model:**
- Calling operation methods (e.g., `mpsse.gpio_set()`) immediately queues the operation and returns a `Future`
- Operations are **not** executed immediately
- Awaiting **any** operation triggers flush of **all** pending operations
- Worker coroutine serializes all pending ops, performs I/O, parses responses, resolves futures

**Benefits:**
- Natural batching without explicit context managers
- Efficient USB bandwidth usage (one bulk transfer for multiple operations)
- Clean API: `result = await op1` implicitly batches with any queued ops

**Example:**
```python
# All three operations are queued
op1 = mpsse.gpio_set(3, True)    # Returns Future, queued
op2 = mpsse.gpio_set(4, False)   # Returns Future, queued
op3 = mpsse.gpio_get(0)          # Returns Future, queued

# Awaiting ANY operation flushes ALL pending ops
result = await op3  # Triggers single USB transaction for all 3 ops
```

#### 3. Futures as Operation Objects

**Architecture:**
```python
class MpsseOperation(asyncio.Future):
    def lower(self) -> tuple[bytes, int]:
        """Serialize to MPSSE command bytes.
        Returns: (command_bytes, expected_response_size)
        """

    def gather(self, response: bytes):
        """Parse response and call self.set_result(value)"""
```

**Benefits:**
- Operations **are** Futures (not wrappers)
- Standard asyncio patterns work naturally
- Cancellation support (per requirement: doesn't affect operation stream)

#### 4. ausb Device Model Integration

**Pattern:**
```python
# Use ausb descriptors and handles
dev_desc = ctx.device_get(vendor_id=0x0403)
dev_handle = dev_desc.open()

# Wrap in FTDI-specific layer
ftdi = await Ftdi.from_device(dev_handle)
channel = FtdiChannel(ftdi, interface_no=0, mode=Bitmode.Mpsse)
await channel.initialize()

# MPSSE engine
mpsse = Mpsse(channel, gpio_oe=0xfb, gpio_value=0)
```

**Rationale:**
- Reuse ausb's async control transfers (`device.vendor_control()`)
- Reuse ausb's transfer timeout/error handling
- Reuse ausb's endpoint abstractions

#### 5. FTDI StreamReader for Status Headers

FTDI chips prepend a 2-byte modem status to every IN packet. This requires a specialized StreamReader:

```python
class FtdiStreamReader(EndpointStreamReader):
    """Extends ausb StreamReader to strip FTDI status headers"""

    async def _background_reader(self):
        # Override to extract 2-byte status from each packet
        packet = await self._endpoint.read()
        self.last_status = Status(int.from_bytes(packet[:2], "little"))
        data = packet[2:]  # Strip status, add to buffer
```

**StreamWriter:** Use ausb `EndpointStreamWriter` directly (no FTDI-specific modifications needed).

## Module Specifications

### 1. constant.py

**Port from:** `backend.py` lines 12-148

**Content:**
```python
import enum
from ausb import exception

class ChipType(enum.IntEnum):
    FT232AM = 0
    FT232BM = 1
    FT2232D = 2
    FT232R = 3
    FT2232H = 4
    FT4232H = 5
    FT232H = 6
    FT230X = 7

class Parity(enum.IntEnum):
    Null = 0
    Odd = 1
    Even = 2
    Mark = 3
    Space = 4

class StopBits(enum.IntEnum):
    One = 0
    OneAndHalf = 1
    Two = 2

class Bitmode(enum.IntEnum):
    Reset = 0
    Bitbang = 1
    Mpsse = 2
    Syncbb = 4
    Mcu = 8
    Opto = 16
    Cbus = 32
    Syncff = 64
    Ft1284 = 128

class Interface(enum.IntEnum):
    A = 0
    B = 1
    C = 2
    D = 3

class Status(enum.IntFlag):
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
    WriteNeg   = 0x01
    Bits       = 0x02
    ReadNeg    = 0x04
    LsbFirst   = 0x08
    Write      = 0x10
    Read       = 0x20
    Tms        = 0x40
    Command    = 0x80

class MpsseCmd(enum.IntEnum):
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
    All        = 0
    PurgeOut   = 1
    PurgeIn    = 2

class ModemCtrl(enum.IntEnum):
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
```

**Changes from original:**
- No dependencies on crobe
- Inherit `FtdiError` from `ausb.exception.TransferError`

---

### 2. device.py

**Port from:** `backend.py` Device and Handle classes

**Key Classes:**

#### Ftdi

Wrapper around ausb `Device` handle with FTDI-specific detection and control.

```python
import asyncio
from .constant import ChipType, Request, ResetCtrl

class Ftdi:
    """FTDI device wrapper with chip detection and control"""

    CHIP_TYPE_LUT = {
        0x0200: ChipType.FT232AM,
        0x0400: ChipType.FT232BM,
        0x0500: ChipType.FT2232D,
        0x0600: ChipType.FT232R,
        0x0700: ChipType.FT2232H,
        0x0800: ChipType.FT4232H,
        0x0900: ChipType.FT232H,
        0x1000: ChipType.FT230X,
    }

    def __init__(self, device_handle):
        """
        :param device_handle: ausb Device handle (from descriptor.open())
        """
        self.device = device_handle
        self.chip_type = self._detect_chip_type()

    def _detect_chip_type(self) -> ChipType:
        """Detect chip type from bcdDevice descriptor"""
        bcd = self.device.descriptor.bcd_device
        isn = self.device.descriptor.serial_number_index

        # Special case: FT232AM vs FT232BM
        if bcd == 0x0200 and isn == 0:
            return ChipType.FT232BM

        return self.CHIP_TYPE_LUT.get(bcd)

    @classmethod
    async def from_device(cls, device_handle):
        """Factory: create and initialize FTDI wrapper"""
        ftdi = cls(device_handle)
        await ftdi.reset()
        return ftdi

    async def reset(self, target=ResetCtrl.All):
        """Reset device/buffers via vendor control request"""
        await self.device.vendor_control(Request.Reset, target, 0, b'')

    async def eeprom_word_read(self, index: int) -> int:
        """Read single EEPROM word (16-bit)"""
        r = await self.device.vendor_control(Request.ReadEeprom, 0, index, 2)
        return int.from_bytes(r, "little")

    async def eeprom_word_write(self, index: int, value: int):
        """Write single EEPROM word (16-bit)"""
        await self.device.vendor_control(Request.WriteEeprom, value, index, b'')
```

#### FtdiChannel

Represents one FTDI channel (interface) with mode-specific configuration.

```python
from .constant import Bitmode, Request, ResetCtrl, Status

class FtdiChannel:
    """FTDI channel with bitmode and endpoint management"""

    def __init__(self, ftdi, interface_no, mode=Bitmode.Reset):
        """
        :param ftdi: Ftdi instance
        :param interface_no: Interface number (0=A, 1=B, etc.)
        :param mode: Bitmode to set after initialization
        """
        self.ftdi = ftdi
        self.device = ftdi.device
        self.interface_no = interface_no
        self.mode = mode

        # Claim interface
        self.interface = self.device.interface_claim(interface_no)

        # Get bulk endpoints
        # FTDI endpoint addresses: Interface A: 0x81/0x02, Interface B: 0x83/0x04
        in_addr = 0x81 + (interface_no * 2)
        out_addr = 0x02 + (interface_no * 2)

        in_ep_desc = self.interface.descriptor.endpoint_by_address(in_addr)
        out_ep_desc = self.interface.descriptor.endpoint_by_address(out_addr)

        self.ep_in = self.interface.open(in_ep_desc)
        self.ep_out = self.interface.open(out_ep_desc)

        # FTDI-specific state
        self.status = Status(0)

    async def initialize(self):
        """Initialize channel for configured mode"""
        await self.bitmode_set(Bitmode.Reset)
        await self.flush_buffers()
        await self.latency_timer_set(2)

        if self.mode != Bitmode.Reset:
            await self.bitmode_set(self.mode)

    async def bitmode_set(self, mode, gpio_oe=0):
        """
        Set bitmode and GPIO output enable.

        :param mode: Bitmode enum value
        :param gpio_oe: GPIO output enable mask (low byte)
        """
        await self.device.vendor_control(
            Request.SetBitmode,
            (mode << 8) | gpio_oe,
            self.interface_no + 1,  # FTDI uses 1-based indexing
            b'')

    async def latency_timer_set(self, timer):
        """
        Set latency timer (1-255 ms).

        Lower values reduce latency but increase USB overhead.
        Default is typically 16ms, we use 2ms for MPSSE.
        """
        await self.device.vendor_control(
            Request.SetLatencyTimer,
            timer,
            self.interface_no + 1,
            b'')

    async def flush_buffers(self):
        """Flush both IN and OUT endpoint buffers"""
        await self.device.vendor_control(
            Request.Reset, ResetCtrl.PurgeOut,
            self.interface_no + 1, b'')
        await self.device.vendor_control(
            Request.Reset, ResetCtrl.PurgeIn,
            self.interface_no + 1, b'')

    async def write(self, data: bytes):
        """Raw write to OUT endpoint"""
        await self.ep_out.write(data)

    async def read(self, size: int) -> tuple[bytes, Status]:
        """
        Raw read from IN endpoint with status extraction.

        FTDI prepends 2-byte modem status to every packet.

        :param size: Number of data bytes to read (excluding status)
        :returns: (data, status) tuple
        """
        packet = await self.ep_in.read(size + 2)
        status = Status(int.from_bytes(packet[:2], "little"))
        self.status = status
        return packet[2:], status
```

**Changes from original:**
- All I/O methods are async
- Use ausb `Device.vendor_control()` instead of usb1 direct calls
- Interface claiming uses ausb model
- Endpoints accessed via `interface.open(endpoint_descriptor)`

---

### 3. mpsse.py

**Port from:** `backend.py` Mpsse class + `mpsse.py` operation classes

**Complete MPSSE command set:**

All MPSSE operations inherit from `asyncio.Future` and implement:
- `lower() -> tuple[bytes, int]`: Serialize to command bytes
- `gather(response: bytes)`: Parse response and resolve future

**Operation Classes:**

1. **GPIO Operations:**
   - `SetBitsLow(value, oe)`
   - `SetBitsHigh(value, oe)`
   - `GetBitsLow()`
   - `GetBitsHigh()`

2. **Clock Configuration:**
   - `ClkDiv(divisor)`
   - `ClkDiv5Enable()`
   - `ClkDiv5Disable()`

3. **Loopback:**
   - `LoopbackEnable()`
   - `LoopbackDisable()`

4. **Three-Phase Clocking:**
   - `ThreePhaseEnable()`
   - `ThreePhaseDisable()`

5. **Adaptive Clocking:**
   - `AdaptiveEnable()`
   - `AdaptiveDisable()`

6. **Wait Operations:**
   - `WaitOnHigh()`
   - `WaitOnLow()`

7. **Drive Mode:**
   - `DriveOpenCollector(low_pins, high_pins)`

8. **Data Shift:**
   - `ShiftOut(data, write_neg, lsb_first)` - Write-only
   - `ShiftIn(length, read_neg, lsb_first)` - Read-only
   - `ShiftInOut(data, write_neg, read_neg, lsb_first)` - Simultaneous read/write
   - `TmsShift(tms_bits, tdi, read_tdo, write_neg, lsb_first)` - TMS mode

9. **Control:**
   - `SendImmediate()` - Force FTDI buffer flush

**Mpsse Engine:**

```python
class Mpsse:
    """MPSSE async operation engine with implicit batching"""

    def __init__(self, channel, gpio_oe=0, gpio_value=0):
        self.channel = channel
        self._pending = deque()  # Queue of MpsseOperation
        self._flush_lock = asyncio.Lock()
        self._worker_scheduled = False

        # GPIO state tracking
        self._gpio_oe = gpio_oe
        self._gpio_value = gpio_value

        # Chip capabilities
        self.can_div5 = channel.ftdi.chip_type in [
            ChipType.FT2232H, ChipType.FT232H, ChipType.FT4232H]
        self.can_opendrain = channel.ftdi.chip_type == ChipType.FT232H
        self.base_freq = (12e6 if channel.ftdi.chip_type == ChipType.FT2232D
                         else 60e6)
        self._divisor = (False, 0)  # (div5_enable, divisor)

    def _queue(self, op: MpsseOperation) -> MpsseOperation:
        """Queue operation and schedule worker"""
        self._pending.append(op)
        self._schedule_worker()
        return op

    async def _flush_worker(self):
        """Serialize all pending ops, execute I/O, parse responses"""
        async with self._flush_lock:
            self._worker_scheduled = False

            if not self._pending:
                return

            # Build command stream
            commands = []
            response_sizes = []
            operations = []

            while self._pending:
                op = self._pending.popleft()
                operations.append(op)
                cmd, rsp_size = op.lower()
                commands.append(cmd)
                response_sizes.append(rsp_size)

            # Add SendImmediate
            commands.append(bytes([MpsseCmd.SendImmediate]))

            # Execute I/O
            try:
                await self.channel.write(b''.join(commands))

                total_response = sum(response_sizes)
                if total_response > 0:
                    response_blob, _ = await self.channel.read(total_response)
                else:
                    response_blob = b''

                # Distribute responses to operations
                offset = 0
                for op, rsp_size in zip(operations, response_sizes):
                    chunk = response_blob[offset:offset + rsp_size]
                    offset += rsp_size
                    try:
                        op.gather(chunk)
                    except Exception as e:
                        if not op.done():
                            op.set_exception(e)

            except Exception as e:
                # Fail all pending operations
                for op in operations:
                    if not op.done():
                        op.set_exception(e)

    # Public API methods:
    # - gpio_set_low/high, gpio_get_low/high, gpio_set, gpio_get, gpio_mask_set
    # - freq property (getter/setter)
    # - loopback_enable/disable
    # - three_phase_enable/disable
    # - adaptive_enable/disable
    # - wait_on_high/low
    # - drive_open_collector
    # - shift_out, shift_in, shift_in_out
    # - tms_shift
    # - send_immediate
```

**Key Implementation Notes:**

- **Byte mode vs Bit mode:**
  - Byte mode: `data: bytes`, operations handle up to 65536 bytes with length encoding
  - Bit mode: `data: tuple[int, int]` as `(value, bit_count)`, max 7 bits
  - Shift operations detect mode by type inspection

- **Batching:**
  - All public methods queue operations and return Futures immediately
  - Worker is scheduled via `asyncio.create_task()` on first queue
  - Awaiting any Future triggers flush (worker acquires lock, drains queue)

- **Error Handling:**
  - USB exceptions fail all pending operations
  - Individual operation `gather()` exceptions only fail that operation

---

### 4. stream.py

**Port from:** ausb `stream.py` with FTDI-specific modifications

```python
from ausb.stream import EndpointStreamReader
from ausb import exception
from .constant import Status

class FtdiStreamReader(EndpointStreamReader):
    """
    StreamReader for FTDI endpoints that handles 2-byte status headers.

    FTDI chips prepend a 2-byte modem status to every IN packet.
    This reader strips the status and makes it available separately.
    """

    def __init__(self, endpoint, buffer_limit=65536):
        super().__init__(endpoint, buffer_limit)
        self.last_status = Status(0)

    async def _background_reader(self):
        """Override to strip FTDI status header from each packet"""
        try:
            while not self._closed:
                await self._can_read_more.wait()

                if self._closed:
                    break

                try:
                    # Read full packet (includes 2-byte status)
                    packet = await self._endpoint.read()

                    if len(packet) >= 2:
                        # Extract status
                        self.last_status = Status(
                            int.from_bytes(packet[:2], "little"))

                        # Add data (sans status) to buffer
                        data = packet[2:]
                        if data:
                            self._buffer.extend(data)
                            self._data_available.set()

                        # Flow control
                        if len(self._buffer) >= self._buffer_limit:
                            self._can_read_more.clear()

                except exception.TransferError as e:
                    self._eof = True
                    self._exception = e
                    self._data_available.set()
                    break
                except exception.TransferTimeout:
                    # Timeout is not fatal, retry
                    pass
                except Exception as e:
                    self._eof = True
                    self._exception = e
                    self._data_available.set()
                    break

        except asyncio.CancelledError:
            pass
```

**Changes:**
- Inherit from `ausb.stream.EndpointStreamReader`
- Override `_background_reader()` to strip 2-byte status prefix
- Expose `last_status` property for modem status monitoring

**StreamWriter:** Use `ausb.stream.EndpointStreamWriter` directly without modifications.

---

### 5. eeprom.py

**Port from:** `eeprom.py`

```python
from .constant import ChipType

class Eeprom:
    """FTDI EEPROM read/write with checksum validation"""

    def __init__(self, ftdi):
        """
        :param ftdi: Ftdi instance
        """
        self.ftdi = ftdi
        self.data = None

    async def read(self):
        """
        Read EEPROM contents and detect actual size.

        Reads 256 words and detects actual EEPROM size (32/64/128/256 words)
        by checking for mirroring. Validates checksum.
        """
        data = []
        for loc in range(256):
            word = await self.ftdi.eeprom_word_read(loc)
            data.append(word)

        # Detect actual size by looking for mirroring
        if any(x != data[0] for x in data):
            while len(data) > 32:
                half = len(data) // 2
                if data[:half] != data[half:]:
                    break
                data = data[:half]

        if not self._checksum_is_valid(data):
            raise ValueError("EEPROM checksum invalid")

        self.data = data

    async def write(self):
        """
        Write EEPROM with automatic checksum calculation.

        Last word is automatically set to calculated checksum.
        """
        if self.data is None:
            raise RuntimeError("No data to write")

        if len(self.data) not in [32, 64, 128, 256]:
            raise ValueError(f"Invalid EEPROM size: {len(self.data)}")

        for index, value in enumerate(self.data):
            if index == len(self.data) - 1:
                # Last word is checksum
                value = self._checksum_calc(self.data[:-1])
            await self.ftdi.eeprom_word_write(index, value)

    def _checksum_calc(self, data):
        """
        Calculate FTDI EEPROM checksum.

        Algorithm: XOR-rotate with initial value 0xAAAA.
        FT230X has special handling for user area (0x12-0x3F).
        """
        chk = 0xaaaa
        for index, value in enumerate(data):
            # FT230X: skip user area in checksum
            if (self.ftdi.chip_type == ChipType.FT230X and
                0x12 <= index < 0x40):
                continue
            chk ^= value
            chk = ((chk << 1) | (chk >> 15)) & 0xffff
        return chk

    def _checksum_is_valid(self, data):
        """Validate EEPROM checksum"""
        return data[-1] == self._checksum_calc(data[:-1])
```

**Changes:**
- All methods are async
- Use `ftdi.eeprom_word_read/write()` instead of direct USB

---

### 6. __init__.py

```python
"""FTDI chip support for ausb"""

from .constant import (
    ChipType, Parity, StopBits, Bitmode, Interface,
    Status, MpsseIo, MpsseCmd,
    Request, ResetCtrl, ModemCtrl,
    FtdiError,
)
from .device import Ftdi, FtdiChannel
from .mpsse import (
    Mpsse, MpsseOperation,
    # Operation classes
    SetBitsLow, SetBitsHigh, GetBitsLow, GetBitsHigh,
    ClkDiv, ClkDiv5Enable, ClkDiv5Disable,
    LoopbackEnable, LoopbackDisable,
    ThreePhaseEnable, ThreePhaseDisable,
    AdaptiveEnable, AdaptiveDisable,
    WaitOnHigh, WaitOnLow,
    DriveOpenCollector,
    ShiftOut, ShiftIn, ShiftInOut, TmsShift,
    SendImmediate,
)
from .eeprom import Eeprom
from .stream import FtdiStreamReader

__all__ = [
    # Constants
    'ChipType', 'Parity', 'StopBits', 'Bitmode', 'Interface',
    'Status', 'MpsseIo', 'MpsseCmd',
    'Request', 'ResetCtrl', 'ModemCtrl',
    'FtdiError',
    # Device
    'Ftdi', 'FtdiChannel',
    # MPSSE
    'Mpsse', 'MpsseOperation',
    'SetBitsLow', 'SetBitsHigh', 'GetBitsLow', 'GetBitsHigh',
    'ClkDiv', 'ClkDiv5Enable', 'ClkDiv5Disable',
    'LoopbackEnable', 'LoopbackDisable',
    'ThreePhaseEnable', 'ThreePhaseDisable',
    'AdaptiveEnable', 'AdaptiveDisable',
    'WaitOnHigh', 'WaitOnLow',
    'DriveOpenCollector',
    'ShiftOut', 'ShiftIn', 'ShiftInOut', 'TmsShift',
    'SendImmediate',
    # EEPROM
    'Eeprom',
    # Stream
    'FtdiStreamReader',
]
```

---

## Implementation Order

1. **constant.py** - Straightforward port, no dependencies
2. **device.py** - Core functionality, uses ausb Device model
3. **stream.py** - Extends ausb StreamReader for FTDI status
4. **eeprom.py** - Simple, depends on device.py
5. **mpsse.py** - Most complex, depends on device.py
6. **__init__.py** - Exports

---

## Example Usage

### Basic FTDI Device Access

```python
import asyncio
import ausb
from ausb.util.ftdi import Ftdi, FtdiChannel, Bitmode, Interface

async def main():
    async with ausb.Context() as ctx:
        # Find FTDI device
        dev_desc = ctx.device_get(vendor_id=0x0403)

        # Open device
        dev_handle = dev_desc.open()

        # Create FTDI wrapper
        ftdi = await Ftdi.from_device(dev_handle)
        print(f"Chip type: {ftdi.chip_type}")

        # Open channel in reset mode
        channel = FtdiChannel(ftdi, Interface.A, mode=Bitmode.Reset)
        await channel.initialize()

asyncio.run(main())
```

### MPSSE GPIO Control

```python
import asyncio
import ausb
from ausb.util.ftdi import Ftdi, FtdiChannel, Mpsse, Bitmode, Interface

async def main():
    async with ausb.Context() as ctx:
        dev_desc = ctx.device_get(vendor_id=0x0403)
        dev_handle = dev_desc.open()
        ftdi = await Ftdi.from_device(dev_handle)

        # Open channel in MPSSE mode
        channel = FtdiChannel(ftdi, Interface.A, mode=Bitmode.Mpsse)
        await channel.initialize()

        # Create MPSSE engine with GPIO config
        mpsse = Mpsse(channel, gpio_oe=0xfb, gpio_value=0)

        # Queue operations (implicit batching)
        op1 = mpsse.gpio_set(3, True)   # Returns Future, queued
        op2 = mpsse.gpio_set(4, False)  # Returns Future, queued
        op3 = mpsse.gpio_get(0)         # Returns Future, queued

        # Await triggers flush of all pending operations
        result = await op3
        print(f"GPIO 0: {result}")

        # Set clock frequency
        mpsse.freq = 1e6  # 1 MHz
        await mpsse.send_immediate()  # Force flush

asyncio.run(main())
```

### MPSSE Data Shift

```python
# Byte-mode shift
write_data = b'\x01\x02\x03\x04'
op = mpsse.shift_in_out(write_data, write_neg=True, read_neg=False)
read_data = await op  # Returns bytes

# Bit-mode shift (max 7 bits)
write_bits = (0b1010101, 7)  # (value, bit_count)
op = mpsse.shift_in_out(write_bits, write_neg=True, read_neg=False)
read_bits = await op  # Returns (value, bit_count)
```

### EEPROM Access

```python
from ausb.util.ftdi import Eeprom

async def read_eeprom():
    async with ausb.Context() as ctx:
        dev_desc = ctx.device_get(vendor_id=0x0403)
        dev_handle = dev_desc.open()
        ftdi = await Ftdi.from_device(dev_handle)

        eeprom = Eeprom(ftdi)
        await eeprom.read()

        print(f"EEPROM size: {len(eeprom.data)} words")
        print(f"Data: {eeprom.data[:8]}")  # First 8 words

asyncio.run(read_eeprom())
```

### Stream I/O with FTDI

```python
from ausb.util.ftdi import FtdiStreamReader

async def stream_example():
    async with ausb.Context() as ctx:
        dev_desc = ctx.device_get(vendor_id=0x0403)
        dev_handle = dev_desc.open()
        ftdi = await Ftdi.from_device(dev_handle)

        channel = FtdiChannel(ftdi, Interface.A, mode=Bitmode.Syncff)
        await channel.initialize()

        # Create stream reader (strips FTDI status headers)
        reader = FtdiStreamReader(channel.ep_in, buffer_limit=131072)

        # Read data
        data = await reader.read(1024)
        print(f"Last modem status: {reader.last_status}")

        await reader.close()

asyncio.run(stream_example())
```

---

## Testing Strategy

### Unit Tests

1. **constant.py**: Verify enum values match FTDI specification
2. **device.py**:
   - Chip type detection with various bcdDevice values
   - Control request formatting
3. **mpsse.py**:
   - Operation serialization (`lower()` output)
   - Response parsing (`gather()` logic)
   - Batching behavior
4. **eeprom.py**: Checksum calculation for different chip types

### Integration Tests

Require actual FTDI hardware:

1. **Device detection**: Find and open FTDI device
2. **MPSSE GPIO**: Toggle pins, read back
3. **MPSSE clock**: Set various frequencies, verify
4. **MPSSE shift**: Loopback mode data verification
5. **EEPROM**: Read, validate checksum
6. **Stream**: Continuous data flow with status monitoring

### Mock Testing

Use `unittest.mock` to simulate:
- ausb Device handles
- USB control transfers
- Endpoint read/write

---

## Open Issues

### To Be Resolved During Implementation

1. **Endpoint address calculation:** Verify FTDI endpoint addressing for multi-interface devices
2. **Error recovery:** Strategy for handling partial batch failures
3. **StreamWriter:** Confirm no FTDI-specific requirements (currently assuming standard ausb StreamWriter works)
4. **Timeout handling:** Verify ausb timeout model matches requirements

### Future Enhancements (Out of Scope)

1. **Protocol interfaces:** JTAG, SWD, I2C, SPI, Chipcon adapters
2. **High-level abstractions:** Protocol-agnostic transaction APIs
3. **EEPROM templating:** Helper functions for common EEPROM configurations
4. **Bitbang modes:** Support for non-MPSSE bitmodes

---

## References

- **FTDI MPSSE Basics:** [AN_108 Command Processor for MPSSE and MCU Host Bus Emulation Modes](https://www.ftdichip.com/Support/Documents/AppNotes/AN_108_Command_Processor_for_MPSSE_and_MCU_Host_Bus_Emulation_Modes.pdf)
- **ausb Documentation:** `/Users/nipo/projects/ausb/docs/`
- **Original Code:** `/Users/nipo/projects/crobe-wip/crobe/adapter/ftdi/`

---

## Revision History

| Date       | Version | Changes |
|------------|---------|---------|
| 2025-12-04 | 1.0     | Initial plan |
