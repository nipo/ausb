import enum

class RequestTypeDirection(enum.IntEnum):
    HostToDevice = 0
    DeviceToHost = 1

class RequestTypeType(enum.IntEnum):
    Standard = 0
    Class = 1
    Vendor = 2
    Reserved = 3

class RequestTypeRecipient(enum.IntEnum):
    Device = 0
    Interface = 1
    Endpoint = 2
    Other = 3

class RequestType:
    @staticmethod
    def pack(direction, type, recipient):
        return (int(direction) << 7) | (int(type) << 5) | int(recipient)

    @staticmethod
    def unpack(bmRequestType):
        b = int(bmRequestType)
        return (constant.RequestTypeDirection(b >> 7),
                constant.RequestTypeType((b >> 5) & 0x3),
                constant.RequestTypeRecipient(b & 0x1f))

class Request(enum.IntEnum):
    GetStatus = 0
    ClearFeature = 1
    SetFeature = 3
    SetAddress = 5
    GetDescriptor = 6
    SetDescriptor = 7
    GetConfiguration = 8
    SetConfiguration = 9
    GetInterface = 10
    SetInterface = 11
    SynchFrame = 12

class DescriptorType(enum.IntEnum):
    Device = 1
    Configuration = 2
    String = 3
    Interface = 4
    Endpoint = 5
    DeviceQualifier = 6
    OtherSpeedConfiguration = 7
    InterfacePower = 8
