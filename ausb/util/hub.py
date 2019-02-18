import struct
from ..exception import *
from ..constant import *
import enum

class HubClassRequest(enum.IntEnum):
    GetStatus = 0
    ClearFeature = 1
    GetState = 2
    SetFeature = 3
    GetDescriptor = 6
    SetDescriptor = 7
    ClearTtBuffer = 8
    ResetTt = 9
    GetTtState = 10
    StopTt = 11

class HubClassFeature(enum.IntEnum):
    LocalPower = 0
    OverCurrent = 1

class HubPortFeature(enum.IntEnum):
    Connection       = 0
    Enable           = 1
    Suspend          = 2
    OverCurrent      = 3
    Reset            = 4
    Power            = 8
    LowSpeed         = 9
    CPortConnection  = 16
    CPortEnable      = 17
    CPortSuspend     = 18
    CPortOverCurrent = 19
    CPortReset       = 20
    Test             = 21
    Indicator        = 22

class HubStatus(enum.IntFlag):
    LocalPowerSource = 0x0001
    OverCurrent      = 0x0002

class PortStatus(enum.IntFlag):
    CurrentConnection = 0x0001
    Enable            = 0x0002
    Suspend           = 0x0004
    OverCurrent       = 0x0008
    Reset             = 0x0010
    Power             = 0x0100
    LowSpeed          = 0x0200
    HighSpeed         = 0x0400
    TestMode          = 0x0800
    Indicator         = 0x1000

class DescriptorType(enum.IntEnum):
    Hub = 0x0029
    SsHub = 0x002a
    
class Port:
    def __init__(self, hub, index, removable):
        self.hub = hub
        self.index = index
        self.removable = removable
        self.ports = self.hub.handle.descriptor.ports + [index]
    
    async def feature_clear(self, feature):
        await self.hub.handle.control(RequestTypeType.Class,
                                  RequestTypeRecipient.Other,
                                  Request.ClearFeature, feature, self.index, b'')

    async def feature_set(self, feature):
        await self.hub.handle.control(RequestTypeType.Class,
                                  RequestTypeRecipient.Other,
                                  Request.SetFeature, feature, self.index, b'')

    async def status_get(self):
        st = await self.hub.handle.control(RequestTypeType.Class,
                                       RequestTypeRecipient.Other,
                                       Request.GetStatus, 0, self.index, 4)
        ps, cs = struct.unpack("<HH", st)
        return PortStatus(ps), PortStatus(cs)

class Hub:
    def __init__(self, handle):
        self.handle = handle

    @classmethod
    async def create(cls, handle):
        self = cls(handle)
        await self._init()
        return self
        
    async def _init(self):
        try:
            desc = await self.descriptor_get_std(0)
        except TransferStalled:
            raise NotImplementedError()

        l, t, port_count, car, pwr, cont = struct.unpack("<BBBHBB", desc[:7])
        if t == DescriptorType.Hub:
            bc = (port_count+8) // 8
            fixed = int.from_bytes(desc[7 : 7 + bc], "little")
        elif t == DescriptorType.SsHub:
            declat, delay, fixed = struct.unpack("<BBH", desc[7:11])

        self.port = []
        for i in range(port_count):
            self.port.append(Port(self, i + 1, not ((fixed >> i) & 2)))

    def __getitem__(self, index):
        return self.port[index]

    def __len__(self):
        return len(self.port)

    def __iter__(self):
        return iter(self.port)
            
    async def descriptor_get(self, type, index):
        return await self.handle.control(RequestTypeType.Class,
                                         RequestTypeRecipient.Device,
                                         Request.GetDescriptor,
                                         (type << 8) | index, 0,
                                         self.handle.descriptor.max_packet_size0)

    async def descriptor_get_std(self, index):
        return await self.descriptor_get(DescriptorType.Hub, index)

    async def feature_clear(self, feature):
        await self.handle.control(RequestTypeType.Class,
                                  RequestTypeRecipient.Device,
                                  Request.ClearFeature, feature, 0, b'')

    async def feature_set(self, feature):
        await self.handle.control(RequestTypeType.Class,
                                  RequestTypeRecipient.Device,
                                  Request.SetFeature, feature, 0, b'')

    async def status_get(self):
        st = await self.handle.control(RequestTypeType.Class,
                                       RequestTypeRecipient.Device,
                                       Request.GetStatus, 0, 0, 4)
        ps, cs = struct.unpack("<HH", st)
        return HubStatus(ps), HubStatus(cs)
