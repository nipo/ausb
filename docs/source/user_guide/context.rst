Context and Device Management
==============================

The ``Context`` class is the entry point for all USB operations in ausb. It manages device
enumeration, hotplug events, and integrates with the asyncio event loop.

Creating a Context
------------------

Always use the async context manager to ensure proper cleanup:

.. code-block:: python

   import asyncio
   import ausb

   async def main():
       async with ausb.Context() as ctx:
           # Use context here
           for device in ctx:
               print(device)

   asyncio.run(main())

The context must be explicitly closed or used as a context manager, otherwise the asyncio event
loop may hang due to the background ContextNotifier task.

Asyncio Integration
-------------------

The ``Context`` integrates with asyncio through the ``ContextNotifier`` class, which:

1. Registers libusb file descriptors with asyncio's event loop
2. Calls ``handleEventsTimeout()`` when FDs are ready
3. Triggers asyncio future resolution in transfer callbacks

This allows all USB operations to be fully asynchronous.

Finding Devices
---------------

By Vendor/Product ID
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get exactly one device (raises ValueError if not found or multiple matches)
   device = ctx.device_get(vendor_id=0x1234, product_id=0x5678)

   # Get any matching device
   device = ctx.device_get_any(vendor_id=0x1234)

By Other Criteria
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # By bus and address
   device = ctx.device_get(bus=1, address=5)

   # By bus and port path
   device = ctx.device_get(bus=1, ports=(1, 2, 3))

Iterating All Devices
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   for device in ctx:
       print(f"{device.vendor_id:04x}:{device.product_id:04x} - {device.product}")

Filtering Devices
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Iterate matching devices
   for device in ctx.device_filter(vendor_id=0x1234):
       print(device.product)

Opening Devices
---------------

Once you have a device descriptor, open it to get a handle:

.. code-block:: python

   device_desc = ctx.device_get(vendor_id=0x1234, product_id=0x5678)
   device_handle = device_desc.open()

The device handle is used for all communication with the device.

See Also
--------

* :doc:`../api/context` - API reference
* :doc:`descriptors` - USB descriptors
* :doc:`hotplug` - Device hotplug events
