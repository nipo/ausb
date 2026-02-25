#!/usr/bin/env python3
"""
Verify that the stream wrapper factory methods are properly integrated
into the endpoint classes.
"""

import sys
from unittest.mock import Mock
from ausb.handle import (
    BulkInEndpoint,
    BulkOutEndpoint,
    InterruptInEndpoint,
    InterruptOutEndpoint,
)
from ausb.stream import EndpointStreamReader, EndpointStreamWriter


def verify_endpoint_integration():
    """Verify all endpoint types have the factory methods."""

    mock_device = Mock()

    # Test BulkInEndpoint
    bulk_in = BulkInEndpoint(mock_device, address=0x81, mps=512)
    assert hasattr(bulk_in, 'stream_reader'), "BulkInEndpoint missing stream_reader()"
    reader = bulk_in.stream_reader()
    assert isinstance(reader, EndpointStreamReader), "stream_reader() didn't return EndpointStreamReader"
    print("  BulkInEndpoint.stream_reader() works")

    # Test BulkOutEndpoint
    bulk_out = BulkOutEndpoint(mock_device, address=0x02, mps=512)
    assert hasattr(bulk_out, 'stream_writer'), "BulkOutEndpoint missing stream_writer()"
    writer = bulk_out.stream_writer()
    assert isinstance(writer, EndpointStreamWriter), "stream_writer() didn't return EndpointStreamWriter"
    print("  BulkOutEndpoint.stream_writer() works")

    print("\n  All endpoint types properly support stream wrappers!")


def verify_wrapper_references():
    """Verify that wrappers maintain correct references to endpoints."""

    mock_device = Mock()

    in_ep = BulkInEndpoint(mock_device, address=0x81, mps=512)
    out_ep = BulkOutEndpoint(mock_device, address=0x02, mps=512)

    reader = in_ep.stream_reader()
    writer = out_ep.stream_writer()

    assert reader._endpoint is in_ep, "Reader doesn't reference correct endpoint"
    print("  StreamReader maintains endpoint reference")

    assert writer._endpoint is out_ep, "Writer doesn't reference correct endpoint"
    assert writer.get_extra_info('endpoint') is out_ep, "get_extra_info doesn't return endpoint"
    assert writer.get_extra_info('address') == 0x02, "get_extra_info address mismatch"
    assert writer.get_extra_info('mps') == 512, "get_extra_info mps mismatch"
    print("  StreamWriter maintains endpoint reference")
    print("  get_extra_info() returns correct values")

    print("\n  Wrapper references are correct!")


def verify_bulk_pair():
    """Verify BulkPair basic API."""
    from ausb.handle import BulkPair

    mock_device = Mock()
    ep_out = BulkOutEndpoint(mock_device, address=0x02, mps=512)
    ep_in = BulkInEndpoint(mock_device, address=0x81, mps=512)

    pair = BulkPair(ep_out, ep_in)
    assert pair.out is ep_out
    assert pair.in_ is ep_in
    assert hasattr(pair, 'transfer')
    assert hasattr(pair, '_sync_transfer')
    print("  BulkPair API correct")


def verify_sync_methods():
    """Verify endpoints expose sync methods."""
    mock_device = Mock()

    bulk_in = BulkInEndpoint(mock_device, address=0x81, mps=512)
    assert hasattr(bulk_in, 'read_sync'), "BulkInEndpoint missing read_sync()"
    print("  BulkInEndpoint.read_sync() exists")

    bulk_out = BulkOutEndpoint(mock_device, address=0x02, mps=512)
    assert hasattr(bulk_out, 'write_sync'), "BulkOutEndpoint missing write_sync()"
    print("  BulkOutEndpoint.write_sync() exists")

    int_in = InterruptInEndpoint(mock_device, address=0x83, mps=64, interval=10)
    assert hasattr(int_in, 'read_sync'), "InterruptInEndpoint missing read_sync()"
    print("  InterruptInEndpoint.read_sync() exists")

    int_out = InterruptOutEndpoint(mock_device, address=0x04, mps=64, interval=10)
    assert hasattr(int_out, 'write_sync'), "InterruptOutEndpoint missing write_sync()"
    print("  InterruptOutEndpoint.write_sync() exists")


if __name__ == '__main__':
    print("Verifying integration...\n")
    try:
        verify_endpoint_integration()
        verify_wrapper_references()
        verify_bulk_pair()
        verify_sync_methods()
        print("\n" + "="*60)
        print("SUCCESS: All integration checks passed!")
        print("="*60)
        sys.exit(0)
    except AssertionError as e:
        print(f"\nFAILED: {e}")
        sys.exit(1)
