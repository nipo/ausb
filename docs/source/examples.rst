Examples
========

This page contains complete examples demonstrating various ausb features.

Basic Device Communication
--------------------------

Reading and writing data:

.. literalinclude:: ../../examples/stream_example.py
   :language: python
   :caption: Stream-based communication

See the ``examples/`` directory in the repository for more examples.

Common Patterns
---------------

Finding a Device
~~~~~~~~~~~~~~~~

.. code-block:: python

   import asyncio
   import ausb

   async def find_my_device():
       async with ausb.Context() as ctx:
           try:
               device = ctx.device_get(vendor_id=0x1234, product_id=0x5678)
               print(f"Found: {device.product}")
           except ValueError:
               print("Device not found")

   asyncio.run(find_my_device())

Bulk Transfer Loop
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def transfer_loop():
       async with ausb.Context() as ctx:
           device = ctx.device_get(vendor_id=0x1234, product_id=0x5678)
           handle = device.open()
           interface = handle.interface_claim(0)

           in_ep = interface.open(interface.descriptor.endpoint_by_address(0x81))
           out_ep = interface.open(interface.descriptor.endpoint_by_address(0x02))

           async with in_ep.stream_reader() as reader:
               writer = out_ep.stream_writer()

               while True:
                   # Send request
                   writer.write(b"REQUEST\n")
                   await writer.drain()

                   # Read response
                   response = await reader.readline()
                   print(f"Response: {response}")

                   await asyncio.sleep(1)

Request-Response Pattern
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def request_response():
       async with ausb.Context() as ctx:
           device = ctx.device_get(vendor_id=0x1234, product_id=0x5678)
           handle = device.open()

           # Send control request
           response = await handle.vendor_control(
               request=0x01,
               value=0,
               index=0,
               data_or_length=64
           )

           print(f"Device responded: {response.hex()}")

See Also
--------

* Check the ``examples/`` directory in the source repository
* :doc:`user_guide/streams` - Stream wrapper guide
* :doc:`quickstart` - Quick start guide
