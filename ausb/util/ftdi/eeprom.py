"""FTDI EEPROM read/write with checksum validation"""

from .constant import ChipType


class Eeprom:
    """
    FTDI EEPROM read/write with automatic size detection and checksum validation.

    FTDI chips have internal EEPROM for configuration (VID/PID, strings, channel
    settings, etc.). This class provides async read/write with:
    - Automatic size detection (32/64/128/256 words)
    - Checksum validation
    - Chip-specific checksum algorithms
    """

    def __init__(self, ftdi):
        """
        Create EEPROM accessor.

        :param ftdi: Ftdi instance
        """
        self.ftdi = ftdi
        self.data = None

    async def read(self):
        """
        Read EEPROM contents and detect actual size.

        Reads up to 256 words and detects actual EEPROM size by checking
        for mirroring (smaller EEPROMs repeat their contents at higher
        addresses). Validates checksum before accepting data.

        :raises ValueError: If checksum validation fails
        """
        data = []
        for loc in range(256):
            word = await self.ftdi.eeprom_word_read(loc)
            data.append(word)

        # Detect actual size by looking for mirroring
        # Small EEPROMs (32/64 words) mirror at higher addresses
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
        Must call read() first or manually populate self.data.

        :raises RuntimeError: If no data to write (call read() first)
        :raises ValueError: If data size is invalid
        """
        if self.data is None:
            raise RuntimeError("No data to write (call read() first)")

        if len(self.data) not in [32, 64, 128, 256]:
            raise ValueError(f"Invalid EEPROM size: {len(self.data)} (must be 32/64/128/256)")

        for index, value in enumerate(self.data):
            if index == len(self.data) - 1:
                # Last word is checksum
                value = self._checksum_calc(self.data[:-1])
            await self.ftdi.eeprom_word_write(index, value)

    def _checksum_calc(self, data):
        """
        Calculate FTDI EEPROM checksum.

        Algorithm: XOR-rotate with initial value 0xAAAA.
        FT230X has special handling - user area (0x12-0x3F) is excluded
        from checksum calculation.

        :param data: List of 16-bit words (excluding checksum word)
        :returns: 16-bit checksum value
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
        """
        Validate EEPROM checksum.

        :param data: Complete EEPROM data including checksum as last word
        :returns: True if checksum matches
        """
        return data[-1] == self._checksum_calc(data[:-1])
