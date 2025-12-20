"""FTDI MPSSE async operation engine"""

import asyncio
from typing import Tuple
from collections import deque
from .constant import MpsseCmd, MpsseIo, ChipType
from .device import Ftdi, Channel

# ============================================================================
# Base Operation Class
# ============================================================================

class MpsseOperation(asyncio.Future):
    """
    Base class for MPSSE operations.

    Operations are asyncio Futures that can be awaited. They implement:
    - lower(): Serialize to MPSSE command bytes
    - gather(): Parse response bytes and resolve the future
    """

    def lower(self) -> bytes:
        """
        Serialize operation to MPSSE command bytes.

        :returns: (command_bytes, expected_response_size) tuple
        """
        raise NotImplementedError

    def gather(self, response: bytes):
        """
        Parse response bytes and resolve future.

        Should call self.set_result() or self.set_exception().

        :param response: Response bytes from FTDI
        """
        raise NotImplementedError


# ============================================================================
# GPIO Operations
# ============================================================================

class SetBitsLow(MpsseOperation):
    """Set low byte GPIO (pins 0-7)"""

    def __init__(self, value: int, oe: int):
        super().__init__()
        self.value = value & 0xff
        self.oe = oe & 0xff

    def lower(self) -> bytes:
        return bytes([MpsseCmd.SetBitsLow, self.value, self.oe]), 0

    def gather(self, response: bytes):
        self.set_result(None)


class SetBitsHigh(MpsseOperation):
    """Set high byte GPIO (pins 8-15)"""

    def __init__(self, value: int, oe: int):
        super().__init__()
        self.value = value & 0xff
        self.oe = oe & 0xff

    def lower(self) -> bytes:
        return bytes([MpsseCmd.SetBitsHigh, self.value, self.oe]), 0

    def gather(self, response: bytes):
        self.set_result(None)


class GetBitsLow(MpsseOperation):
    """Get low byte GPIO (pins 0-7)"""

    def lower(self) -> bytes:
        return bytes([MpsseCmd.GetBitsLow]), 1

    def gather(self, response: bytes):
        self.set_result(response[0])


class GetBitsHigh(MpsseOperation):
    """Get high byte GPIO (pins 8-15)"""

    def lower(self) -> bytes:
        return bytes([MpsseCmd.GetBitsHigh]), 1

    def gather(self, response: bytes):
        self.set_result(response[0])


# ============================================================================
# Clock Configuration
# ============================================================================

class ClkDiv(MpsseOperation):
    """Set clock divisor"""

    def __init__(self, divisor: int):
        super().__init__()
        self.divisor = divisor & 0xffff

    def lower(self) -> bytes:
        return bytes([MpsseCmd.ClkDiv]) + self.divisor.to_bytes(2, 'little'), 0

    def gather(self, response: bytes):
        self.set_result(None)


class ClkDiv5Enable(MpsseOperation):
    """Enable divide-by-5 clock prescaler (FT2232H/FT4232H/FT232H only)"""

    def lower(self) -> bytes:
        return bytes([MpsseCmd.ClkDiv5Enable]), 0

    def gather(self, response: bytes):
        self.set_result(None)


class ClkDiv5Disable(MpsseOperation):
    """Disable divide-by-5 clock prescaler"""

    def lower(self) -> bytes:
        return bytes([MpsseCmd.ClkDiv5Disable]), 0

    def gather(self, response: bytes):
        self.set_result(None)


# ============================================================================
# Loopback
# ============================================================================

class LoopbackEnable(MpsseOperation):
    """Enable loopback mode (TDO connected to TDI internally)"""

    def lower(self) -> bytes:
        return bytes([MpsseCmd.LoopbackEnable]), 0

    def gather(self, response: bytes):
        self.set_result(None)


class LoopbackDisable(MpsseOperation):
    """Disable loopback mode"""

    def lower(self) -> bytes:
        return bytes([MpsseCmd.LoopbackDisable]), 0

    def gather(self, response: bytes):
        self.set_result(None)


# ============================================================================
# Three-Phase Clocking
# ============================================================================

class ThreePhaseEnable(MpsseOperation):
    """Enable three-phase clocking (for I2C)"""

    def lower(self) -> bytes:
        return bytes([MpsseCmd.ThreePhaseEnable]), 0

    def gather(self, response: bytes):
        self.set_result(None)


class ThreePhaseDisable(MpsseOperation):
    """Disable three-phase clocking"""

    def lower(self) -> bytes:
        return bytes([MpsseCmd.ThreePhaseDisable]), 0

    def gather(self, response: bytes):
        self.set_result(None)


# ============================================================================
# Adaptive Clocking
# ============================================================================

class AdaptiveEnable(MpsseOperation):
    """Enable adaptive clocking (wait for clock stretching)"""

    def lower(self) -> bytes:
        return bytes([MpsseCmd.AdaptiveEnable]), 0

    def gather(self, response: bytes):
        self.set_result(None)


class AdaptiveDisable(MpsseOperation):
    """Disable adaptive clocking"""

    def lower(self) -> bytes:
        return bytes([MpsseCmd.AdaptiveDisable]), 0

    def gather(self, response: bytes):
        self.set_result(None)


# ============================================================================
# Wait Operations
# ============================================================================

class WaitOnHigh(MpsseOperation):
    """Wait until I/O goes high"""

    def lower(self) -> bytes:
        return bytes([MpsseCmd.WaitOnHigh]), 0

    def gather(self, response: bytes):
        self.set_result(None)


class WaitOnLow(MpsseOperation):
    """Wait until I/O goes low"""

    def lower(self) -> bytes:
        return bytes([MpsseCmd.WaitOnLow]), 0

    def gather(self, response: bytes):
        self.set_result(None)


# ============================================================================
# Drive Mode
# ============================================================================

class DriveOpenCollector(MpsseOperation):
    """Configure open-collector drive mode (FT232H only)"""

    def __init__(self, low_pins: int, high_pins: int):
        super().__init__()
        self.low = low_pins & 0xff
        self.high = high_pins & 0xff

    def lower(self) -> bytes:
        return bytes([MpsseCmd.DriveOpenCollector, self.low, self.high]), 0

    def gather(self, response: bytes):
        self.set_result(None)


# ============================================================================
# Control
# ============================================================================

class SendImmediate(MpsseOperation):
    """Force FTDI to flush internal buffer immediately"""

    def lower(self) -> bytes:
        return bytes([MpsseCmd.SendImmediate]), 0

    def gather(self, response: bytes):
        self.set_result(None)


# ============================================================================
# Data Shift Operations
# ============================================================================

class ShiftOut(MpsseOperation):
    """
    Shift data out (write-only, no read).

    Data format:
    - bytes: Byte mode (multiples of 8 bits)
    - (value, bit_count): Bit mode (1-7 bits)
    """

    def __init__(self,
                 data: bytes,
                 write_neg: bool = True,
                 lsb_first: bool = True):
        super().__init__()
        self.data = data
        self.write_neg = write_neg
        self.lsb_first = lsb_first

    def lower(self) -> bytes:
        cmd = MpsseIo.Write
        if self.write_neg:
            cmd |= MpsseIo.WriteNeg
        if self.lsb_first:
            cmd |= MpsseIo.LsbFirst

        if isinstance(self.data, bytes):
            # Byte mode
            ret = bytearray()
            for offset in range(0, len(self.data), 65536):
                chunk = self.data[offset:offset + 65536]
                length = len(chunk) - 1
                ret.extend([cmd, length & 0xff, (length >> 8) & 0xff])
                ret.extend(chunk)
            return bytes(ret), 0
        else:
            # Bit mode (value, bit_count)
            value, bit_count = self.data
            assert 1 <= bit_count <= 7, "Bit count must be 1-7"
            cmd |= MpsseIo.Bits
            return bytes([cmd, bit_count - 1, value & 0x7f]), 0

    def gather(self, response: bytes):
        self.set_result(None)


class ShiftIn(MpsseOperation):
    """
    Shift data in (read-only, no write).

    Length format:
    - int: Byte count
    - (bit_count,): Bit mode (1-7 bits)
    """

    def __init__(self,
                 length: int,
                 read_neg: bool = False,
                 lsb_first: bool = True):
        super().__init__()
        self.length = length
        self.read_neg = read_neg
        self.lsb_first = lsb_first

    def lower(self) -> bytes:
        cmd = MpsseIo.Read
        if self.read_neg:
            cmd |= MpsseIo.ReadNeg
        if self.lsb_first:
            cmd |= MpsseIo.LsbFirst

        if isinstance(self.length, int):
            # Byte mode
            ret = bytearray()
            response_size = 0
            for offset in range(0, self.length, 65536):
                chunk_len = min(65536, self.length - offset)
                length_param = chunk_len - 1
                ret.extend([cmd, length_param & 0xff, (length_param >> 8) & 0xff])
                response_size += chunk_len
            return bytes(ret), response_size
        else:
            # Bit mode (bit_count,)
            bit_count = self.length[0]
            assert 1 <= bit_count <= 7, "Bit count must be 1-7"
            cmd |= MpsseIo.Bits
            return bytes([cmd, bit_count - 1]), 1

    def gather(self, response: bytes):
        if isinstance(self.length, int):
            # Byte mode - return bytes
            self.set_result(response: bytes)
        else:
            # Bit mode - return (value, bit_count)
            bit_count = self.length[0]
            value = response[0] >> (8 - bit_count)
            self.set_result((value, bit_count))


class ShiftInOut(MpsseOperation):
    """
    Shift data in and out simultaneously.

    Data format:
    - bytes: Byte mode
    - (value, bit_count): Bit mode (1-7 bits)
    """

    def __init__(self,
                 data: bytes,
                 write_neg: bool = True,
                 read_neg: bool = False,
                 lsb_first: bool = True):
        super().__init__()
        self.data = data
        self.write_neg = write_neg
        self.read_neg = read_neg
        self.lsb_first = lsb_first

    def lower(self) -> bytes:
        cmd = MpsseIo.Write | MpsseIo.Read
        if self.write_neg:
            cmd |= MpsseIo.WriteNeg
        if self.read_neg:
            cmd |= MpsseIo.ReadNeg
        if self.lsb_first:
            cmd |= MpsseIo.LsbFirst

        if isinstance(self.data, bytes):
            # Byte mode
            ret = bytearray()
            response_size = 0
            for offset in range(0, len(self.data), 65536):
                chunk = self.data[offset:offset + 65536]
                length = len(chunk) - 1
                ret.extend([cmd, length & 0xff, (length >> 8) & 0xff])
                ret.extend(chunk)
                response_size += len(chunk)
            return bytes(ret), response_size
        else:
            # Bit mode (value, bit_count)
            value, bit_count = self.data
            assert 1 <= bit_count <= 7, "Bit count must be 1-7"
            cmd |= MpsseIo.Bits
            return bytes([cmd, bit_count - 1, value & 0x7f]), 1

    def gather(self, response: bytes):
        if isinstance(self.data, bytes):
            # Byte mode - return bytes
            self.set_result(response: bytes)
        else:
            # Bit mode - return (value, bit_count)
            bit_count = self.data[1]
            value = response[0] >> (8 - bit_count)
            self.set_result((value, bit_count))


class TmsShift(MpsseOperation):
    """
    TMS shift operation (bit mode only, max 7 bits).

    Used for JTAG TAP state machine transitions.
    """

    def __init__(self,
                 tms_bits: Tuple[int, int],
                 tdi: int = 0,
                 read_tdo: bool = False,
                 write_neg: bool = True,
                 lsb_first: bool = True):
        super().__init__()
        self.tms_value, self.bit_count = tms_bits
        assert 1 <= self.bit_count <= 7, "TMS bit count must be 1-7"
        self.tdi = int(bool(tdi))
        self.read_tdo = read_tdo
        self.write_neg = write_neg
        self.lsb_first = lsb_first

    def lower(self) -> bytes:
        cmd = MpsseIo.Tms | MpsseIo.Bits
        if self.write_neg:
            cmd |= MpsseIo.WriteNeg
        if self.lsb_first:
            cmd |= MpsseIo.LsbFirst
        if self.read_tdo:
            cmd |= MpsseIo.Read

        data_byte = (self.tms_value & 0x7f) | (self.tdi << 7)
        response_size = 1 if self.read_tdo else 0

        return bytes([cmd, self.bit_count - 1, data_byte]), response_size

    def gather(self, response: bytes):
        if self.read_tdo:
            value = response[0] >> (8 - self.bit_count)
            self.set_result((value, self.bit_count))
        else:
            self.set_result(None)


# ============================================================================
# MPSSE Engine
# ============================================================================

class Mpsse:
    """
    MPSSE async operation engine with implicit batching.

    Operations are queued when methods are called. Awaiting any operation
    triggers flush of all pending operations in a single USB transaction.

    Example:
        op1 = mpsse.gpio_set(3, True)   # Queued
        op2 = mpsse.gpio_set(4, False)  # Queued
        result = await op1               # Flushes both ops
    """

    def __init__(self,
                 channel: FtdiChannel,
                 gpio_oe: int = 0,
                 gpio_value : int =0):
        """
        Create MPSSE engine.

        :param channel: FtdiChannel in MPSSE mode
        :param gpio_oe: Initial GPIO output enable mask (16-bit)
        :param gpio_value: Initial GPIO value (16-bit)
        """
        self.channel = channel
        self._pending = deque()
        self._flush_lock = asyncio.Lock()
        self._next_worker = None

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

    def _queue(self, op: MpsseOperation) -> asyncio.Future:
        """
        Queue operation and schedule worker.

        :param op: MpsseOperation instance
        :returns: The operation (for awaiting)
        """
        self._pending.append(op)
        self._schedule_worker()
        return op

    def _schedule_worker(self):
        """Schedule worker coroutine if not already scheduled"""
        if not self._worker and self._pending:
            self._next_worker = asyncio.create_task(self._flush_worker())

    async def _flush_worker(self):
        """
        Flush all pending operations.

        Serializes all queued operations, executes single USB I/O,
        distributes responses, and resolves futures.
        """
        async with self._flush_lock:
            self._next_worker = None

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

            # Add SendImmediate to force FTDI flush
            commands.append(bytes([MpsseCmd.SendImmediate]))

            # Execute I/O
            try:
                await self.channel.write(b''.join(commands))

                total_response = sum(response_sizes)
                if total_response > 0:
                    response_blob = await self.channel.read(total_response: bytes)
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

    # ========================================================================
    # Public API - GPIO
    # ========================================================================

    def gpio_set_low(self, value: int, oe: int) -> asyncio.Future:
        """
        Set low byte GPIO (pins 0-7).

        :param value: Pin values (bit 0 = pin 0, etc.)
        :param oe: Output enable mask
        :returns: Awaitable operation
        """
        self._gpio_value = (self._gpio_value & 0xff00) | (value & 0xff)
        self._gpio_oe = (self._gpio_oe & 0xff00) | (oe & 0xff)
        return self._queue(SetBitsLow(value, oe))

    def gpio_set_high(self, value: int, oe: int) -> asyncio.Future:
        """
        Set high byte GPIO (pins 8-15).

        :param value: Pin values (bit 0 = pin 8, etc.)
        :param oe: Output enable mask
        :returns: Awaitable operation
        """
        self._gpio_value = (self._gpio_value & 0x00ff) | ((value & 0xff) << 8)
        self._gpio_oe = (self._gpio_oe & 0x00ff) | ((oe & 0xff) << 8)
        return self._queue(SetBitsHigh(value, oe))

    def gpio_get_low(self) -> asyncio.Future:
        """
        Get low byte GPIO (pins 0-7).

        :returns: Awaitable operation that resolves to byte value
        """
        return self._queue(GetBitsLow())

    def gpio_get_high(self) -> asyncio.Future:
        """
        Get high byte GPIO (pins 8-15).

        :returns: Awaitable operation that resolves to byte value
        """
        return self._queue(GetBitsHigh())

    def gpio_set(self, pin: int, value: int) -> asyncio.Future:
        """
        Set single GPIO pin.

        :param pin: Pin number (0-15)
        :param value: True for high, False for low
        :returns: Awaitable operation
        """
        mask = 1 << pin
        new_oe = self._gpio_oe | mask
        new_value = (self._gpio_value & ~mask) | (mask if value else 0)
        return self.gpio_mask_set(mask, new_oe, new_value)

    def gpio_mask_set(self, change_mask: int, oe: int, value: int) -> asyncio.Future:
        """
        Set multiple GPIO pins by mask.

        :param change_mask: Bits to modify
        :param oe: Output enable for changed bits
        :param value: Values for changed bits
        :returns: Awaitable operation (or gather of multiple ops)
        """
        self._gpio_oe = (self._gpio_oe & ~change_mask) | (change_mask & oe)
        self._gpio_value = (self._gpio_value & ~change_mask) | (change_mask & value)

        ops = []
        if change_mask & 0xff:
            ops.append(self.gpio_set_low(self._gpio_value & 0xff, self._gpio_oe & 0xff))
        if change_mask & 0xff00:
            ops.append(self.gpio_set_high(self._gpio_value >> 8, self._gpio_oe >> 8))

        return asyncio.gather(*ops) if len(ops) > 1 else ops[0]

    def gpio_get(self, pin: int) -> asyncio.Future:
        """
        Get single GPIO pin value.

        :param pin: Pin number (0-15)
        :returns: Awaitable task that resolves to bool
        """
        op = self.gpio_get_high() if pin >= 8 else self.gpio_get_low()

        async def _extract_bit():
            value = await op
            return bool(value & (1 << (pin & 7)))

        return asyncio.create_task(_extract_bit())

    # ========================================================================
    # Public API - Clock
    # ========================================================================

    def freq_get(self) -> int:
        """
        Current MPSSE clock frequency.

        :returns: Frequency in Hz
        """
        div5, div = self._divisor
        r = self.base_freq / (div + 1) / 2  # MPSSE cycle = 2 base clocks
        if div5:
            r /= 5
        return r

    def freq_set(self, freq: int) -> asyncio.Future:
        """
        Set MPSSE clock frequency.

        Queues clock configuration operations.

        :param freq: Target frequency in Hz
        """
        cycles = freq * 2
        div5 = self.can_div5 and cycles < self.base_freq / 5

        if div5:
            div = self.base_freq / cycles / 5 - 1
        else:
            div = self.base_freq / cycles - 1

        div = min(max(int(div), 0), 0xffff)
        self._divisor = (div5, div)

        if self.can_div5:
            self._queue(ClkDiv5Enable() if div5 else ClkDiv5Disable())
        return self._queue(ClkDiv(div))

    # ========================================================================
    # Public API - Loopback
    # ========================================================================

    def loopback_enable(self) -> asyncio.Future:
        """Enable loopback mode (TDO->TDI internally)"""
        return self._queue(LoopbackEnable())

    def loopback_disable(self) -> asyncio.Future:
        """Disable loopback mode"""
        return self._queue(LoopbackDisable())

    # ========================================================================
    # Public API - Three-Phase / Adaptive
    # ========================================================================

    def three_phase_enable(self) -> asyncio.Future:
        """Enable three-phase clocking (for I2C)"""
        return self._queue(ThreePhaseEnable())

    def three_phase_disable(self) -> asyncio.Future:
        """Disable three-phase clocking"""
        return self._queue(ThreePhaseDisable())

    def adaptive_enable(self) -> asyncio.Future:
        """Enable adaptive clocking (clock stretching)"""
        return self._queue(AdaptiveEnable())

    def adaptive_disable(self) -> asyncio.Future:
        """Disable adaptive clocking"""
        return self._queue(AdaptiveDisable())

    # ========================================================================
    # Public API - Wait
    # ========================================================================

    def wait_on_high(self) -> asyncio.Future:
        """Wait until I/O signal goes high"""
        return self._queue(WaitOnHigh())

    def wait_on_low(self) -> asyncio.Future:
        """Wait until I/O signal goes low"""
        return self._queue(WaitOnLow())

    # ========================================================================
    # Public API - Drive Mode
    # ========================================================================

    def drive_open_collector(self, low_pins, high_pins) -> asyncio.Future:
        """
        Configure open-collector drive mode (FT232H only).

        :param low_pins: Low byte open-collector mask
        :param high_pins: High byte open-collector mask
        """
        return self._queue(DriveOpenCollector(low_pins, high_pins))

    # ========================================================================
    # Public API - Data Shift
    # ========================================================================

    def shift_out(self, data, write_neg=True, lsb_first=True) -> asyncio.Future:
        """
        Shift data out (write-only).

        :param data: bytes for byte-mode, or (value, bit_count) for bit-mode
        :param write_neg: Clock data on negative edge
        :param lsb_first: LSB-first bit order
        :returns: Awaitable operation
        """
        return self._queue(ShiftOut(data, write_neg, lsb_first))

    def shift_in(self, length, read_neg=False, lsb_first=True) -> asyncio.Future:
        """
        Shift data in (read-only).

        :param length: int for byte-mode, or (bit_count,) for bit-mode
        :param read_neg: Clock data on negative edge
        :param lsb_first: LSB-first bit order
        :returns: Awaitable operation that resolves to read data
        """
        return self._queue(ShiftIn(length, read_neg, lsb_first))

    def shift_in_out(self, data, write_neg=True, read_neg=False, lsb_first=True) -> asyncio.Future:
        """
        Shift data in and out simultaneously.

        :param data: bytes for byte-mode, or (value, bit_count) for bit-mode
        :param write_neg: Clock write data on negative edge
        :param read_neg: Clock read data on negative edge
        :param lsb_first: LSB-first bit order
        :returns: Awaitable operation that resolves to read data
        """
        return self._queue(ShiftInOut(data, write_neg, read_neg, lsb_first))

    def tms_shift(self, tms_bits, tdi=0, read_tdo=False, write_neg=True, lsb_first=True) -> asyncio.Future:
        """
        TMS shift operation (JTAG TAP state transitions).

        :param tms_bits: (tms_value, bit_count) where 1 ≤ bit_count ≤ 7
        :param tdi: TDI value (0 or 1) for all bits
        :param read_tdo: Whether to read TDO
        :param write_neg: Clock on negative edge
        :param lsb_first: LSB-first bit order
        :returns: Awaitable operation
        """
        return self._queue(TmsShift(tms_bits, tdi, read_tdo, write_neg, lsb_first))

    def send_immediate(self) -> asyncio.Future:
        """Force FTDI to flush its internal buffer"""
        return self._queue(SendImmediate())
