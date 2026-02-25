import asyncio
from . import exception

class EndpointStreamReader:
    """
    StreamReader-compatible wrapper for Bulk IN endpoints.
    Provides asyncio StreamReader API for reading from USB endpoints.

    This implementation uses an internal buffer and background task to handle
    the fact that USB endpoints can only be read in multiples of max packet size.
    The background task continuously reads from the endpoint and fills the buffer,
    allowing arbitrary-sized reads from the user's perspective.
    """

    def __init__(self, endpoint, buffer_limit=65536):
        """
        :param endpoint: BulkInEndpoint instance
        :param buffer_limit: Maximum internal buffer size in bytes before pausing reads.
                            Default is 64KB. Background reading pauses when buffer
                            exceeds this limit and resumes at buffer_limit/2.
        """
        self._endpoint = endpoint
        self._buffer = bytearray()
        self._buffer_limit = buffer_limit
        self._low_water = buffer_limit // 2
        self._eof = False
        self._exception = None

        # Synchronization
        self._data_available = asyncio.Event()  # Set when buffer has data or EOF
        self._can_read_more = asyncio.Event()   # Set when buffer below high water mark
        self._can_read_more.set()  # Initially can read

        # Background reader task
        self._reader_task = None
        self._closed = False

    def _start_background_reader(self):
        """Start the background reader task if not already started."""
        if self._reader_task is None and not self._closed:
            self._reader_task = asyncio.create_task(self._background_reader())

    async def _background_reader(self):
        """
        Background task that continuously reads from USB endpoint and fills buffer.
        Pauses when buffer exceeds buffer_limit, resumes when it drops below low water mark.
        """
        try:
            while not self._closed:
                # Wait if buffer is too full
                await self._can_read_more.wait()

                if self._closed:
                    break

                # Read from USB endpoint (always reads full packets)
                try:
                    data = await self._endpoint.read()

                    if data:
                        self._buffer.extend(data)
                        self._data_available.set()

                        # Check if we should pause reading
                        if len(self._buffer) >= self._buffer_limit:
                            self._can_read_more.clear()
                    else:
                        # Empty read might indicate short packet or error
                        # Keep trying unless we hit an exception
                        pass

                except exception.TransferError as e:
                    # Transfer error indicates EOF or device disconnection
                    self._eof = True
                    self._exception = e
                    self._data_available.set()
                    break
                except exception.TransferTimeout:
                    # Timeout is not fatal, just retry
                    pass
                except Exception as e:
                    # Other exceptions are fatal
                    self._eof = True
                    self._exception = e
                    self._data_available.set()
                    break

        except asyncio.CancelledError:
            # Task was cancelled (normal cleanup)
            pass
        finally:
            self._eof = True
            self._data_available.set()

    async def read(self, n=-1):
        """
        Read up to n bytes from the stream.

        :param n: Maximum number of bytes to read. If -1, reads all available
                 buffered data (at least one USB packet worth).
        :returns: Bytes read from endpoint (may be less than n)
        """
        self._start_background_reader()

        if self._eof and not self._buffer:
            return b''

        # Wait for data to be available
        while not self._buffer and not self._eof:
            self._data_available.clear()
            await self._data_available.wait()

        # Check for exception
        if self._exception and not self._buffer:
            return b''

        if n <= 0:
            # Read all available
            data = bytes(self._buffer)
            self._buffer.clear()
        else:
            # Read up to n bytes
            data = bytes(self._buffer[:n])
            del self._buffer[:n]

        # Signal that buffer has space if we're below low water mark
        if len(self._buffer) < self._low_water:
            self._can_read_more.set()

        return data

    async def readexactly(self, n):
        """
        Read exactly n bytes. Waits for background reader to fill buffer if necessary.

        :param n: Number of bytes to read
        :returns: Exactly n bytes
        :raises asyncio.IncompleteReadError: If EOF is reached before reading n bytes
        """
        chunks = []
        remaining = n

        while remaining > 0:
            chunk = await self.read(remaining)
            if not chunk:
                break

            chunks.append(chunk)
            remaining -= len(chunk)

        return b''.join(chunks)

    async def readline(self):
        """
        Read until newline (\\n) is found.

        This implementation reads from the internal buffer, so it's efficient
        even though USB can only read in packet-sized chunks.

        :returns: Bytes up to and including newline, or remaining data if EOF
        """
        self._start_background_reader()
        chunks = []

        while True:
            # Search for newline in buffer
            try:
                newline_pos = self._buffer.index(b'\n'[0])
                # Found newline, return up to and including it
                chunk = bytes(self._buffer[:newline_pos + 1])
                del self._buffer[:newline_pos + 1]

                # Signal that buffer has space
                if len(self._buffer) < self._low_water:
                    self._can_read_more.set()

                chunks.append(chunk)
                break
            except ValueError:
                # No newline in buffer yet
                if self._buffer:
                    chunk = bytes(self._buffer)
                    self._buffer.clear()
                    chunks.append(chunk)

                if self._eof:
                    break

                # Wait for more data
                self._data_available.clear()
                await self._data_available.wait()

        return b''.join(chunks)

    def at_eof(self):
        """
        Return True if EOF was reached and buffer is empty.

        :returns: True if EOF reached and no data in buffer
        """
        return self._eof and not self._buffer

    async def close(self):
        """
        Close the stream reader and stop the background task.
        """
        if self._closed:
            return

        self._closed = True
        self._can_read_more.set()  # Wake up background task
        self._data_available.set()

        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None

    async def __aenter__(self):
        """Support async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Support async context manager."""
        await self.close()
        return False

    def __aiter__(self):
        """Support async iteration"""
        return self

    async def __anext__(self):
        """
        Iterate reading data until EOF.
        Note: This reads available buffered data, not necessarily USB packet boundaries.
        """
        data = await self.read()
        if not data:
            raise StopAsyncIteration
        return data


class EndpointStreamWriter:
    """
    StreamWriter-compatible wrapper for Bulk OUT endpoints.
    Provides asyncio StreamWriter API for writing to USB endpoints.
    """

    def __init__(self, endpoint):
        """
        :param endpoint: BulkOutEndpoint instance
        """
        self._endpoint = endpoint
        self._buffer = bytearray()
        self._closed = False
        self._buffer_lock = asyncio.Lock()
        self._drain_task = None

    def write(self, data):
        """
        Buffer data for writing. Call drain() to wait for transmit completion.

        :param data: Bytes to write
        """
        if self._closed:
            raise RuntimeError("Stream is closed")
        self._buffer.extend(data)
        self._drain_start()

    def writelines(self, lines):
        """
        Buffer multiple chunks for writing. Call drain() to actually send.

        :param lines: Iterable of bytes to write
        """
        for line in lines:
            self._buffer.extend(line)
        self._drain_start()

    def _drain_start(self):
        """
        Start background task to send buffered data.
        """
        if self._drain_task:
            return

        if self._buffer:
            self._drain_task = asyncio.create_task(self._drain_worker())

    async def drain(self):
        """
        Waits for current pending tx buffer to be sent in full.
        """
        t = self._drain_task
        if t:
            await t

    async def _drain_worker(self):
        """
        Background task worker for sending buffer
        """
        mps = self._endpoint.mps
        while self._buffer:
            async with self._buffer_lock:
                chunk_size = min(len(self._buffer), mps)
                chunk = bytes(self._buffer[:chunk_size])
                del self._buffer[:chunk_size]
            await self._endpoint.write(chunk)
        self._drain_task = None

    def close(self):
        """
        Mark the stream as closed. Pending data will still be sent on drain().
        """
        self._closed = True

    async def wait_closed(self):
        """
        Wait for the stream to close. Ensures all pending data is flushed.
        """
        await self.drain()

    def is_closing(self):
        """
        Return True if the stream is closed or closing.

        :returns: True if closed
        """
        return self._closed

    def can_write_eof(self):
        """
        USB endpoints don't support EOF.

        :returns: Always False
        """
        return False

    def write_eof(self):
        """
        USB endpoints don't support EOF.

        :raises NotImplementedError: Always
        """
        raise NotImplementedError("USB endpoints do not support EOF")

    def get_extra_info(self, name, default=None):
        """
        Get extra information about the endpoint.

        Supported names:
        - 'endpoint': The underlying Endpoint object
        - 'address': Endpoint address
        - 'mps': Max packet size

        :param name: Information name
        :param default: Default value if not found
        :returns: Information value or default
        """
        if name == 'endpoint':
            return self._endpoint
        elif name == 'address':
            return self._endpoint.address
        elif name == 'mps':
            return self._endpoint.mps
        else:
            return default
