# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ausb** is a Python asyncio wrapper for libusb-1 that provides asynchronous USB device access. It wraps the `usb1` Python package (which itself wraps libusb-1 via ctypes) using `asyncio.run_in_executor()` for non-blocking I/O.

## Installation and Setup

```bash
# Install the package in development mode
pip install -e .

# Dependencies: libusb1, asyncclick
```

## Running Commands

### CLI Entry Point
The main CLI is accessible via `ausb`:

```bash
ausb tree        # Show USB device tree
ausb list        # Basic device listing
ausb dev-info 05ac 025a  # Get device info by VID:PID
ausb monitor     # Monitor hotplug events
```

### Tests
```bash
python tests/test_exception.py
python tests/test_handle.py
python tests/test_streams.py
python tests/test_streams_simple.py
python tests/verify_integration.py
python tests/test_context_cleanup.py  # requires USB hardware
```

## Architecture

### Async Integration

All USB I/O uses `asyncio.run_in_executor()` wrapping synchronous libusb calls (`bulkRead`, `bulkWrite`, `controlTransfer`, etc.). Each USB transfer is a self-contained sync call in a worker thread. No FD polling, no `handleEventsTimeout()`, no transfer callbacks.

Endpoints expose both async and sync interfaces:
- `read()` / `write()` — async, for normal use
- `read_sync()` / `write_sync()` — sync, for composing custom transfer patterns inside `run_in_executor`

### Core Object Model

```
Context (ausb/context.py)
  └─ Device Descriptor (ausb/descriptor.py: Device)
      └─ Configuration Descriptor (ausb/descriptor.py: Configuration)
          └─ Interface Descriptor (ausb/descriptor.py: Interface)
              └─ Setting Descriptor (ausb/descriptor.py: Setting)
                  └─ Endpoint Descriptor (ausb/descriptor.py: Endpoint)
```

### Key Components

#### 1. Context (ausb/context.py)
- Main entry point for USB access
- Wraps `usb1.USBContext`
- Device filtering and enumeration: `device_filter()`, `device_get()`, `device_get_any()`
- Hotplug via daemon thread calling `handleEventsTimeout()` in a loop
- Hotplug callbacks use `loop.call_soon_threadsafe()` to post events to asyncio
- `close()` is sync — stops hotplug thread, closes usb1 context
- Supports both sync and async context manager protocol

#### 2. Descriptors (ausb/descriptor.py)
Read-only descriptor objects mirroring USB hierarchy. Call `.open()` on Device descriptor to get a handle (exceptions propagate, no silent swallowing).

#### 3. Handles (ausb/handle.py)
Active device/interface/endpoint handles for data transfer:
- **Device**: Control transfers via `run_in_executor`, interface claiming, device reset
- **Interface**: Interface-level control transfers, endpoint opening
- **BulkInEndpoint / BulkOutEndpoint**: `read()`/`write()` async, `read_sync()`/`write_sync()` for executor composition
- **InterruptInEndpoint / InterruptOutEndpoint**: Same pattern
- **BulkPair**: Atomic write+read in single executor call for command/response protocols

Exception mapping: `map_usb_error()` in exception.py converts usb1 exceptions to ausb exceptions.

#### 4. Streams (ausb/stream.py)
- **EndpointStreamReader**: asyncio StreamReader-compatible, background task buffers USB reads
- **EndpointStreamWriter**: asyncio StreamWriter-compatible, chunks writes by MPS

#### 5. Utilities
- **ausb/util/fx.py**: Cypress FX2/FX3 firmware loading
- **ausb/util/hub.py**: USB hub enumeration and port control

### Exception Hierarchy (ausb/exception.py)

```
Error
  └─ TransferError (generic)
  └─ TransferTimeout (USBErrorTimeout)
  └─ TransferStalled (USBErrorPipe)
  └─ DeviceError (USBErrorNoDevice)
  └─ TransferOverflow (USBErrorOverflow)
```

`map_usb_error(func, *args, **kwargs)` — call func, mapping usb1 exceptions to ausb exceptions.

## Code Patterns

### Opening a Device

```python
import ausb

async def example():
    ctx = ausb.Context(enable_hotplug=False)
    dev_desc = ctx.device_get(vendor_id=0x1234, product_id=0x5678)
    device = dev_desc.open()
    intf = device.interface_claim(0)
    ep = intf.open(intf.descriptor[0])
    data = await ep.read(64)
    ctx.close()
```

### BulkPair for Command/Response

```python
from ausb.handle import BulkOutEndpoint, BulkInEndpoint, BulkPair

ep_out = BulkOutEndpoint(device, 0x02, 512)
ep_in = BulkInEndpoint(device, 0x81, 512)
pair = BulkPair(ep_out, ep_in)

# Atomic write+read (single executor call)
response = await pair.transfer(command_bytes, response_len)

# Or compose custom patterns with sync methods:
async def custom_transfer(pair, data, response_len):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync, pair, data, response_len)

def _sync(pair, data, response_len):
    pair.out.write_sync(data)
    # Custom read logic here
    return pair.in_.read_sync(response_len)
```

### Control Transfers

Direction is automatic: `int` for IN (length), `bytes` for OUT (data).

```python
await device.vendor_control(request, value, index, data_or_length)
```

## Development Notes

- License is MIT (also check libusb-1 and python-libusb1 licenses: LGPL-2.1)
- Default timeout: 1000ms per endpoint, overridable per call
