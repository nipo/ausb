#!/usr/bin/env python3
"""
Simple tests for stream wrappers focusing on key functionality.
"""

import asyncio
from unittest.mock import Mock, AsyncMock
from ausb.stream import EndpointStreamReader, EndpointStreamWriter


async def test_basic_read():
    """Test basic read with buffering."""
    mock_endpoint = Mock()
    mock_endpoint.read = AsyncMock(side_effect=[b'hello', b' world', asyncio.CancelledError()])

    reader = EndpointStreamReader(mock_endpoint, buffer_limit=1024)

    data = await reader.read(5)
    assert data == b'hello', f"Expected b'hello', got {data}"

    await reader.close()
    print("  Basic read works")


async def test_readexactly():
    """Test readexactly assembles from multiple reads."""
    mock_endpoint = Mock()
    mock_endpoint.read = AsyncMock(side_effect=[b'12345', b'67890', asyncio.CancelledError()])

    reader = EndpointStreamReader(mock_endpoint, buffer_limit=1024)

    data = await reader.readexactly(10)
    assert data == b'1234567890', f"Expected b'1234567890', got {data}"

    await reader.close()
    print("  Readexactly works")


async def test_buffer_limit_param():
    """Test that buffer_limit parameter is respected."""
    mock_endpoint = Mock()
    mock_endpoint.read = AsyncMock(return_value=b'test')

    reader = EndpointStreamReader(mock_endpoint, buffer_limit=8192)
    assert reader._buffer_limit == 8192
    assert reader._low_water == 4096

    await reader.close()
    print("  Buffer limit parameter works")


async def test_writer_basic():
    """Test basic writer functionality."""
    mock_endpoint = Mock()
    mock_endpoint.write = AsyncMock()
    mock_endpoint.mps = 64

    writer = EndpointStreamWriter(mock_endpoint)
    writer.write(b'test')
    await writer.drain()

    mock_endpoint.write.assert_called_once_with(b'test')
    print("  Basic write works")


async def test_writer_chunking():
    """Test writer chunks by mps."""
    mock_endpoint = Mock()
    mock_endpoint.write = AsyncMock()
    mock_endpoint.mps = 5

    writer = EndpointStreamWriter(mock_endpoint)
    writer.write(b'1234567890')
    await writer.drain()

    assert mock_endpoint.write.call_count == 2
    print("  Writer chunking works")


async def main():
    """Run all tests."""
    print("Running simple stream tests...\n")

    try:
        await test_basic_read()
        await test_readexactly()
        await test_buffer_limit_param()
        await test_writer_basic()
        await test_writer_chunking()

        print("\nAll simple tests passed!")
        return 0
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    exit(exit_code)
