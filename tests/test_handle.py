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


def make_fake_transfer(reply: bytes = b"", actual_length: int | None = None,
                       status: int = usb1.TRANSFER_COMPLETED):
    """Create a stub libusb transfer that replays a canned reply
    (for IN) or just records what it was given (for OUT). On
    ``submit()`` it immediately invokes the registered callback
    with itself so the awaiting Future resolves synchronously —
    no event-thread bridging needed in unit tests."""
    transfer = Mock()
    transfer._captured_args = None
    transfer._reply = reply
    transfer._status = status

    def _setBulk(address, buffer_or_size, callback=None, timeout=None):
        transfer._captured_args = ("bulk", address, buffer_or_size,
                                   callback, timeout)
    def _setInterrupt(address, buffer_or_size, callback=None, timeout=None):
        transfer._captured_args = ("interrupt", address, buffer_or_size,
                                   callback, timeout)

    def _submit():
        kind, address, buffer_or_size, callback, timeout = transfer._captured_args
        if isinstance(buffer_or_size, int):
            transfer.getActualLength.return_value = (
                actual_length if actual_length is not None else len(reply))
            transfer.getBuffer.return_value = bytearray(
                reply.ljust(buffer_or_size, b"\x00"))
        else:
            transfer.getActualLength.return_value = (
                actual_length if actual_length is not None else len(buffer_or_size))
            transfer.getBuffer.return_value = bytearray(buffer_or_size)
        transfer.getStatus.return_value = transfer._status
        callback(transfer)

    transfer.setBulk = Mock(side_effect=_setBulk)
    transfer.setInterrupt = Mock(side_effect=_setInterrupt)
    transfer.submit = Mock(side_effect=_submit)
    return transfer


def make_mock_handle(*replies):
    """Mock USB device handle. ``replies`` is a sequence of bytes
    objects served (in order) to async transfer reads; sync
    bulkRead / interruptRead fall back to a fixed legacy stub."""
    handle = Mock()
    handle.controlRead = Mock(return_value=b'\x00\x00')
    handle.controlWrite = Mock(return_value=0)
    handle.bulkRead = Mock(return_value=b'\xaa\xbb')
    handle.bulkWrite = Mock(return_value=2)
    handle.interruptRead = Mock(return_value=b'\xcc')
    handle.interruptWrite = Mock(return_value=1)

    queue = list(replies)
    handle._fake_transfers = []

    def _getTransfer(*args, **kwargs):
        reply = queue.pop(0) if queue else b""
        t = make_fake_transfer(reply)
        handle._fake_transfers.append(t)
        return t
    handle.getTransfer = Mock(side_effect=_getTransfer)
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
    """BulkInEndpoint.read() submits an async transfer and resolves
    the awaiting Future from libusb's completion callback."""
    handle = make_mock_handle(b'\xde\xad')
    dev = make_device(handle)

    ep = BulkInEndpoint(dev, 0x81, 512)
    result = await ep.read(64)
    assert result == b'\xde\xad'
    handle.getTransfer.assert_called_once()
    transfer = handle._fake_transfers[0]
    transfer.setBulk.assert_called_once()
    transfer.submit.assert_called_once()
    print("  BulkInEndpoint.read() works")


async def test_bulk_out_write():
    """BulkOutEndpoint.write() submits an async OUT transfer."""
    handle = make_mock_handle()
    dev = make_device(handle)

    ep = BulkOutEndpoint(dev, 0x02, 512)
    written = await ep.write(b'\xca\xfe')
    assert written == 2
    handle.getTransfer.assert_called_once()
    transfer = handle._fake_transfers[0]
    transfer.setBulk.assert_called_once()
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
    """BulkPair.transfer() submits OUT and IN concurrently via
    asyncio.gather; both run as async libusb transfers."""
    # First getTransfer call serves the OUT (no reply), second serves
    # the IN (canned reply). gather submits both; in the test stub
    # both fire their callbacks immediately.
    handle = make_mock_handle(b"", b'\xde\xad\xbe\xef')
    dev = make_device(handle)

    ep_out = BulkOutEndpoint(dev, 0x02, 512)
    ep_in = BulkInEndpoint(dev, 0x81, 512)
    pair = BulkPair(ep_out, ep_in)

    result = await pair.transfer(b'\x01\x02', 4)
    assert result == b'\xde\xad\xbe\xef'
    assert handle.getTransfer.call_count == 2
    print("  BulkPair.transfer() async works")


async def test_interrupt_endpoints():
    """InterruptIn/Out endpoints work via async libusb transfers."""
    handle = make_mock_handle(b'\x55', b"")
    dev = make_device(handle)

    ep_in = InterruptInEndpoint(dev, 0x83, 64, interval=10)
    result = await ep_in.read(8)
    assert result == b'\x55'

    ep_out = InterruptOutEndpoint(dev, 0x04, 64, interval=10)
    written = await ep_out.write(b'\x66')
    assert written == 1
    assert handle.getTransfer.call_count == 2
    # Second transfer was the OUT.
    assert handle._fake_transfers[1].setInterrupt.called
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
