import struct
from ..exception import *
from ..constant import *
import enum
import uuid

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
    BOS = 0x000f
    DeviceCapability = 0x0010
    Hub = 0x0029
    SsHub = 0x002a

class DeviceCapability(enum.IntEnum):
    WirelessUSB = 1
    USB2 = 2
    SuperSpeed = 3
    ContainerId = 4
    Platform = 5
    PowerDelivery = 6
    BatteryInfo = 7
    SSP = 10
    PrecisionTime = 11
    
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
    def __init__(self, descriptor):
        self.descriptor = descriptor
        self.bus = self.descriptor.bus
        self.alternates = {self.bus:self}
        self.ports = self.descriptor.ports
        self.speed = self.descriptor.speed
        self.port = []
        self.container_id = None

    @classmethod
    async def create(cls, descriptor):
        self = cls(descriptor)
        await self._init()
        return self

    def __hash__(self):
        return hash((self.bus, tuple(self.ports), self.container_id))

    def __lt__(self, other):
        return (self.bus, tuple(self.ports), self.container_id) < (other.bus, tuple(other.ports), other.container_id)

    @property
    def handle(self):
        return self.descriptor.open()
    
    async def _init(self):
        try:
            h_ = self.handle
        except:
            return
        if not h_:
            return

        port_count, fixed = await self._port_info_get()
        
        for i in range(port_count):
            self.port.append(Port(self, i + 1, not ((fixed >> i) & 2)))

        self.container_id = await self._container_id_get()

    async def _port_info_get(self):
        try:
            desc = await self.descriptor_get_std(0)
        except TransferStalled:
            return 0, 0

        l, t, port_count, car, pwr, cont = struct.unpack("<BBBHBB", desc[:7])
        if t == DescriptorType.Hub:
            bc = (port_count+8) // 8
            fixed = int.from_bytes(desc[7 : 7 + bc], "little")
        elif t == DescriptorType.SsHub:
            declat, delay, fixed = struct.unpack("<BBH", desc[7:11])
        return port_count, fixed
        
    async def _container_id_get(self):
        try:
            bos = await self.handle.control(RequestTypeType.Standard,
                                            RequestTypeRecipient.Device,
                                            Request.GetDescriptor,
                                            (DescriptorType.BOS << 8) | 0, 0,
                                            self.handle.descriptor.max_packet_size0)
        except TransferStalled:
            return None
        
        length, type, total_length, count = struct.unpack("<BBHB", bos[:5])

        if len(bos) < total_length:
            return None

        point = length
        for i in range(count):
            length, type, cap = bos[point:point+3]
            if type == DescriptorType.DeviceCapability and cap == DeviceCapability.ContainerId:
                return uuid.UUID(bytes = bytes(bos[point+4:point+4+length]))
            point += length
        return None

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

    def __repr__(self):
        return "<Hub at %d:%s>" % (self.bus, "/".join(str(x) for x in self.ports))

    async def device_at_port(self, index):
        for bus in self.alternates.keys():
            try:
                return self.descriptor.context.device_get(bus = bus,
                                                          ports = self.ports + [index])
            except:
                pass
        return None
    
class Enumerator:
    @classmethod
    async def create(cls, context):
        self = cls(context)
        await self._init()
        return self

    def __init__(self, context):
        self.context = context
        self.hubs = []

    async def _init(self):
        alternates = {}
        hubs = {}

        for d in self.context.device_filter(classes = (9, 0)):
            try:
                hub = await Hub.create(d)
            except NotImplementedError:
                continue

            cid = hub.container_id or (d.bus, d.address)
            key = hub.bus, tuple(hub.ports), cid
            key2 = tuple(hub.ports), cid
            hubs[key] = hub
            try:
                alt = alternates[key2]
            except KeyError:
                alt = {}
                alternates[key2] = alt
            alt[hub.bus] = hub

        for alts in alternates.values():
            for a in alts.values():
                a.alternates = alts

        seen = set()
        aka = {}
        for h in hubs.values():
            if h in seen:
                continue
            seen |= set(h.alternates)
            alts = list(sorted(h.alternates.values()))
            hub = alts[0]
            for h in alts:
                aka[(h.bus, tuple(h.ports))] = hub
            self.hubs.append(hub)
        self.aka = aka
        
    def __iter__(self):
        return iter(self.hubs)

    def __len__(self):
        return len(self.hubs)

    def __getitem__(self, index):
        return self.hubs[index]
