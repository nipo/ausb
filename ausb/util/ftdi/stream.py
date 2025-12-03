"""FTDI-specific stream reader/writer"""

import asyncio
from ausb.stream import EndpointStreamReader
from ausb import exception
from .constant import Status


class FtdiStreamReader(EndpointStreamReader):
    """
    StreamReader for FTDI endpoints that handles 2-byte status headers.

    FTDI chips prepend a 2-byte modem status to every IN packet.
    This reader strips the status and makes it available separately
    via the last_status property.

    Inherits from ausb.stream.EndpointStreamReader and overrides the
    background reader to handle FTDI-specific packet format.
    """

    def __init__(self, endpoint, buffer_limit=65536):
        """
        Create FTDI stream reader.

        :param endpoint: BulkInEndpoint instance
        :param buffer_limit: Maximum internal buffer size before pausing reads (default 64KB)
        """
        super().__init__(endpoint, buffer_limit)
        self.last_status = Status(0)

    async def _background_reader(self):
        """
        Background task that continuously reads from USB endpoint.

        Overrides parent implementation to strip FTDI's 2-byte status header
        from each packet before adding data to buffer.
        """
        try:
            while not self._closed:
                # Wait if buffer is too full
                await self._can_read_more.wait()

                if self._closed:
                    break

                try:
                    # Read full packet (includes 2-byte status)
                    packet = await self._endpoint.read()

                    if len(packet) >= 2:
                        # Extract and save modem status
                        self.last_status = Status(
                            int.from_bytes(packet[:2], "little"))

                        # Add data (sans status) to buffer
                        data = packet[2:]
                        if data:
                            self._buffer.extend(data)
                            self._data_available.set()

                        # Flow control: pause if buffer too full
                        if len(self._buffer) >= self._buffer_limit:
                            self._can_read_more.clear()

                except exception.TransferError as e:
                    # Transfer error indicates device disconnection or fatal error
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
