Utilities
=========

ausb includes utility modules for common USB operations.

Cypress FX2/FX3 Support
-----------------------

The ``ausb.util.fx`` module provides support for loading firmware to Cypress FX2 and FX3 devices.

Loading FX2 Firmware
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import asyncio
   import ausb
   from ausb.util.fx import Fx2, Fx2FirmwareImage

   async def load_fx2():
       async with ausb.Context() as ctx:
           # Find FX2 device in boot mode
           device = ctx.device_get(vendor_id=0x04b4, product_id=0x8613)
           handle = device.open()

           # Load firmware
           fx2 = Fx2(handle)
           firmware = Fx2FirmwareImage.load("firmware.ihx")
           await fx2.load(firmware)

           print("Firmware loaded!")

   asyncio.run(load_fx2())

Loading FX3 Firmware
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from ausb.util.fx import Fx3, Fx3FirmwareImage

   async def load_fx3():
       async with ausb.Context() as ctx:
           device = ctx.device_get(vendor_id=0x04b4, product_id=0x00f3)
           handle = device.open()

           fx3 = Fx3(handle)
           firmware = Fx3FirmwareImage.load("firmware.img")
           await fx3.load(firmware)

   asyncio.run(load_fx3())

USB Hub Control
---------------

The ``ausb.util.hub`` module provides utilities for controlling USB hubs.

Enumerating Hubs
~~~~~~~~~~~~~~~~

.. code-block:: python

   import asyncio
   import ausb
   from ausb.util.hub import Enumerator

   async def list_hubs():
       async with ausb.Context() as ctx:
           enumerator = Enumerator(ctx)
           hubs = await enumerator.enumerate()

           for hub in hubs:
               print(f"Hub: {hub.descriptor.manufacturer}")
               print(f"  Ports: {len(hub.ports)}")

   asyncio.run(list_hubs())

Controlling Hub Ports
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def control_ports():
       async with ausb.Context() as ctx:
           enumerator = Enumerator(ctx)
           hubs = await enumerator.enumerate()

           for hub in hubs:
               for port in hub.ports:
                   # Get port status
                   status = await port.status()
                   print(f"Port {port.number}: {status}")

                   # Power control
                   await port.power_off()
                   await asyncio.sleep(1)
                   await port.power_on()

                   # Reset port
                   await port.reset()

   asyncio.run(control_ports())

CLI Tools
---------

ausb includes several command-line utilities:

ausb tree
~~~~~~~~~

Display USB device tree:

.. code-block:: bash

   ausb tree

ausb list
~~~~~~~~~

List USB devices:

.. code-block:: bash

   ausb list

ausb dev-info
~~~~~~~~~~~~~

Get device information:

.. code-block:: bash

   ausb dev-info 1234 5678  # VID:PID

ausb monitor
~~~~~~~~~~~~

Monitor hotplug events:

.. code-block:: bash

   ausb monitor

See Also
--------

* :doc:`../api/util` - API reference for utilities
