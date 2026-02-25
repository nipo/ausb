#!/usr/bin/env python3
"""Tests for handle.py: Device, Interface, Endpoint, BulkPair."""

import asyncio
from unittest.mock import Mock, MagicMock
import usb1
from ausb.handle import (
    Device, Interface, Endpoint, BulkEndpoint,
    BulkInEndpoint, BulkOutEndpoint,
    InterruptInEndpoint, InterruptOutEndpoint,
    BulkPair,
)
from ausb.exception import TransferTimeout, TransferStalled, DeviceError


def make_mock_handle():
    handle = Mock()
    handle.controlRead = Mock(return_value=b'\x00\x00')
    handle.controlWrite = Mock(return_value=0)
    handle.bulkRead = Mock(return_value=b'\xaa\xbb')
    handle.bulkWrite = Mock(return_value=2)
    handle.interruptRead = Mock(return_value=b'\xcc')
    handle.interruptWrite = Mock(return_value=1)
    return handle


def make_device(handle=None):
    handle = handle or make_mock_handle()
    ctx = Mock()
    desc = Mock()
    return Device(ctx, desc, handle)


async def test_device_control():
    """Device.control() uses run_in_executor and calls controlRead/controlWrite."""
    handle = make_mock_handle()
    handle.controlRead.return_value = b'\x01\x02'
    dev = make_device(handle)

    # IN transfer (int data_or_length)
    result = await dev.vendor_control(0xa0, 0x1234, 0, 4)
    assert result == b'\x01\x02'
    handle.controlRead.assert_called_once()

    # OUT transfer (bytes data_or_length)
    await dev.vendor_control(0xa0, 0x1234, 0, b'\xff')
    handle.controlWrite.assert_called_once()
    print("  Device.control() works")


async def test_device_control_timeout_mapping():
    """Device.control() maps USBErrorTimeout to TransferTimeout."""
    handle = make_mock_handle()
    handle.controlWrite.side_effect = usb1.USBErrorTimeout()
    dev = make_device(handle)

    try:
        await dev.vendor_control(0xa0, 0, 0, b'')
        assert False, "Should have raised"
    except TransferTimeout:
        pass
    print("  Device.control() timeout mapping works")


async def test_bulk_in_read():
    """BulkInEndpoint.read() uses run_in_executor."""
    handle = make_mock_handle()
    handle.bulkRead.return_value = b'\xde\xad'
    dev = make_device(handle)

    ep = BulkInEndpoint(dev, 0x81, 512)
    result = await ep.read(64)
    assert result == b'\xde\xad'
    handle.bulkRead.assert_called_once()
    print("  BulkInEndpoint.read() works")


async def test_bulk_out_write():
    """BulkOutEndpoint.write() uses run_in_executor."""
    handle = make_mock_handle()
    dev = make_device(handle)

    ep = BulkOutEndpoint(dev, 0x02, 512)
    await ep.write(b'\xca\xfe')
    handle.bulkWrite.assert_called_once()
    print("  BulkOutEndpoint.write() works")


def test_bulk_in_read_sync():
    """BulkInEndpoint.read_sync() calls bulkRead directly."""
    handle = make_mock_handle()
    handle.bulkRead.return_value = b'\x11\x22'
    dev = make_device(handle)

    ep = BulkInEndpoint(dev, 0x81, 512)
    result = ep.read_sync(64)
    assert result == b'\x11\x22'
    print("  BulkInEndpoint.read_sync() works")


def test_bulk_out_write_sync():
    """BulkOutEndpoint.write_sync() calls bulkWrite directly."""
    handle = make_mock_handle()
    dev = make_device(handle)

    ep = BulkOutEndpoint(dev, 0x02, 512)
    ep.write_sync(b'\x33\x44')
    handle.bulkWrite.assert_called_once()
    print("  BulkOutEndpoint.write_sync() works")


def test_bulk_pair_sync_transfer():
    """BulkPair._sync_transfer writes then reads."""
    handle = make_mock_handle()
    handle.bulkRead.return_value = b'\xaa\xbb\xcc\xdd'
    dev = make_device(handle)

    ep_out = BulkOutEndpoint(dev, 0x02, 512)
    ep_in = BulkInEndpoint(dev, 0x81, 512)
    pair = BulkPair(ep_out, ep_in)

    result = pair._sync_transfer(b'\x01\x02', 4, None)
    assert result == b'\xaa\xbb\xcc\xdd'
    handle.bulkWrite.assert_called_once()
    handle.bulkRead.assert_called_once()
    print("  BulkPair._sync_transfer() works")


def test_bulk_pair_sync_transfer_no_response():
    """BulkPair._sync_transfer with response_len=0 skips read."""
    handle = make_mock_handle()
    dev = make_device(handle)

    ep_out = BulkOutEndpoint(dev, 0x02, 512)
    ep_in = BulkInEndpoint(dev, 0x81, 512)
    pair = BulkPair(ep_out, ep_in)

    result = pair._sync_transfer(b'\x01\x02', 0, None)
    assert result == b""
    handle.bulkWrite.assert_called_once()
    handle.bulkRead.assert_not_called()
    print("  BulkPair._sync_transfer() no-response works")


async def test_bulk_pair_transfer():
    """BulkPair.transfer() is async via run_in_executor."""
    handle = make_mock_handle()
    handle.bulkRead.return_value = b'\xde\xad\xbe\xef'
    dev = make_device(handle)

    ep_out = BulkOutEndpoint(dev, 0x02, 512)
    ep_in = BulkInEndpoint(dev, 0x81, 512)
    pair = BulkPair(ep_out, ep_in)

    result = await pair.transfer(b'\x01\x02', 4)
    assert result == b'\xde\xad\xbe\xef'
    print("  BulkPair.transfer() async works")


async def test_interrupt_endpoints():
    """InterruptIn/Out endpoints work."""
    handle = make_mock_handle()
    handle.interruptRead.return_value = b'\x55'
    dev = make_device(handle)

    ep_in = InterruptInEndpoint(dev, 0x83, 64, interval=10)
    result = await ep_in.read(8)
    assert result == b'\x55'

    ep_out = InterruptOutEndpoint(dev, 0x04, 64, interval=10)
    await ep_out.write(b'\x66')
    handle.interruptWrite.assert_called_once()

    print("  Interrupt endpoints work")


def test_interface_set_feature_uses_correct_request():
    """Interface.set_feature uses SetFeature, not ClearFeature."""
    from ausb.constant import Request
    # Just verify the code path references Request.SetFeature
    import inspect
    src = inspect.getsource(Interface.set_feature)
    assert 'SetFeature' in src
    assert 'ClearFeature' not in src
    print("  Interface.set_feature uses SetFeature")


def test_endpoint_set_feature_uses_correct_request():
    """Endpoint.set_feature uses SetFeature, not ClearFeature."""
    from ausb.constant import Request
    import inspect
    src = inspect.getsource(Endpoint.set_feature)
    assert 'SetFeature' in src
    assert 'ClearFeature' not in src
    print("  Endpoint.set_feature uses SetFeature")


def test_interface_kernel_driver_calls_handle():
    """Interface.kernel_driver_detach/attach call device.handle methods."""
    handle = make_mock_handle()
    dev = make_device(handle)

    desc = Mock()
    intf = Interface(dev, 0, desc, None)

    intf.kernel_driver_detach()
    handle.detachKernelDriver.assert_called_once_with(0)

    intf.kernel_driver_attach()
    handle.attachKernelDriver.assert_called_once_with(0)
    print("  Interface kernel driver methods call handle correctly")


def run_tests():
    print("Running handle tests...\n")

    # Sync tests
    test_bulk_in_read_sync()
    test_bulk_out_write_sync()
    test_bulk_pair_sync_transfer()
    test_bulk_pair_sync_transfer_no_response()
    test_interface_set_feature_uses_correct_request()
    test_endpoint_set_feature_uses_correct_request()
    test_interface_kernel_driver_calls_handle()

    # Async tests
    asyncio.run(test_device_control())
    asyncio.run(test_device_control_timeout_mapping())
    asyncio.run(test_bulk_in_read())
    asyncio.run(test_bulk_out_write())
    asyncio.run(test_bulk_pair_transfer())
    asyncio.run(test_interrupt_endpoints())

    print("\nAll handle tests passed!")


if __name__ == '__main__':
    run_tests()
