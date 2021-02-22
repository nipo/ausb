import asyncio
import usb1
from select import POLLIN, POLLOUT
from weakref import finalize
from . import descriptor

__all__ = ["Context"]

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
        self.done = asyncio.Event()
        self.readers = set()
        self.writers = set()
        self.context = context

        self.context.setPollFDNotifiers(self._fd_register, self._fd_unregister, self)

        waiter = asyncio.shield(self._work())

    def close(self):
        """
        Stop watching all FDs and stop calling context.
        """
        self.context.setPollFDNotifiers()
        self.done.set()
        self.fd_ready.set()

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
            while not self.done.is_set():
                try:
                    self.fd_ready.clear()
                    await asyncio.wait_for(
                        self.fd_ready.wait(),
                        timeout = self.context.getNextTimeout())
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

class Context:
    """
    AUsb main context.
    """
    def __init__(self, loop = None, ignore_access_errors = True):
        """
        Setup a context wrapping libusb1's context. Binds usb1 to
        asyncio's event loop immediately.
        """
        self.context = usb1.USBContext()
        self.loop = loop or asyncio.get_running_loop()
        self.ignore_access_errors = ignore_access_errors
        self.notifier = ContextNotifier(self.loop, self.context)
        finalize(self, self.notifier.close)
        finalize(self, self.context.close)

    def device_filter(self, **criteria):
        """
        Iterate through device descriptors matching all the criteria.
        Criteria are matched against device descriptor attributes.
        """
        for d in self.context.getDeviceIterator(skip_on_error = self.ignore_access_errors):
            d = descriptor.Device(self, d)
            if all(criteria[k] == getattr(d, k) for k in criteria.keys()):
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
