Quick Start
===========

This guide will help you get started with ausb quickly.

Basic Concepts
--------------

ausb follows the USB hierarchical structure:

* **Context** - Entry point for USB access, manages device enumeration
* **Device** - USB device descriptor (VID/PID, strings, etc.)
* **Handle** - Opened device for communication
* **Interface** - Claimed interface on the device
* **Endpoint** - Communication endpoint for data transfer

All USB operations are asynchronous and integrate with Python's asyncio.

Listing USB Devices
-------------------

List all connected USB devices:

.. code-block:: python

   import asyncio
   import ausb

   async def list_devices():
       async with ausb.Context() as ctx:
           for device in ctx:
               print(f"Bus {device.bus:03d} Device {device.address:03d}: "
                     f"ID {device.vendor_id:04x}:{device.product_id:04x} "
                     f"{device.manufacturer} {device.product}")

   asyncio.run(list_devices())

Finding a Specific Device
-------------------------

Find a device by vendor ID and product ID:

.. code-block:: python

   import asyncio
   import ausb

   async def find_device():
       async with ausb.Context() as ctx:
           # Find device with specific VID:PID
           device = ctx.device_get(vendor_id=0x1234, product_id=0x5678)
           print(f"Found: {device.manufacturer} {device.product}")

   asyncio.run(find_device())

Reading from a Device
---------------------

Open a device, claim an interface, and read from an endpoint:

.. code-block:: python

   import asyncio
   import ausb

   async def read_from_device():
       async with ausb.Context() as ctx:
           # Find and open device
           device_desc = ctx.device_get(vendor_id=0x1234, product_id=0x5678)
           device = device_desc.open()

           # Claim interface 0
           interface = device.interface_claim(0)

           # Open bulk IN endpoint (0x81)
           endpoint = interface.open(
               interface.descriptor.endpoint_by_address(0x81)
           )

           # Read data
           data = await endpoint.read(64)
           print(f"Received {len(data)} bytes: {data.hex()}")

   asyncio.run(read_from_device())

Writing to a Device
-------------------

Write data to an endpoint:

.. code-block:: python

   import asyncio
   import ausb

   async def write_to_device():
       async with ausb.Context() as ctx:
           device_desc = ctx.device_get(vendor_id=0x1234, product_id=0x5678)
           device = device_desc.open()
           interface = device.interface_claim(0)

           # Open bulk OUT endpoint (0x02)
           endpoint = interface.open(
               interface.descriptor.endpoint_by_address(0x02)
           )

           # Write data
           data = b"Hello, USB device!"
           await endpoint.write(data)
           print(f"Sent {len(data)} bytes")

   asyncio.run(write_to_device())

Using Stream Wrappers
---------------------

Use StreamReader/StreamWriter for more Pythonic I/O:

.. code-block:: python

   import asyncio
   import ausb

   async def stream_example():
       async with ausb.Context() as ctx:
           device_desc = ctx.device_get(vendor_id=0x1234, product_id=0x5678)
           device = device_desc.open()
           interface = device.interface_claim(0)

           # Create stream reader
           in_ep = interface.open(interface.descriptor.endpoint_by_address(0x81))
           async with in_ep.stream_reader(buffer_limit=131072) as reader:
               # Read line from device
               line = await reader.readline()
               print(f"Received: {line.decode('utf-8')}")

               # Read exact amount
               data = await reader.readexactly(100)
               print(f"Read exactly {len(data)} bytes")

           # Create stream writer
           out_ep = interface.open(interface.descriptor.endpoint_by_address(0x02))
           writer = out_ep.stream_writer()
           writer.write(b"Hello, device!\n")
           await writer.drain()
           writer.close()
           await writer.wait_closed()

   asyncio.run(stream_example())

Control Transfers
-----------------

Send control requests to a device:

.. code-block:: python

   import asyncio
   import ausb

   async def control_transfer():
       async with ausb.Context() as ctx:
           device_desc = ctx.device_get(vendor_id=0x1234, product_id=0x5678)
           device = device_desc.open()

           # Vendor-specific control request (OUT)
           await device.vendor_control(
               request=0x01,    # Custom request number
               value=0x1234,    # wValue
               index=0,         # wIndex
               data_or_length=b'\x00\x01\x02'  # Data to send
           )

           # Vendor-specific control request (IN)
           response = await device.vendor_control(
               request=0x02,
               value=0,
               index=0,
               data_or_length=64  # Number of bytes to read
           )
           print(f"Response: {response.hex()}")

   asyncio.run(control_transfer())

Monitoring Hotplug Events
--------------------------

Monitor device connection and disconnection events:

.. code-block:: python

   import asyncio
   import ausb

   async def monitor_hotplug():
       async with ausb.Context() as ctx:
           async for event in ctx.hotplug_events():
               if isinstance(event, ausb.ConnectionEvent):
                   device = event.device
                   print(f"Device connected: {device.vendor_id:04x}:{device.product_id:04x}")
               else:
                   print("Device disconnected")

   asyncio.run(monitor_hotplug())

Using with Timeout
------------------

Wrap USB operations with timeouts:

.. code-block:: python

   import asyncio
   import ausb

   async def read_with_timeout():
       async with ausb.Context() as ctx:
           device_desc = ctx.device_get(vendor_id=0x1234, product_id=0x5678)
           device = device_desc.open()
           interface = device.interface_claim(0)
           endpoint = interface.open(
               interface.descriptor.endpoint_by_address(0x81)
           )

           try:
               # Read with 2 second timeout
               data = await asyncio.wait_for(endpoint.read(64), timeout=2.0)
               print(f"Received: {data.hex()}")
           except asyncio.TimeoutError:
               print("Read timeout!")

   asyncio.run(read_with_timeout())

Error Handling
--------------

Handle USB errors gracefully:

.. code-block:: python

   import asyncio
   import ausb
   from ausb.exception import TransferError, TransferTimeout, DeviceError

   async def error_handling():
       async with ausb.Context() as ctx:
           try:
               device = ctx.device_get(vendor_id=0x1234, product_id=0x5678)
               handle = device.open()
               interface = handle.interface_claim(0)

               endpoint = interface.open(
                   interface.descriptor.endpoint_by_address(0x81)
               )
               data = await endpoint.read(64)

           except ValueError:
               print("Device not found!")
           except TransferTimeout:
               print("Transfer timed out")
           except TransferError:
               print("Transfer error occurred")
           except DeviceError:
               print("Device disconnected")

   asyncio.run(error_handling())

Next Steps
----------

* Read the :doc:`user_guide/context` for detailed Context usage
* Learn about :doc:`user_guide/streams` for efficient I/O
* Explore :doc:`user_guide/hotplug` for device monitoring
* Check out the :doc:`examples` for more complex use cases
* Browse the :doc:`api/index` for complete API reference
