#!/usr/bin/env python3
"""Tests for exception mapping helper."""

import usb1
from ausb.exception import (
    map_usb_error,
    TransferTimeout, TransferStalled, DeviceError,
    TransferOverflow, TransferError,
)


def test_map_usb_error_success():
    """map_usb_error returns value on success."""
    result = map_usb_error(lambda: 42)
    assert result == 42
    print("  map_usb_error success")


def test_map_usb_error_timeout():
    def raise_timeout():
        raise usb1.USBErrorTimeout()
    try:
        map_usb_error(raise_timeout)
        assert False, "Should have raised"
    except TransferTimeout:
        pass
    print("  map_usb_error timeout")


def test_map_usb_error_pipe():
    def raise_pipe():
        raise usb1.USBErrorPipe()
    try:
        map_usb_error(raise_pipe)
        assert False, "Should have raised"
    except TransferStalled:
        pass
    print("  map_usb_error pipe -> stalled")


def test_map_usb_error_no_device():
    def raise_no_device():
        raise usb1.USBErrorNoDevice()
    try:
        map_usb_error(raise_no_device)
        assert False, "Should have raised"
    except DeviceError:
        pass
    print("  map_usb_error no device")


def test_map_usb_error_overflow():
    def raise_overflow():
        raise usb1.USBErrorOverflow()
    try:
        map_usb_error(raise_overflow)
        assert False, "Should have raised"
    except TransferOverflow:
        pass
    print("  map_usb_error overflow")


def test_map_usb_error_other():
    def raise_other():
        raise usb1.USBErrorIO()
    try:
        map_usb_error(raise_other)
        assert False, "Should have raised"
    except TransferError:
        pass
    print("  map_usb_error other -> TransferError")


def test_map_usb_error_passes_args():
    def add(a, b, extra=0):
        return a + b + extra
    result = map_usb_error(add, 1, 2, extra=10)
    assert result == 13
    print("  map_usb_error passes args/kwargs")


if __name__ == '__main__':
    print("Running exception tests...\n")
    test_map_usb_error_success()
    test_map_usb_error_timeout()
    test_map_usb_error_pipe()
    test_map_usb_error_no_device()
    test_map_usb_error_overflow()
    test_map_usb_error_other()
    test_map_usb_error_passes_args()
    print("\nAll exception tests passed!")
