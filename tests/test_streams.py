#!/usr/bin/env python3
"""
Tests for EndpointStreamReader and EndpointStreamWriter classes.

This test validates the buffered implementation without requiring actual USB hardware.
"""

import asyncio
from unittest.mock import Mock, AsyncMock
from ausb.stream import EndpointStreamReader, EndpointStreamWriter


def test_stream_reader_api():
    """Test that EndpointStreamReader has the expected methods."""
    mock_endpoint = Mock()
    mock_endpoint.read = AsyncMock(return_value=b'test data')

    reader = EndpointStreamReader(mock_endpoint)

    # Check that all expected methods exist
    assert hasattr(reader, 'read')
    assert hasattr(reader, 'readexactly')
    assert hasattr(reader, 'readline')
    assert hasattr(reader, 'at_eof')
    assert hasattr(reader, 'close')
    assert hasattr(reader, '__aiter__')
    assert hasattr(reader, '__anext__')
    assert hasattr(reader, '__aenter__')
    assert hasattr(reader, '__aexit__')

    # Check initial state
    assert reader.at_eof() == False
    assert reader._buffer_limit == 65536
    assert reader._low_water == 32768
    print("  EndpointStreamReader API check passed")


def test_stream_writer_api():
    """Test that EndpointStreamWriter has the expected methods."""
    mock_endpoint = Mock()
    mock_endpoint.write = AsyncMock()
    mock_endpoint.mps = 512

    writer = EndpointStreamWriter(mock_endpoint)

    # Check that all expected methods exist
    assert hasattr(writer, 'write')
    assert hasattr(writer, 'writelines')
    assert hasattr(writer, 'drain')
    assert hasattr(writer, 'close')
    assert hasattr(writer, 'wait_closed')
    assert hasattr(writer, 'is_closing')
    assert hasattr(writer, 'can_write_eof')
    assert hasattr(writer, 'write_eof')
    assert hasattr(writer, 'get_extra_info')

    # Check initial state
    assert writer.is_closing() == False
    assert writer.can_write_eof() == False

    # Check get_extra_info
    assert writer.get_extra_info('endpoint') == mock_endpoint
    assert writer.get_extra_info('address') == mock_endpoint.address
    assert writer.get_extra_info('mps') == 512
    assert writer.get_extra_info('unknown') is None
    assert writer.get_extra_info('unknown', 'default') == 'default'

    print("  EndpointStreamWriter API check passed")


async def test_stream_reader_basic():
    """Test basic EndpointStreamReader read operations."""
    mock_endpoint = Mock()
    mock_endpoint.read = AsyncMock(side_effect=[
        b'hello world',
        asyncio.CancelledError()
    ])

    reader = EndpointStreamReader(mock_endpoint, buffer_limit=1024)

    data = await reader.read(11)
    assert data == b'hello world'

    await reader.close()
    print("  EndpointStreamReader basic read passed")


async def test_stream_reader_readexactly():
    """Test EndpointStreamReader readexactly with multiple transfers."""
    mock_endpoint = Mock()
    mock_endpoint.read = AsyncMock(side_effect=[
        b'hello',
        b' ',
        b'world',
        b'!!!',
        asyncio.CancelledError()
    ])

    reader = EndpointStreamReader(mock_endpoint, buffer_limit=1024)

    data = await reader.readexactly(11)
    assert data == b'hello world'

    await reader.close()
    print("  EndpointStreamReader readexactly passed")


async def test_stream_reader_readline():
    """Test EndpointStreamReader readline functionality."""
    mock_endpoint = Mock()
    mock_endpoint.read = AsyncMock(side_effect=[
        b'first line\nsecond',
        b' line\nthird',
        b' line\n',
        asyncio.CancelledError()
    ])

    reader = EndpointStreamReader(mock_endpoint, buffer_limit=1024)

    line1 = await reader.readline()
    assert line1 == b'first line\n'

    line2 = await reader.readline()
    assert line2 == b'second line\n'

    line3 = await reader.readline()
    assert line3 == b'third line\n'

    await reader.close()
    print("  EndpointStreamReader readline passed")


async def test_stream_reader_buffering():
    """Test that EndpointStreamReader buffers data from background reads."""
    mock_endpoint = Mock()
    mock_endpoint.read = AsyncMock(side_effect=[
        b'packet1',
        b'packet2',
        b'packet3',
        asyncio.CancelledError()
    ])

    reader = EndpointStreamReader(mock_endpoint, buffer_limit=1024)

    data1 = await reader.read(7)
    assert data1 == b'packet1'

    await asyncio.sleep(0.05)

    data2 = await reader.read(3)
    assert data2 == b'pac'

    data3 = await reader.read(4)
    assert data3 == b'ket2'

    await reader.close()
    print("  EndpointStreamReader buffering passed")


async def test_stream_reader_context_manager():
    """Test that EndpointStreamReader works as async context manager."""
    mock_endpoint = Mock()
    mock_endpoint.read = AsyncMock(side_effect=[
        b'test data',
        asyncio.CancelledError()
    ])

    async with EndpointStreamReader(mock_endpoint) as reader:
        data = await reader.read()
        assert data == b'test data'

    assert reader._closed == True
    print("  EndpointStreamReader context manager passed")


async def test_stream_reader_custom_buffer_limit():
    """Test that EndpointStreamReader accepts custom buffer_limit."""
    mock_endpoint = Mock()
    mock_endpoint.read = AsyncMock(return_value=b'test')

    reader = EndpointStreamReader(mock_endpoint, buffer_limit=8192)

    assert reader._buffer_limit == 8192
    assert reader._low_water == 4096

    await reader.close()
    print("  EndpointStreamReader custom buffer_limit passed")


async def test_stream_writer_basic():
    """Test basic EndpointStreamWriter write and drain."""
    mock_endpoint = Mock()
    mock_endpoint.write = AsyncMock()
    mock_endpoint.mps = 64

    writer = EndpointStreamWriter(mock_endpoint)

    writer.write(b'hello')
    writer.write(b' world')

    mock_endpoint.write.assert_not_called()

    await writer.drain()

    mock_endpoint.write.assert_called_once_with(b'hello world')

    print("  EndpointStreamWriter basic write passed")


async def test_stream_writer_chunking():
    """Test that EndpointStreamWriter chunks data by max packet size."""
    mock_endpoint = Mock()
    mock_endpoint.write = AsyncMock()
    mock_endpoint.mps = 10

    writer = EndpointStreamWriter(mock_endpoint)

    data = b'a' * 25
    writer.write(data)
    await writer.drain()

    assert mock_endpoint.write.call_count == 3
    calls = [call.args[0] for call in mock_endpoint.write.call_args_list]
    assert calls[0] == b'a' * 10
    assert calls[1] == b'a' * 10
    assert calls[2] == b'a' * 5

    print("  EndpointStreamWriter chunking passed")


async def test_stream_writer_close():
    """Test EndpointStreamWriter close and wait_closed."""
    mock_endpoint = Mock()
    mock_endpoint.write = AsyncMock()
    mock_endpoint.mps = 64

    writer = EndpointStreamWriter(mock_endpoint)

    writer.write(b'final message')

    writer.close()
    assert writer.is_closing() == True

    await writer.wait_closed()
    mock_endpoint.write.assert_called_once_with(b'final message')

    print("  EndpointStreamWriter close passed")


async def test_stream_reader_iteration():
    """Test EndpointStreamReader collects all data."""
    mock_endpoint = Mock()
    mock_endpoint.read = AsyncMock(side_effect=[
        b'packet1',
        b'packet2',
        b'packet3',
        asyncio.CancelledError()
    ])

    reader = EndpointStreamReader(mock_endpoint, buffer_limit=1024)

    # Background reader may aggregate packets, so collect all data
    chunks = []
    while True:
        chunk = await reader.read()
        if not chunk:
            break
        chunks.append(chunk)

    total = b''.join(chunks)
    assert total == b'packet1packet2packet3'

    await reader.close()
    print("  EndpointStreamReader iteration passed")


async def test_factory_method_buffer_limit():
    """Test that factory methods accept buffer_limit parameter."""
    from ausb.handle import BulkInEndpoint

    mock_device = Mock()
    endpoint = BulkInEndpoint(mock_device, address=0x81, mps=512)
    endpoint.read = AsyncMock(return_value=b'test')

    reader1 = endpoint.stream_reader()
    assert reader1._buffer_limit == 65536

    reader2 = endpoint.stream_reader(buffer_limit=8192)
    assert reader2._buffer_limit == 8192

    await reader1.close()
    await reader2.close()

    print("  Factory method buffer_limit parameter passed")


def run_tests():
    """Run all tests."""
    print("Running stream wrapper tests...\n")

    # Synchronous tests
    test_stream_reader_api()
    test_stream_writer_api()

    # Async tests
    asyncio.run(test_stream_reader_basic())
    asyncio.run(test_stream_reader_readexactly())
    asyncio.run(test_stream_reader_readline())
    asyncio.run(test_stream_reader_buffering())
    asyncio.run(test_stream_reader_context_manager())
    asyncio.run(test_stream_reader_custom_buffer_limit())
    asyncio.run(test_stream_writer_basic())
    asyncio.run(test_stream_writer_chunking())
    asyncio.run(test_stream_writer_close())
    asyncio.run(test_stream_reader_iteration())
    asyncio.run(test_factory_method_buffer_limit())

    print("\nAll stream tests passed!")


if __name__ == '__main__':
    run_tests()
