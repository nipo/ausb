"""FTDI device and channel handles"""

from .constant import ChipType, Request, ResetCtrl, Bitmode, Status


class Ftdi:
    """
    FTDI device wrapper with chip detection and control.

    Wraps an ausb Device handle and provides FTDI-specific functionality
    including chip type detection and EEPROM access.
    """

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
        Create FTDI wrapper around ausb Device handle.

        :param device_handle: ausb Device handle (from descriptor.open())
        """
        self.device = device_handle
        self.chip_type = self._detect_chip_type()

    def _detect_chip_type(self) -> ChipType:
        """
        Detect chip type from bcdDevice descriptor.

        Uses device descriptor's bcdDevice field and iSerialNumber index
        to determine the specific FTDI chip type.

        :returns: ChipType enum value
        """
        bcd = self.device.descriptor.bcd_device
        isn = self.device.descriptor.serial_number_index

        # Special case: FT232AM vs FT232BM disambiguation
        if bcd == 0x0200 and isn == 0:
            return ChipType.FT232BM

        return self.CHIP_TYPE_LUT.get(bcd)

    @classmethod
    async def from_device(cls, device_handle):
        """
        Factory method: create and initialize FTDI wrapper.

        :param device_handle: ausb Device handle
        :returns: Initialized Ftdi instance
        """
        ftdi = cls(device_handle)
        await ftdi.reset()
        return ftdi

    async def reset(self, target=ResetCtrl.All):
        """
        Reset device or buffers via vendor control request.

        :param target: ResetCtrl value (All, PurgeOut, or PurgeIn)
        """
        await self.device.vendor_control(Request.Reset, target, 0, b'')

    async def eeprom_word_read(self, index: int) -> int:
        """
        Read single EEPROM word (16-bit).

        :param index: Word address (0-255)
        :returns: 16-bit word value
        """
        r = await self.device.vendor_control(Request.ReadEeprom, 0, index, 2)
        return int.from_bytes(r, "little")

    async def eeprom_word_write(self, index: int, value: int):
        """
        Write single EEPROM word (16-bit).

        :param index: Word address (0-255)
        :param value: 16-bit word value
        """
        await self.device.vendor_control(Request.WriteEeprom, value, index, b'')


class FtdiChannel:
    """
    FTDI channel (interface) with bitmode and endpoint management.

    Represents one physical channel on an FTDI chip. Multi-channel chips
    (FT2232, FT4232) have multiple independent channels.
    """

    def __init__(self, ftdi, interface_no, mode=Bitmode.Reset):
        """
        Create FTDI channel handle.

        :param ftdi: Ftdi instance
        :param interface_no: Interface number (0=A, 1=B, 2=C, 3=D)
        :param mode: Bitmode to set after initialization
        """
        self.ftdi = ftdi
        self.device = ftdi.device
        self.interface_no = interface_no
        self.mode = mode

        # Claim interface
        self.interface = self.device.interface_claim(interface_no)

        # Get bulk endpoints
        # FTDI endpoint addresses: Interface A: 0x81/0x02, Interface B: 0x83/0x04, etc.
        in_addr = 0x81 + (interface_no * 2)
        out_addr = 0x02 + (interface_no * 2)

        in_ep_desc = self.interface.descriptor.endpoint_by_address(in_addr)
        out_ep_desc = self.interface.descriptor.endpoint_by_address(out_addr)

        self.ep_in = self.interface.open(in_ep_desc)
        self.ep_out = self.interface.open(out_ep_desc)

        # FTDI-specific state
        self.status = Status(0)

    async def initialize(self):
        """
        Initialize channel for configured mode.

        Performs standard initialization sequence:
        1. Reset to default bitmode
        2. Flush endpoint buffers
        3. Set latency timer to 2ms
        4. Set target bitmode if not Reset
        """
        await self.bitmode_set(Bitmode.Reset)
        await self.flush_buffers()
        await self.latency_timer_set(2)

        if self.mode != Bitmode.Reset:
            await self.bitmode_set(self.mode)

    async def bitmode_set(self, mode, gpio_oe=0):
        """
        Set bitmode and GPIO output enable.

        :param mode: Bitmode enum value
        :param gpio_oe: GPIO output enable mask (low byte, pins 0-7)
        """
        await self.device.vendor_control(
            Request.SetBitmode,
            (mode << 8) | gpio_oe,
            self.interface_no + 1,  # FTDI uses 1-based indexing for wIndex
            b'')

    async def latency_timer_set(self, timer):
        """
        Set latency timer (1-255 ms).

        Lower values reduce latency but increase USB overhead.
        Default is typically 16ms. MPSSE applications typically use 2ms.

        :param timer: Latency in milliseconds (1-255)
        """
        await self.device.vendor_control(
            Request.SetLatencyTimer,
            timer,
            self.interface_no + 1,
            b'')

    async def flush_buffers(self):
        """Flush both IN and OUT endpoint buffers."""
        await self.device.vendor_control(
            Request.Reset, ResetCtrl.PurgeOut,
            self.interface_no + 1, b'')
        await self.device.vendor_control(
            Request.Reset, ResetCtrl.PurgeIn,
            self.interface_no + 1, b'')

    async def write(self, data: bytes):
        """
        Raw write to OUT endpoint.

        :param data: Data to write
        """
        await self.ep_out.write(data)

    async def read(self, size: int) -> tuple[bytes, Status]:
        """
        Raw read from IN endpoint with status extraction.

        FTDI prepends 2-byte modem status to every IN packet.
        This method strips the status and returns it separately.

        :param size: Number of data bytes to read (excluding 2-byte status header)
        :returns: (data, status) tuple
        """
        packet = await self.ep_in.read(size + 2)
        status = Status(int.from_bytes(packet[:2], "little"))
        self.status = status
        return packet[2:], status
