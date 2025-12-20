Exceptions
==========

.. automodule:: ausb.exception
   :members:
   :undoc-members:
   :show-inheritance:

Transfer Exceptions
-------------------

.. autoexception:: ausb.exception.TransferError
   :members:
   :undoc-members:
   :show-inheritance:

.. autoexception:: ausb.exception.TransferTimeout
   :members:
   :undoc-members:
   :show-inheritance:

.. autoexception:: ausb.exception.TransferStalled
   :members:
   :undoc-members:
   :show-inheritance:

.. autoexception:: ausb.exception.TransferOverflow
   :members:
   :undoc-members:
   :show-inheritance:

Device Exceptions
-----------------

.. autoexception:: ausb.exception.DeviceError
   :members:
   :undoc-members:
   :show-inheritance:

Exception Hierarchy
-------------------

All ausb exceptions inherit from Python's built-in ``Exception`` class:

.. code-block:: text

   Exception
   ├── TransferError
   ├── TransferTimeout
   ├── TransferStalled
   ├── TransferOverflow
   └── DeviceError

Usage Example
-------------

.. code-block:: python

   import asyncio
   import ausb
   from ausb.exception import TransferTimeout, DeviceError

   async def example():
       async with ausb.Context() as ctx:
           try:
               device = ctx.device_get(vendor_id=0x1234, product_id=0x5678)
               handle = device.open()
               interface = handle.interface_claim(0)
               endpoint = interface.open(
                   interface.descriptor.endpoint_by_address(0x81)
               )

               # This might timeout
               data = await asyncio.wait_for(endpoint.read(64), timeout=1.0)

           except asyncio.TimeoutError:
               print("asyncio timeout")
           except TransferTimeout:
               print("USB transfer timeout")
           except DeviceError:
               print("Device disconnected or error")
