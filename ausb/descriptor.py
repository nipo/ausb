import usb1

class Device:
    """
    Device descriptor, retrieved from main context.
    """

    def __init__(self, context, device):
        self.context = context
        self.device = device

    def __str__(self):
        return str(self.device)

    def __len__(self):
        """
        Count of configurations for device
        """
        return len(self.device)

    def __getitem__(self, index):
        """
        Retrieve configuration descriptor by its index (indice are 1-based)
        """
        return Configuration(self, self.device[index - 1])

    def __hash__(self):
        return hash(self.device)

    def __eq__(self, other):
        return self.device == other.device

    @property
    def configurations(self):
        """
        Iterator over configuration descriptors
        """
        for c in self.device.iterConfigurations():
            yield Configuration(self, c)

    @property
    def settings(self):
        """
        Iterator over alternate settings descriptors
        """
        for c in self.configurations:
            for i in c:
                for s in i:
                    yield s

    @property
    def bus(self):
        """
        Hosting bus number
        """
        return self.device.getBusNumber()

    @property
    def port(self):
        """
        Bus port number
        """
        return self.device.getPortNumber()

    @property
    def ports(self):
        """
        Hierarchical list of post numbers to get to the device
        """
        return self.device.getPortNumberList()

    @property
    def address(self):
        """
        Device Address
        """
        return self.device.getDeviceAddress()

    @property
    def usb_version(self):
        """
        Device USB Version (bcdUSB), raw value
        """
        return self.device.getbcdUSB()

    @property
    def classes(self):
        """
        (class, subclass) couple
        """
        return self.device.getDeviceClass(), self.device.getDeviceSubClass()

    @property
    def protocol(self):
        """
        Device protocol
        """
        return self.device.getProtocol()

    @property
    def max_packet_size0(self):
        """
        Device MPS for Endpoint 0, in bytes
        """
        mps0 = self.device.getMaxPacketSize0()
        if self.speed == 4:
            return 1 << mps0
        return mps0

    @property
    def vendor_id(self):
        """
        VendorID from descriptor
        """
        return self.device.getVendorID()

    @property
    def product_id(self):
        """
        ProductID from descriptor
        """
        return self.device.getProductID()

    @property
    def device_version(self):
        """
        Device version from descriptor (bcdDevice), raw value
        """
        return self.device.getbcdDevice()

    @property
    def manufacturer(self):
        """
        Device manufacturer string from descriptor
        """
        return self.device.getManufacturer()

    @property
    def product(self):
        """
        Device product string from descriptor
        """
        return self.device.getProduct()

    @property
    def serial(self):
        """
        Device serial number string from descriptor
        """
        return self.device.getSerialNumber()

    @property
    def speed(self):
        """
        Device current connection speed
        """
        return self.device.getDeviceSpeed()

    def open(self):
        """
        Open device, get a Device handle on it.
        """
        from . import handle
        return handle.Device(self.context, self, self.device.open())
    
class Configuration:
    """
    Configuration descriptor, should be spawned by Device.
    """
    def __init__(self, device, configuration):
        self.device = device
        self.configuration = configuration

    @property
    def context(self):
        """
        AUsb Context for this descriptor
        """
        return self.device.context

    @property
    def number(self):
        """
        Configuration number
        """
        return self.configuration.getConfigurationValue()

    def __len__(self):
        """
        Count of interfaces in configuration
        """
        return self.configuration.getNumInterfaces()

    def __iter__(self):
        """
        Iterate over interfaces
        """
        for i in self.configuration:
            yield Interface(self, i)

    def __getitem__(self, interface):
        """
        Get interface by its index (0-based)
        """
        return Interface(self, self.configuration[interface])
    
class Interface:
    """
    Interface descriptor, spawned by Configuration
    """
    def __init__(self, configuration, interface):
        self.configuration = configuration
        self.interface = interface

    @property
    def device(self):
        """
        Device descriptor owning this interface.
        """
        return self.configuration.device

    @property
    def context(self):
        """
        AUsb Context
        """
        return self.configuration.device.context
    
    def __len__(self):
        """
        Count of alternate settings in interface
        """
        return self.interface.getNumSettings()

    def __iter__(self):
        """
        Iterator over alternate settings
        """
        for s in self.interface:
            yield Setting(self, s)

    def __getitem__(self, alt_setting):
        """
        Retrieve an alternate setting by its index (0-based)
        """
        return Setting(self, self.interface[alt_setting])

class Setting:
    """
    Alternate Setting descriptor, spawned by Interface.
    """
    def __init__(self, interface, interface_setting):
        self.interface = interface
        self.interface_setting = interface_setting

    @property
    def configuration(self):
        """
        Parent Configuration
        """
        return self.interface.configuration

    @property
    def device(self):
        """
        Parent Device
        """
        return self.interface.configuration.device

    @property
    def context(self):
        """
        AUsb context
        """
        return self.interface.configuration.device.context

    @property
    def number(self):
        """
        Setting number
        """
        return self.interface_setting.getNumber()

    @property
    def alternate(self):
        """
        Alternate setting number
        """
        return self.interface_setting.getAlternateSetting()

    @property
    def classes(self):
        """
        (class, subclass) couple
        """
        return (self.interface_setting.getClass(), self.interface_setting.getSubClass())

    @property
    def protocol(self):
        """
        Protocol id of setting
        """
        return self.interface_setting.getProtocol()

    @property
    def extra(self):
        """
        Extra descriptor blob
        """
        return self.interface_setting.getExtra()

    def endpoint_by_address(self, address):
        """
        Retrieve an Endpoint matching an endpoint address
        (including direction bit).
        :param address: Endpoint address
        :retruns: an Endpoint
        """
        for e in self.interface_setting:
            if e.getAddress() == address:
                return Endpoint(self, e)
        raise KeyError(address)
    
    def __len__(self):
        """
        Count of endpoints defined for this setting
        """
        return self.interface_setting.getNumEndpoints()

    def __iter__(self):
        """
        Iterate over endpoints
        """
        for e in self.interface_setting:
            yield Endpoint(self, e)

    def __getitem__(self, endpoint):
        """
        Retrieve an endpoint by its index (0-based, not address)
        """
        return Endpoint(self, self.interface_setting[endpoint])

class Endpoint:
    """
    Endpoint descriptor, spawned by Setting.
    """
    def __init__(self, interface_setting, endpoint):
        self.interface_setting = interface_setting
        self.endpoint = endpoint

    @property
    def direction(self):
        """
        Endpoint direction, either "in" or "out"
        """
        if self.endpoint.getAddress() & usb1.ENDPOINT_DIR_MASK == usb1.ENDPOINT_OUT:
            return "out"
        else:
            return "in"

    @property
    def number(self):
        """
        Endpoint number, without direction bit
        """
        return self.endpoint.getAddress() & ~usb1.ENDPOINT_DIR_MASK

    @property
    def type(self):
        """
        Endpoint type, either "control", "isochronous", "bulk" or "interrupt"
        """
        attrs = self.endpoint.getAttributes()
        type = attrs & 0x3
        return ["control", "isochronous", "bulk", "interrupt"][type]
        
    @property
    def interface(self):
        """
        Endpoint parent interface descriptor
        """
        return self.interface_setting.interface

    @property
    def configuration(self):
        """
        Endpoint parent configuration descriptor
        """
        return self.interface_setting.interface.configuration

    @property
    def device(self):
        """
        Endpoint parent device descriptor
        """
        return self.interface_setting.interface.configuration.device

    @property
    def context(self):
        """
        AUsb context
        """
        return self.interface_setting.interface.configuration.device.context

    @property
    def address(self):
        """
        Endpoint address (direction and number in a byte)
        """
        return self.endpoint.getAddress()

    @property
    def attributes(self):
        """
        Endpoint attribute word
        """
        return self.endpoint.getAttributes()

    @property
    def max_packet_size(self):
        """
        Endpoint max packet size, bytes
        """
        return self.endpoint.getMaxPacketSize()

    @property
    def interval(self):
        return self.endpoint.getInterval()

    @property
    def refresh(self):
        return self.endpoint.getRefresh()

    @property
    def sync_address(self):
        return self.endpoint.getSyncAddress()

    @property
    def extra(self):
        """
        Extra descriptor blob
        """
        return self.endpoint.getExtra()
