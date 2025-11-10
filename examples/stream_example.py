#!/usr/bin/env python3
"""
Example demonstrating EndpointStreamReader and EndpointStreamWriter usage.

This example shows how to use the asyncio StreamReader/StreamWriter compatible
wrappers for USB endpoints with buffering and flow control.
"""

import asyncio
import ausb


async def stream_reader_example():
    """Example using EndpointStreamReader for reading from a USB device."""
    async with ausb.Context() as ctx:
        # Find your device (adjust VID/PID as needed)
        dev_desc = ctx.device_get(vendor_id=0x1234, product_id=0x5678)
        dev_handle = dev_desc.open()

        # Claim interface
        intf = dev_handle.interface_claim(0)

        # Get IN endpoint and create a stream reader with custom buffer
        ep_desc = intf.descriptor.endpoint_by_address(0x81)
        ep = intf.open(ep_desc)

        # Use async context manager for automatic cleanup
        # buffer_limit controls memory usage and flow control
        async with ep.stream_reader(buffer_limit=131072) as reader:
            # Read data using StreamReader API
            # Background task continuously fills buffer
            data = await reader.read(64)
            print(f"Read {len(data)} bytes: {data.hex()}")

            # Read exactly N bytes (waits for background task to fill buffer)
            exact_data = await reader.readexactly(100)
            print(f"Read exactly {len(exact_data)} bytes")

            # Readline is efficient thanks to buffering
            line = await reader.readline()
            print(f"Line: {line.decode('utf-8', errors='ignore')}")

            # Iterate over data chunks
            count = 0
            async for chunk in reader:
                print(f"Received chunk {count}: {len(chunk)} bytes")
                count += 1
                if count >= 10:  # Process 10 chunks then stop
                    break

        # Reader automatically closed when exiting context


async def stream_writer_example():
    """Example using EndpointStreamWriter for writing to a USB device."""
    async with ausb.Context() as ctx:
        # Find your device (adjust VID/PID as needed)
        dev_desc = ctx.device_get(vendor_id=0x1234, product_id=0x5678)
        dev_handle = dev_desc.open()

        # Claim interface
        intf = dev_handle.interface_claim(0)

        # Get OUT endpoint and create a stream writer
        ep_desc = intf.descriptor.endpoint_by_address(0x02)
        ep = intf.open(ep_desc)
        writer = ep.stream_writer()

        # Write data (buffered)
        writer.write(b"Hello, USB device!\n")
        writer.write(b"This is a test.\n")

        # Flush to actually send
        await writer.drain()

        # Write multiple lines
        writer.writelines([b"Line 1\n", b"Line 2\n", b"Line 3\n"])
        await writer.drain()

        # Close when done
        writer.close()
        await writer.wait_closed()


async def bidirectional_example():
    """Example using both reader and writer for bidirectional communication."""
    async with ausb.Context() as ctx:
        # Find your device
        dev_desc = ctx.device_get(vendor_id=0x1234, product_id=0x5678)
        dev_handle = dev_desc.open()

        # Claim interface
        intf = dev_handle.interface_claim(0)

        # Open both IN and OUT endpoints
        in_ep_desc = intf.descriptor.endpoint_by_address(0x81)
        out_ep_desc = intf.descriptor.endpoint_by_address(0x02)

        in_ep = intf.open(in_ep_desc)
        out_ep = intf.open(out_ep_desc)

        # Use context managers for automatic cleanup
        async with in_ep.stream_reader(buffer_limit=65536) as reader:
            writer = out_ep.stream_writer()

            # Send a command
            writer.write(b"GET_STATUS\n")
            await writer.drain()

            # Read response (readline is efficient with buffering)
            response = await reader.readline()
            print(f"Device response: {response.decode('utf-8', errors='ignore')}")

            # Send more commands and read responses
            for i in range(10):
                writer.write(f"COMMAND_{i}\n".encode())
                await writer.drain()

                # Background reader keeps buffer filled
                response = await reader.readline()
                print(f"Response {i}: {response.decode('utf-8', errors='ignore').strip()}")

            # Clean up writer
            writer.close()
            await writer.wait_closed()

        # Reader automatically closed when exiting context


if __name__ == "__main__":
    # Run one of the examples
    asyncio.run(stream_writer_example())
