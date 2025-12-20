Utilities
=========

.. automodule:: ausb.util

Cypress FX2/FX3
---------------

.. automodule:: ausb.util.fx
   :members:
   :undoc-members:
   :show-inheritance:

Firmware Image Classes
~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: ausb.util.fx.Fx2FirmwareImage
   :members:
   :undoc-members:
   :special-members: __init__
   :show-inheritance:

.. autoclass:: ausb.util.fx.Fx3FirmwareImage
   :members:
   :undoc-members:
   :special-members: __init__
   :show-inheritance:

Device Helper Classes
~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: ausb.util.fx.Fx2
   :members:
   :undoc-members:
   :special-members: __init__
   :show-inheritance:

.. autoclass:: ausb.util.fx.Fx3
   :members:
   :undoc-members:
   :special-members: __init__
   :show-inheritance:

USB Hub Control
---------------

.. automodule:: ausb.util.hub
   :members:
   :undoc-members:
   :show-inheritance:

Hub Classes
~~~~~~~~~~~

.. autoclass:: ausb.util.hub.Hub
   :members:
   :undoc-members:
   :special-members: __init__
   :show-inheritance:

.. autoclass:: ausb.util.hub.Port
   :members:
   :undoc-members:
   :special-members: __init__
   :show-inheritance:

.. autoclass:: ausb.util.hub.Enumerator
   :members:
   :undoc-members:
   :special-members: __init__
   :show-inheritance:

Usage Examples
--------------

Loading FX2 Firmware
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import asyncio
   import ausb
   from ausb.util.fx import Fx2, Fx2FirmwareImage

   async def load_fx2_firmware():
       async with ausb.Context() as ctx:
           # Find FX2 device
           device = ctx.device_get(vendor_id=0x04b4, product_id=0x8613)
           handle = device.open()

           # Load firmware
           fx2 = Fx2(handle)
           firmware = Fx2FirmwareImage.load("firmware.ihx")
           await fx2.load(firmware)

   asyncio.run(load_fx2_firmware())

Controlling USB Hub Ports
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import asyncio
   import ausb
   from ausb.util.hub import Enumerator

   async def control_hub():
       async with ausb.Context() as ctx:
           # Enumerate all hubs
           enumerator = Enumerator(ctx)
           hubs = await enumerator.enumerate()

           for hub in hubs:
               print(f"Hub: {hub.descriptor.manufacturer}")

               # Control each port
               for port in hub.ports:
                   # Get port status
                   status = await port.status()
                   print(f"  Port {port.number}: {status}")

                   # Power cycle the port
                   await port.power_off()
                   await asyncio.sleep(1)
                   await port.power_on()

   asyncio.run(control_hub())
