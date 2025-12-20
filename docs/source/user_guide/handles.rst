Handles and Transfers
=====================

Handles represent opened USB resources for communication. ausb provides handles for devices,
interfaces, and endpoints.

Device Handles
--------------

Open a device descriptor to get a device handle:

.. code-block:: python

   device_desc = ctx.device_get(vendor_id=0x1234, product_id=0x5678)
   device_handle = device_desc.open()

Device Handle Operations
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Configuration
   current_config = device_handle.configuration
   device_handle.configuration = 1

   # String descriptors
   print(device_handle.manufacturer)
   print(device_handle.product)
   print(device_handle.serial)

   # Device reset
   device_handle.reset()

   # Reopen after reset (using bus/port path)
   device_handle.reopen()

Control Transfers
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Vendor-specific control OUT
   await device_handle.vendor_control(
       request=0x01,
       value=0x1234,
       index=0,
       data_or_length=b'\x00\x01\x02'
   )

   # Vendor-specific control IN
   response = await device_handle.vendor_control(
       request=0x02,
       value=0,
       index=0,
       data_or_length=64  # bytes to read
   )

   # Class control transfer
   await device_handle.class_control(request=0x20, value=0, index=0, data_or_length=b'')

   # Standard control transfer
   await device_handle.standard_control(request=0x00, value=0, index=0, data_or_length=2)

Interface Handles
-----------------

Claim an interface to communicate with it:

.. code-block:: python

   interface = device_handle.interface_claim(0)  # Interface 0

   # Alternate setting
   interface.alternate = 1

   # Kernel driver management
   interface.kernel_driver_detach()
   interface.kernel_driver_attach()

Endpoint Handles
----------------

Open an endpoint from the interface:

.. code-block:: python

   # Get endpoint descriptor
   endpoint_desc = interface.descriptor.endpoint_by_address(0x81)

   # Open endpoint
   endpoint = interface.open(endpoint_desc)

Bulk Transfers
~~~~~~~~~~~~~~

.. code-block:: python

   # Bulk IN
   data = await bulk_in_endpoint.read(512)

   # Bulk OUT
   await bulk_out_endpoint.write(b'data to send')

Interrupt Transfers
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Interrupt IN (respects MPS limit)
   data = await interrupt_in_endpoint.read(64)

   # Interrupt OUT (respects MPS limit)
   await interrupt_out_endpoint.write(b'data')

Error Handling
--------------

.. code-block:: python

   from ausb.exception import TransferTimeout, TransferStalled, DeviceError

   try:
       data = await endpoint.read(64)
   except TransferTimeout:
       print("Transfer timed out")
   except TransferStalled:
       print("Endpoint stalled")
       endpoint.resume()  # Clear halt
   except DeviceError:
       print("Device disconnected")

See Also
--------

* :doc:`../api/handle` - API reference
* :doc:`streams` - Stream wrappers for easier I/O
* :doc:`../api/exception` - Exception types
