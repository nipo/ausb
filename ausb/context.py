import asyncio
import threading
import usb1
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

    def close(self):
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
        self.close()
        return False

class Context:
    """
    AUsb main context.
    """
    def __init__(self, *, ignore_access_errors=True, enable_hotplug=True):
        """
        Setup a context wrapping libusb1's context.

        :param ignore_access_errors: Skip devices that can't be accessed during enumeration
        :param enable_hotplug: Enable hotplug event notifications (default: True)
        """
        self._ctx = usb1.USBContext()
        self._ignore_access_errors = ignore_access_errors

        # Hotplug support
        self._hotplug_iterators = set()
        self._hotplug_thread = None
        self._hotplug_stop = threading.Event()

        if enable_hotplug:
            self._start_hotplug_thread()

    @property
    def context(self):
        return self._ctx

    @property
    def ignore_access_errors(self):
        return self._ignore_access_errors

    def _start_hotplug_thread(self):
        """Start a daemon thread for processing hotplug events."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        def hotplug_callback(context, device, event_type):
            try:
                if event_type == usb1.HOTPLUG_EVENT_DEVICE_ARRIVED:
                    event = ConnectionEvent(self._ctx, device)
                else:
                    event = DisconnectionEvent(self._ctx, device)

                for iterator in list(self._hotplug_iterators):
                    try:
                        if loop and loop.is_running():
                            loop.call_soon_threadsafe(iterator._post_event, event)
                        else:
                            iterator._post_event(event)
                    except Exception:
                        pass
            except Exception:
                pass
            return 0

        try:
            self._ctx.hotplugRegisterCallback(
                hotplug_callback,
                events=usb1.HOTPLUG_EVENT_DEVICE_ARRIVED | usb1.HOTPLUG_EVENT_DEVICE_LEFT
            )
        except (AttributeError, usb1.USBError):
            # Hotplug not supported on this platform
            return

        def hotplug_worker():
            while not self._hotplug_stop.is_set():
                try:
                    self._ctx.handleEventsTimeout(0.5)
                except Exception:
                    break

        self._hotplug_thread = threading.Thread(target=hotplug_worker, daemon=True)
        self._hotplug_thread.start()

    def hotplug_events(self):
        """
        Create and return an async iterator for USB hotplug events.

        Usage::

            ctx = ausb.Context()
            async for event in ctx.hotplug_events():
                print(f"Event: {event}")

        Or with context manager::

            ctx = ausb.Context()
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
        for d in self._ctx.getDeviceIterator(skip_on_error=self._ignore_access_errors):
            d = descriptor.Device(self._ctx, d)
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

    def close(self):
        """
        Close the Context and clean up resources.
        """
        # Close all hotplug iterators
        for iterator in list(self._hotplug_iterators):
            iterator.close()

        # Stop hotplug thread
        if self._hotplug_thread:
            self._hotplug_stop.set()
            self._hotplug_thread.join(timeout=2)
            self._hotplug_thread = None

        self._ctx.close()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self.close()
        return False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
