import asyncio
import usb1
from select import POLLIN, POLLOUT
from weakref import finalize
from . import descriptor

__all__ = ["Context", "ConnectionEvent", "DisconnectionEvent"]

class HotplugEvent:
    def __init__(self, context, device):
        """
        :param context: ausb context
        :param device: device object
        """
        self.device = descriptor.Device(context, device) if device else None

class ConnectionEvent(HotplugEvent):
    """
    Represents a USB hotplug event (device arrival).
    """

    def __repr__(self):
        return f"<ConnectionEvent: {self.device.vendor_id:04x}:{self.device.product_id:04x}>"

class DisconnectionEvent(HotplugEvent):
    """
    Represents a USB hotplug event (device left).
    """

    def __repr__(self):
        return f"<DisconnectionEvent>"

class HotplugIterator:
    """
    Async iterator for USB hotplug events.
    Yields HotplugEvent objects when devices are connected or disconnected.
    """
    def __init__(self, context):
        """
        :param context: The Context instance this iterator belongs to
        """
        self.context = context
        self.queue = asyncio.Queue()
        self._closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        """
        Wait for and return the next hotplug event.
        Raises StopAsyncIteration when the iterator is closed.
        """
        if self._closed and self.queue.empty():
            raise StopAsyncIteration
        try:
            event = await self.queue.get()
        except asyncio.CancelledError:
            raise StopAsyncIteration
        if event is None:  # Sentinel for close
            raise StopAsyncIteration
        return event

    def _post_event(self, event):
        """
        Internal method to post an event to this iterator's queue.
        Called by Context when a hotplug event occurs.
        """
        if not self._closed:
            self.queue.put_nowait(event)

    async def close(self):
        """
        Close this iterator. After closing, no more events will be received.
        """
        if not self._closed:
            self._closed = True
            self.queue.put_nowait(None)  # Sentinel to wake up any waiting __anext__
            if self in self.context._hotplug_iterators:
                self.context._hotplug_iterators.remove(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False

class ContextNotifier:
    """
    Object used for binding libusb1 into Asyncio's event loop.
    This is an implementation detail (i.e. no API stability).
    """
    def __init__(self, loop, context):
        """
        :param loop: Event loop
        :param context: usb1 context
        """
        self.loop = loop
        self.fd_ready = asyncio.Event()
        self.terminate = asyncio.Event()
        self.terminated = asyncio.Event()
        self.readers = set()
        self.writers = set()
        self.context = context

        self.context.setPollFDNotifiers(self._fd_register, self._fd_unregister, self)
        self._task = asyncio.create_task(self._work())

    def _finalizer(self, obj):
        finalize(obj, self._close, self.context, self.terminate)

    @staticmethod
    def _close(context, terminate):
        context.setPollFDNotifiers()
        terminate.set()

    async def close(self):
        """
        Stop watching all FDs and stop calling context.
        """
        self.context.setPollFDNotifiers()
        self.terminate.set()
        self.fd_ready.set()
        await self.terminated.wait()

    @staticmethod
    def _fd_register(fd, events, self):
        if events & POLLIN:
            self.readers.add(fd)
            self.loop.add_reader(fd, self.fd_ready.set)
        if events & POLLOUT:
            self.writers.add(fd)
            self.loop.add_writer(fd, self.fd_ready.set)

    @staticmethod
    def _fd_unregister(fd, self):
        if fd in self.readers:
            self.readers.remove(fd)
            self.loop.remove_reader(fd)
        if fd in self.writers:
            self.writers.remove(fd)
            self.loop.remove_writer(fd)

    async def _work(self):
        try:
            while not self.terminate.is_set():
                try:
                    self.fd_ready.clear()
                    # Even if libusb context has nothing to wait for,
                    # have a 0.1 second timeout so that hotplug events
                    # are still processed.
                    await asyncio.wait_for(
                        self.fd_ready.wait(),
                        timeout = self.context.getNextTimeout() or 0.1)
                except asyncio.TimeoutError:
                    pass
                except asyncio.CancelledError:
                    continue
                self.context.handleEventsTimeout()
        finally:
            for fd in self.writers:
                self.loop.remove_writer(fd)
            for fd in self.readers:
                self.loop.remove_reader(fd)
            self.terminated.set()
        
class Context:
    """
    AUsb main context.
    """
    def __init__(self, loop = None, ignore_access_errors = True, enable_hotplug = True):
        """
        Setup a context wrapping libusb1's context. Binds usb1 to
        asyncio's event loop immediately.

        :param loop: asyncio event loop (default: get current event loop)
        :param ignore_access_errors: Skip devices that can't be accessed during enumeration
        :param enable_hotplug: Enable hotplug event notifications (default: True)
        """
        self.context = usb1.USBContext()
        self.loop = loop or asyncio.get_event_loop()
        self.ignore_access_errors = ignore_access_errors
        self.notifier = ContextNotifier(self.loop, self.context)

        # Hotplug support
        self._hotplug_iterators = set()
        self._hotplug_handle = None

        finalize(self, self.context.close)
        finalize(self, self._cleanup_hotplug, self._hotplug_iterators)
        self.notifier._finalizer(self)

        if enable_hotplug:
            self._register_hotplug()
        
    @staticmethod
    def _cleanup_hotplug(iterators):
        """
        Cleanup hotplug iterators when Context is finalized.
        Called automatically during garbage collection.
        """
        # Close all active iterators
        for iterator in list(iterators):
            iterator._closed = True
            try:
                iterator.queue.put_nowait(None)
            except:
                pass

    def _register_hotplug(self):
        """
        Register hotplug callback with libusb to receive device arrival/departure events.
        Internal method called during Context initialization if enable_hotplug is True.
        """
        def hotplug_callback(context, device, event_type):
            """
            Callback invoked by libusb when a USB device is connected or disconnected.
            This is called from the libusb event handling thread.
            """
            try:
                if event_type == usb1.HOTPLUG_EVENT_DEVICE_ARRIVED:
                    event = ConnectionEvent(context, device)
                else:
                    event = DisconnectionEvent(context, device)

                for iterator in list(self._hotplug_iterators):
                    try:
                        iterator._post_event(event)
                    except Exception:
                        pass
            except Exception:
                pass

            # Return 0 to keep callback registered
            return 0

        try:
            self._hotplug_handle = self.context.hotplugRegisterCallback(
                hotplug_callback,
                events = usb1.HOTPLUG_EVENT_DEVICE_ARRIVED | usb1.HOTPLUG_EVENT_DEVICE_LEFT
            )
        except (AttributeError, usb1.USBError):
            # Hotplug not supported on this platform or libusb version
            self._hotplug_handle = None

    def hotplug_events(self):
        """
        Create and return an async iterator for USB hotplug events.

        Returns an async iterator that yields HotplugEvent objects when USB devices
        are connected (DEVICE_ARRIVED) or disconnected (DEVICE_LEFT).

        Usage::

            ctx = ausb.Context(loop)
            async for event in ctx.hotplug_events():
                if event.event_type == ausb.HotplugEventType.DEVICE_ARRIVED:
                    print(f"Device connected: {event.device.vendor_id:04x}:{event.device.product_id:04x}")
                else:
                    print(f"Device disconnected")

        Or with context manager::

            ctx = ausb.Context(loop)
            async with ctx.hotplug_events() as events:
                async for event in events:
                    print(f"Event: {event}")

        :returns: HotplugIterator instance
        """
        iterator = HotplugIterator(self)
        self._hotplug_iterators.add(iterator)
        return iterator

    def device_filter(self, **criteria):
        """
        Iterate through device descriptors matching all the criteria.
        Criteria are matched against device descriptor attributes.
        """
        for d in self.context.getDeviceIterator(skip_on_error = self.ignore_access_errors):
            d = descriptor.Device(self.context, d)
#            for k, v in criteria.items():
#                print(getattr(d, k), v)
            if all(v == getattr(d, k) for k, v in criteria.items()):
                yield d

    def device_get_any(self, **criteria):
        """
        Retrieve first device descriptor matching all the criteria.
        Criteria are matched against device descriptor attributes.
        Raise KeyError if no device matches.
        """
        for d in self.device_filter(**criteria):
            return d
        raise KeyError()

    def device_get(self, **criteria):
        """
        Retrieve the only device descriptor matching all the criteria.
        Criteria are matched against device descriptor attributes.
        Raise ValueError if count of matching device is not 1.
        """
        matching = self.device_filter(**criteria)
        try:
            d, = matching
            return d
        except ValueError:
            raise ValueError("Not exactly one device matching")

    def __iter__(self):
        """
        Iterate over all available devices, yields descriptor.Device objects.
        """
        return self.device_filter()

    async def close(self):
        """
        Explicitly close the Context and clean up resources.
        This stops the ContextNotifier and closes all hotplug iterators.
        """
        # Close all hotplug iterators
        for iterator in list(self._hotplug_iterators):
            try:
                await iterator.close()
            except:
                pass

        # Close the notifier
        if self.notifier:
            await self.notifier.close()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
        return False
