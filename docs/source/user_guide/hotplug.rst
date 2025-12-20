Hotplug Events
==============

ausb supports monitoring USB device connection and disconnection events through an async iterator.

Basic Usage
-----------

.. code-block:: python

   import asyncio
   import ausb

   async def monitor_devices():
       async with ausb.Context() as ctx:
           async for event in ctx.hotplug_events():
               if isinstance(event, ausb.ConnectionEvent):
                   device = event.device
                   print(f"Connected: {device.vendor_id:04x}:{device.product_id:04x}")
               else:
                   print("Device disconnected")

   asyncio.run(monitor_devices())

Event Types
-----------

ConnectionEvent
~~~~~~~~~~~~~~~

Fired when a device is connected:

.. code-block:: python

   if isinstance(event, ausb.ConnectionEvent):
       device = event.device
       # Access device descriptor
       print(device.manufacturer, device.product)

DisconnectionEvent
~~~~~~~~~~~~~~~~~~

Fired when a device is disconnected:

.. code-block:: python

   if isinstance(event, ausb.DisconnectionEvent):
       print("A device was disconnected")

Multiple Iterators
------------------

You can have multiple hotplug iterators on the same context - all receive the same events:

.. code-block:: python

   async def monitor1():
       async for event in ctx.hotplug_events():
           print(f"Monitor 1: {event}")

   async def monitor2():
       async for event in ctx.hotplug_events():
           print(f"Monitor 2: {event}")

   # Both monitors receive all events
   await asyncio.gather(monitor1(), monitor2())

Filtering Events
----------------

You can filter events by device properties:

.. code-block:: python

   async for event in ctx.hotplug_events():
       if isinstance(event, ausb.ConnectionEvent):
           device = event.device
           if device.vendor_id == 0x1234:
               print(f"Our device connected: {device.product}")

Using Context Manager
---------------------

The hotplug iterator supports async context manager for cleanup:

.. code-block:: python

   async with ctx.hotplug_events() as events:
       async for event in events:
           process(event)

Disabling Hotplug
-----------------

You can disable hotplug support when creating the context:

.. code-block:: python

   ctx = ausb.Context(enable_hotplug=False)

See Also
--------

* :doc:`../api/context` - API reference for Context and hotplug events
* :doc:`context` - Context management
