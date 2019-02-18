import asyncio
import enum
import struct

class FirmwareImage:
    def __init__(self):
        self.segments = []
        self.entry_point = None

    @classmethod
    def from_file(cls, filename):
        """Load a Program from a Cypress FX image file"""
        if filename.endswith(".img.gz"):
            import gzip
            open_ = gzip.open
        else:
            open_ = open

        with open(filename, 'rb') as fd:
            header, ctl, typ = struct.unpack("2sBB", fd.read(4))
            if header != b"CY":
                raise ValueError("Bad file header")

            self = cls()

            chk = 0

            while True:
                ch = fd.read(8)
                size, address = struct.unpack("<LL", ch)
                if size == 0:
                    self.entry_point = address
                    break
                blob = fd.read(size * 4)
                self.segments.append((address, blob))
                chk += sum(struct.unpack("<%dL" % (len(blob) // 4), blob))

            checksum, = struct.unpack("<L", fd.read(4))

            if checksum != chk & 0xffffffff:
                raise ValueError("Bad file checksum")

            return self

    def __iter__(self):
        return iter(self.segments)
        
class Fx:
    def __init__(self, handle):
        self.handle = handle

    CTRL_MAX_PACKET_SIZE = 4096

    async def mem_rw(self, addr, data_or_length):
        return await self.handle.vendor_control(
            0xa0, addr & 0xffff, addr >> 16, data_or_length)
    
    async def memory_upload(self, segments):
        for base_address, data in segments:
            off = 0
            for off in range(0, len(data), self.CTRL_MAX_PACKET_SIZE):
                addr = base_address + off
                chunk = data[off : off + self.CTRL_MAX_PACKET_SIZE]

                await self.mem_rw(addr, chunk)
                readback = await self.mem_rw(addr, len(chunk))

                if readback == chunk:
                    continue

                raise RuntimeError("Bad readback data")

class Fx2(Fx):
    async def cpu_control(self, *, enabled = False):
        await self.mem_rw(0xe600, bytes([int(enabled)]))

    async def firmware_load(self, firmware):
        self.handle.configuration = 0
        await self.cpu_control(enabled = False)
        await self.memory_upload(firmware.segments)
        await self.cpu_control(enabled = true)
        

class Fx3(Fx):
    async def bootloader_revision_read(self):
        return await self.mem_rw(0xffff0020, 4)

    async def jump_to(self, addr):
        await self.mem_rw(addr, b'')

    async def firmware_load(self, firmware):
        await self.memory_upload(firmware.segments)
        await self.jump_to(firmware.entry_point)
        await asyncio.sleep(.6)
        
