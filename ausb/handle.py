import asyncio
import usb1
from . import exception

class Device:
    """
    Opened device handle. This object should be spawned by DeviceDescriptor.open().
    """
    def __init__(self, context, descriptor, handle):
        self.context = context
        self.descriptor = descriptor
        self.handle = handle

    @property
    def configuration(self):
        """
        Current configuration index.
        """
        return self.handle.getConfiguration()

    @configuration.setter
    def configuration(self, configuration):
        return self.handle.setConfiguration(configuration)

    @property
    def manufacturer(self):
        """
        Manufacturer string from descriptor
        """
        return self.handle.getManufacturer()

    @property
    def product(self):
        """
        Product string from descriptor
        """
        return self.handle.getProduct()

    @property
    def serial(self):
        """
        Device serial number string from descriptor
        """
        return self.handle.getSerialNumber()

    def interface_claim(self, interface):
        """
        Claim and retrieve an interface.

        :param interface: Interface index
        :returns: An Interface instance
        """
        intf = self.handle.claimInterface(interface)
        return Interface(self, interface, self.descriptor[self.configuration][interface], intf)

    def reset(self):
        """
        Perform an USB reset for device
        """
        self.handle.resetDevice()

    @property
    def kernel_driver_active(self):
        """
        Getter whether a kernel driver is currently active for device.
        """
        return self.handle.kernelDriverActive()

    @property
    def languages(self):
        return self.handle.getSupportedLanguageList()

    @staticmethod
    def _on_transfer_done(transfer):
        """
        Internal method for handling transfers with Asyncio.
        """
        transfer_done = transfer.transfer_done

        if not transfer_done or transfer_done.done():
            return

        transfer.transfer_done = None
        
        status = transfer.getStatus()
        if status == usb1.TRANSFER_COMPLETED:
            transfer_done.set_result(transfer.getBuffer()[:transfer.getActualLength()])
        elif status == usb1.TRANSFER_CANCELLED:
            transfer_done.set_exception(asyncio.CancelledError())
        elif status == usb1.TRANSFER_ERROR:
            transfer_done.set_exception(exception.TransferError())
        elif status == usb1.TRANSFER_TIMED_OUT:
            transfer_done.set_exception(exception.TransferTimeout())
        elif status == usb1.TRANSFER_STALL:
            transfer_done.set_exception(exception.TransferStalled())
        elif status == usb1.TRANSFER_NO_DEVICE:
            transfer_done.set_exception(exception.DeviceError())
        elif status == usb1.TRANSFER_OVERFLOW:
            transfer_done.set_exception(exception.TransferOverflow())
        else:
            transfer_done.set_exception(RuntimeError())
    
    async def _transfer_run(self, transfer):
        """
        Internal method for handling transfers with Asyncio.
        """
        transfer_done = self.context.loop.create_future()
        transfer.transfer_done = transfer_done
        transfer.setCallback(self._on_transfer_done)
        try:
            transfer.submit()
        except usb1.USBErrorNoDevice:
            raise DeviceError()

        try:
            return await transfer_done
        except asyncio.CancelledError:
            try:
                transfer.cancel()
            except:
                pass
            raise
    
    async def write(self, type, request, value, index, data):
        """
        Control OUT request.
        """
        transfer = self.handle.getTransfer()
        type = (type & ~usb1.ENDPOINT_DIR_MASK) | usb1.ENDPOINT_OUT
        transfer.setControl(type, request, value, index, data)
        return await self._transfer_run(transfer)

    async def read(self, type, request, value, index, size):
        """
        Control IN request.
        :returns: input data buffer, if any.
        """
        transfer = self.handle.getTransfer()
        type = (type & ~usb1.ENDPOINT_DIR_MASK) | usb1.ENDPOINT_IN
        transfer.setControl(type, request, value, index, size)
        return await self._transfer_run(transfer)
    
class Interface:
    """
    Interface handle. Should be spawned by Device.interface_claim().
    """
    def __init__(self, device, interface, descriptor, interface_handle):
        self.device = device
        self.interface = interface
        self.__descriptor = descriptor
        self.interface_handle = interface_handle
        self.__alt_setting = 0

    @property
    def descriptor(self):
        """
        InterfaceDescriptor object for interface
        """
        return self.__descriptor[self.__alt_setting]

    @property
    def alternate(self):
        """
        Current alternate setting index
        """
        return self.__alt_setting

    @alternate.setter
    def alternate(self, setting):
        self.device.setInterfaceAltSetting(self.interface, setting)
        self.__alt_setting = setting

    def kernel_driver_detach(self):
        """
        Ask for kernel driver detach
        """
        self.device.detachKernelDriver(self.interface)

    def kernel_driver_attach(self):
        """
        Ask for kernel driver attach
        """
        self.device.attachKernelDriver(self.interface)

    def open(self, endpoint):
        """
        Get an Endpoint handle for an EndpointDescriptor.

        :param endpoint: EndpointDescriptor instance to open endpoint for
        :returns: An Endpoint instance
        """
        t = endpoint.type
        a = endpoint.address
        s = endpoint.max_packet_size

        if t == "bulk":
            if a & usb1.ENDPOINT_DIR_MASK == usb1.ENDPOINT_IN:
                return BulkInEndpoint(self.device, a, s)
            else:
                return BulkOutEndpoint(self.device, a, s)
        elif t == "interrupt":
            if a & usb1.ENDPOINT_DIR_MASK == usb1.ENDPOINT_IN:
                return InterruptInEndpoint(self.device, a, s, endpoint.interval)
            else:
                return InterruptOutEndpoint(self.device, a, s, endpoint.interval)
        else:
            raise ValueError(t)

class Endpoint:
    """
    Endpoint handle, should be spawned by Interface.open()
    """
    def __init__(self, device, address, mps):
        self.device = device
        self.address = address
        self.mps = mps

    def resume(self):
        """
        Resume servicing endpoint, clears halt condition.
        """
        self.device.handle.clearHalt(self.address)
        
class BulkEndpoint(Endpoint):
    pass

class BulkInEndpoint(BulkEndpoint):
    async def read(self, size = 0):
        """
        Bulk IN transfer
        """
        size = size or self.mps

        transfer = self.device.handle.getTransfer()
        transfer.setBulk(self.address, size)
        return await self.device._transfer_run(transfer)

class BulkOutEndpoint(BulkEndpoint):
    async def write(self, data):
        """
        Bulk OUT transfer
        """
        transfer = self.device.handle.getTransfer()
        transfer.setBulk(self.address, data)
        return await self.device._transfer_run(transfer)

class InterruptEndpoint(Endpoint):
    def __init__(self, device, address, mps, interval):
        Endpoint.__init__(self, device, address, mps)
        self.interval = interval

class InterruptInEndpoint(InterruptEndpoint):
    async def read(self, size = 0):
        """
        Interrupt IN transfer
        """
        size = size or self.mps

        if size > self.mps:
            raise ValueError("Size too big for max packet size")

        transfer = self.device.handle.getTransfer()
        transfer.setInterrupt(self.address, size)
        return await self.device._transfer_run(transfer)

class InterruptOutEndpoint(InterruptEndpoint):
    async def write(self, data):
        """
        Interrupt OUT transfer
        """
        if len(data) > self.mps:
            raise ValueError("Data buffer too big for max packet size")

        transfer = self.device.handle.getTransfer()
        transfer.setInterrupt(self.address, data)
        return await self.device._transfer_run(transfer)
