USB Descriptors
===============

ausb provides read-only descriptor objects that mirror the USB hierarchical structure.

Descriptor Hierarchy
--------------------

USB devices have a hierarchical descriptor structure:

.. code-block:: text

   Device
   └── Configuration
       └── Interface
           └── Setting
               └── Endpoint

Accessing Descriptors
---------------------

Device Descriptor
~~~~~~~~~~~~~~~~~

.. code-block:: python

   device = ctx.device_get(vendor_id=0x1234, product_id=0x5678)

   # Device properties
   print(f"VID:PID = {device.vendor_id:04x}:{device.product_id:04x}")
   print(f"Manufacturer: {device.manufacturer}")
   print(f"Product: {device.product}")
   print(f"Serial: {device.serial}")
   print(f"Bus: {device.bus}, Address: {device.address}")
   print(f"Ports: {device.ports}")

Configuration Descriptor
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get configuration by index
   config = device[0]  # First configuration

   # Iterate configurations
   for config in device:
       print(f"Configuration {config.index}")

Interface Descriptor
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get interface by index
   interface = config[0]

   # Interface has multiple alternate settings
   for setting in interface:
       print(f"Setting {setting.alternate}")

Setting Descriptor
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   setting = interface[0]  # First alternate setting

   # Setting properties
   print(f"Class: {setting.class_code}")
   print(f"Subclass: {setting.subclass}")
   print(f"Protocol: {setting.protocol}")

Endpoint Descriptor
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Iterate endpoints in a setting
   for endpoint in setting:
       print(f"Endpoint {endpoint.address:02x}")
       print(f"  Type: {endpoint.type}")
       print(f"  Direction: {endpoint.direction}")
       print(f"  Max packet size: {endpoint.max_packet_size}")

   # Get endpoint by address
   endpoint = setting.endpoint_by_address(0x81)

See Also
--------

* :doc:`../api/descriptor` - API reference
* :doc:`handles` - Opening and using descriptors
