import asyncio
import usb1
from .exception import (
    map_usb_error,
    TransferError, TransferTimeout, TransferStalled,
    DeviceError, TransferOverflow,
)
from .constant import *

DEFAULT_TIMEOUT = 1000


# libusb transfer status -> ausb exception. None means "completed OK".
_TRANSFER_STATUS_MAP = {
    usb1.TRANSFER_COMPLETED: None,
    usb1.TRANSFER_TIMED_OUT: TransferTimeout,
    usb1.TRANSFER_STALL:     TransferStalled,
    usb1.TRANSFER_NO_DEVICE: DeviceError,
    usb1.TRANSFER_OVERFLOW:  TransferOverflow,
    usb1.TRANSFER_CANCELLED: TransferError,
    usb1.TRANSFER_ERROR:     TransferError,
}


def _resolve_transfer_future(loop, future, transfer, payload_extractor):
    """libusb completion callback. Runs on the libusb event thread —
    schedule the actual Future resolution onto the asyncio loop via
    ``call_soon_threadsafe``. ``payload_extractor`` is called on the
    asyncio side and returns the value to set on the future (e.g.
    ``bytes(transfer.getBuffer()[:transfer.getActualLength()])`` for
    reads, ``transfer.getActualLength()`` for writes)."""
    status = transfer.getStatus()
    if status == usb1.TRANSFER_COMPLETED:
        try:
            payload = payload_extractor(transfer)
        except Exception as exc:
            loop.call_soon_threadsafe(_safe_set_exception, future, exc)
            return
        loop.call_soon_threadsafe(_safe_set_result, future, payload)
    else:
        exc_cls = _TRANSFER_STATUS_MAP.get(status, TransferError)
        loop.call_soon_threadsafe(
            _safe_set_exception, future,
            exc_cls(f"transfer status {status}"))


def _safe_set_result(future, value):
    if not future.done():
        future.set_result(value)


def _safe_set_exception(future, exc):
    if not future.done():
        future.set_exception(exc)


def _read_payload(transfer):
    return bytes(transfer.getBuffer()[:transfer.getActualLength()])


def _write_payload(transfer):
    return transfer.getActualLength()

class Device:
    """
    Opened device handle. This object should be spawned by DeviceDescriptor.open().
    """

    def __init__(self, context, descriptor, handle, timeout=DEFAULT_TIMEOUT):
        self.context = context
        self.descriptor = descriptor
        self.handle = handle
        self._timeout = timeout

    def reopen(self):
        ports = self.descriptor.ports
        bus = self.descriptor.bus
        self.descriptor = None
        self.handle = None
        next_desc = self.context.device_get(ports = ports, bus = bus)
        self.descriptor = next_desc
        self.handle = next_desc.device.open()

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

    def _sync_control(self, bmRequestType, request, value, index, data_or_length, timeout):
        if isinstance(data_or_length, int):
            return map_usb_error(
                self.handle.controlRead,
                bmRequestType, request, value, index, data_or_length,
                timeout=timeout)
        else:
            return map_usb_error(
                self.handle.controlWrite,
                bmRequestType, request, value, index, data_or_length,
                timeout=timeout)

    async def control(self, type, recipient, request, value, index, data_or_length, timeout=None):
        """
        Raw control IN/OUT request targeted on device.
        """
        bmRequestType = RequestType.pack(RequestTypeDirection.DeviceToHost
                                if isinstance(data_or_length, int) else
                                RequestTypeDirection.HostToDevice,
                                type,
                                recipient)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._sync_control,
            bmRequestType, request, value, index, data_or_length,
            timeout or self._timeout)

    async def standard_control(self, request, value, index, data_or_length):
        """
        Standard control IN/OUT request targeted on device.
        """
        return await self.control(RequestTypeType.Standard,
                                  RequestTypeRecipient.Device,
                                  request, value, index, data_or_length)

    async def class_control(self, request, value, index, data_or_length):
        """
        Class control IN/OUT request targeted on device.
        """
        return await self.control(RequestTypeType.Class,
                                  RequestTypeRecipient.Device,
                                  request, value, index, data_or_length)

    async def vendor_control(self, request, value, index, data_or_length):
        """
        Vendor-specific control IN/OUT request targeted on device.
        """
        return await self.control(RequestTypeType.Vendor,
                                  RequestTypeRecipient.Device,
                                  request, value, index, data_or_length)

    async def clear_feature(self, feature_selector):
        return await self.standard_control(Request.ClearFeature, feature_selector,
                                           0, b'')

    async def set_feature(self, feature_selector):
        return await self.standard_control(Request.SetFeature, feature_selector,
                                           0, b'')

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
        self.device.handle.setInterfaceAltSetting(self.interface, setting)
        self.__alt_setting = setting

    def kernel_driver_detach(self):
        """
        Ask for kernel driver detach
        """
        self.device.handle.detachKernelDriver(self.interface)

    def kernel_driver_attach(self):
        """
        Ask for kernel driver attach
        """
        self.device.handle.attachKernelDriver(self.interface)

    async def standard_control(self, request, value, data_or_length):
        """
        Standard control IN/OUT request targeted on interface.
        """
        return await self.device.control(RequestTypeType.Standard,
                                  RequestTypeRecipient.Interface,
                                  request, value, self.interface, data_or_length)

    async def class_control(self, request, value, data_or_length):
        """
        Class control IN/OUT request targeted on interface.
        """
        return await self.device.control(RequestTypeType.Class,
                                  RequestTypeRecipient.Interface,
                                  request, value, self.interface, data_or_length)

    async def vendor_control(self, request, value, data_or_length):
        """
        Vendor-specific control IN/OUT request targeted on interface.
        """
        return await self.device.control(RequestTypeType.Vendor,
                                  RequestTypeRecipient.Interface,
                                  request, value, self.interface, data_or_length)

    async def clear_feature(self, feature_selector):
        return await self.standard_control(Request.ClearFeature, feature_selector,
                                           b'')

    async def set_feature(self, feature_selector):
        return await self.standard_control(Request.SetFeature, feature_selector,
                                           b'')

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
    def __init__(self, device, address, mps, timeout=DEFAULT_TIMEOUT):
        self.device = device
        self.address = address
        self.mps = mps
        self._timeout = timeout

    def resume(self):
        """
        Resume servicing endpoint, clears halt condition.
        """
        self.device.handle.clearHalt(self.address)

    async def standard_control(self, request, value, data_or_length):
        """
        Standard control IN/OUT request targeted on endpoint.
        """
        return await self.device.control(RequestTypeType.Standard,
                                  RequestTypeRecipient.Endpoint,
                                  request, value, self.address, data_or_length)

    async def class_control(self, request, value, data_or_length):
        """
        Class control IN/OUT request targeted on endpoint.
        """
        return await self.device.control(RequestTypeType.Class,
                                  RequestTypeRecipient.Endpoint,
                                  request, value, self.address, data_or_length)

    async def vendor_control(self, request, value, data_or_length):
        """
        Vendor-specific control IN/OUT request targeted on endpoint.
        """
        return await self.device.control(RequestTypeType.Vendor,
                                  RequestTypeRecipient.Endpoint,
                                  request, value, self.address, data_or_length)

    async def clear_feature(self, feature_selector):
        return await self.standard_control(Request.ClearFeature, feature_selector,
                                           b'')

    async def set_feature(self, feature_selector):
        return await self.standard_control(Request.SetFeature, feature_selector,
                                           b'')

class BulkEndpoint(Endpoint):
    pass

class BulkInEndpoint(BulkEndpoint):
    def read_sync(self, size=0, timeout=None):
        """Sync bulk read. For use inside run_in_executor or
        outside an asyncio loop. The async ``read()`` uses libusb's
        async transfer API instead — multiple in-flight transfers
        across endpoints stay genuinely concurrent."""
        return map_usb_error(
            self.device.handle.bulkRead,
            self.address, size or self.mps,
            timeout=timeout or self._timeout)

    async def read(self, size=0, timeout=None):
        """Bulk IN transfer.

        Submits a libusb async transfer and awaits its completion.
        The completion callback fires on the Context's event thread
        and bridges back to this loop via ``call_soon_threadsafe``;
        multiple transfers (across endpoints or even on the same
        endpoint) run truly concurrently inside libusb's scheduler.
        """
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        transfer = self.device.handle.getTransfer()
        transfer.setBulk(
            self.address,
            size or self.mps,
            callback=lambda t: _resolve_transfer_future(
                loop, future, t, _read_payload),
            timeout=timeout or self._timeout,
        )
        map_usb_error(transfer.submit)
        return await future

    def stream_reader(self, buffer_limit=65536):
        """
        Create a StreamReader wrapper for this endpoint.

        :param buffer_limit: Maximum internal buffer size before pausing reads (default 64KB)
        :returns: EndpointStreamReader instance
        """
        from .stream import EndpointStreamReader
        return EndpointStreamReader(self, buffer_limit=buffer_limit)

class BulkOutEndpoint(BulkEndpoint):
    def write_sync(self, data, timeout=None):
        """Sync bulk write. See ``BulkInEndpoint.read_sync``."""
        return map_usb_error(
            self.device.handle.bulkWrite,
            self.address, data,
            timeout=timeout or self._timeout)

    async def write(self, data, timeout=None):
        """Bulk OUT transfer. See ``BulkInEndpoint.read``."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        transfer = self.device.handle.getTransfer()
        transfer.setBulk(
            self.address,
            data,
            callback=lambda t: _resolve_transfer_future(
                loop, future, t, _write_payload),
            timeout=timeout or self._timeout,
        )
        map_usb_error(transfer.submit)
        return await future

    def stream_writer(self):
        """
        Create a StreamWriter wrapper for this endpoint.

        :returns: EndpointStreamWriter instance
        """
        from .stream import EndpointStreamWriter
        return EndpointStreamWriter(self)

class InterruptEndpoint(Endpoint):
    def __init__(self, device, address, mps, interval, timeout=DEFAULT_TIMEOUT):
        Endpoint.__init__(self, device, address, mps, timeout)
        self.interval = interval

class InterruptInEndpoint(InterruptEndpoint):
    def read_sync(self, size=0, timeout=None):
        """Sync interrupt read. For use inside run_in_executor or
        outside an asyncio loop."""
        size = size or self.mps
        if size > self.mps:
            raise ValueError("Size too big for max packet size")
        return map_usb_error(
            self.device.handle.interruptRead,
            self.address, size,
            timeout=timeout or self._timeout)

    async def read(self, size=0, timeout=None):
        """Interrupt IN transfer (async)."""
        size = size or self.mps
        if size > self.mps:
            raise ValueError("Size too big for max packet size")
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        transfer = self.device.handle.getTransfer()
        transfer.setInterrupt(
            self.address,
            size,
            callback=lambda t: _resolve_transfer_future(
                loop, future, t, _read_payload),
            timeout=timeout or self._timeout,
        )
        map_usb_error(transfer.submit)
        return await future

class InterruptOutEndpoint(InterruptEndpoint):
    def write_sync(self, data, timeout=None):
        """Sync interrupt write. For use inside run_in_executor or
        outside an asyncio loop."""
        if len(data) > self.mps:
            raise ValueError("Data buffer too big for max packet size")
        return map_usb_error(
            self.device.handle.interruptWrite,
            self.address, data,
            timeout=timeout or self._timeout)

    async def write(self, data, timeout=None):
        """Interrupt OUT transfer (async)."""
        if len(data) > self.mps:
            raise ValueError("Data buffer too big for max packet size")
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        transfer = self.device.handle.getTransfer()
        transfer.setInterrupt(
            self.address,
            data,
            callback=lambda t: _resolve_transfer_future(
                loop, future, t, _write_payload),
            timeout=timeout or self._timeout,
        )
        map_usb_error(transfer.submit)
        return await future

class BulkPair:
    """Paired bulk OUT/IN endpoints for command/response protocols."""

    def __init__(self, ep_out, ep_in):
        self.out = ep_out
        self.in_ = ep_in

    def _sync_transfer(self, data, response_len, timeout):
        """Sequential write-then-read, sync. For callers that aren't
        in an asyncio loop. The async ``transfer`` is preferable —
        it submits OUT and IN concurrently into libusb's scheduler."""
        self.out.write_sync(data, timeout)
        if response_len == 0:
            return b""
        return self.in_.read_sync(response_len, timeout)

    async def transfer(self, data, response_len, timeout=None):
        """Submit OUT and IN transfers concurrently and await both.

        Both transfers post into libusb's async scheduler at the same
        time, so the device sees the OUT command while the host
        already has an IN transfer pending — required for devices
        with small response FIFOs that need the host to drain data
        in flight while the device is still processing commands."""
        if response_len == 0:
            await self.out.write(data, timeout=timeout)
            return b""
        _, rsp = await asyncio.gather(
            self.out.write(data, timeout=timeout),
            self.in_.read(response_len, timeout=timeout),
        )
        return rsp
