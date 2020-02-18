=======================================================
 Python3.5+ Asyncio wrapper for usb1 module (libusb-1)
=======================================================

This is an asyncio module for accessing USB devices.

Current code base is functional, but API has some rough edges, see
todo_. Use it as a PoC rather than a production-grade API.

Current implementation is a wrapper around `libusb1 <usb1_>`_ python
package (i.e. usb1 module), which itself wraps `libusb-1 <libusb_>`_
library through ctypes.  API tries not to expose this implementation
detail, that may change in the future.

.. contents::

Usage
=====

ausb's Context is the main entry point. It allows to list all devices
on the system.  When Context is created, it registers itself to
asyncio event loop.

Device discovery
----------------

A basic lsusb substitute is as simple as:

.. code:: python

  import asyncio
  import ausb
  
  async def ausb_list(loop):
      ctx = ausb.Context(loop)
      for dev in ctx:
          try:
              product = dev.product
              manufacturer = dev.manufacturer
          except:
              product = ""
              manufacturer = ""
          print("Bus %03d Device %03d: ID %04x:%04x %s %s" % (
              dev.bus, dev.address, dev.vendor_id, dev.product_id,
              manufacturer, product))
      
  if __name__ == "__main__":
      loop = asyncio.get_event_loop()
      t = loop.create_task(ausb_list(loop))
      loop.run_until_complete(t)

Sample:

.. code:: shell

  $ python3 -m ausb.tool.list
  Bus 020 Device 010: ID 05ac:8289 Apple Inc. Bluetooth USB Host Controller
  Bus 020 Device 009: ID 0a5c:4500 Apple Inc. BRCM20702 Hub
  Bus 020 Device 007: ID 05ac:025a Apple Inc. Apple Internal Keyboard / Trackpad

Iteration over the context object retrieves descriptors for all
devices in the system.

Context also allows to retrieve:

* the only matching device by some criteria (exception is raised if
  more than one matches):

  .. code:: python

    my_ft2232hl = ctx.device_get(vendor_id = 0x0403, product_id = 0x6010)

* any of matching devices (device returned not guaranteed if more than
  one matches):

  .. code:: python

    some_hub = ctx.device_get_any(classes = (0x09, 0x00))

Descriptor tree
---------------

For a given device, USB descriptors are organized as a treee, as follows::

  Device Descriptor
    Configuration Descriptor
      Interface Descriptor
        Alternate Settings
          Endpoints

ausb descriptor object model follows this:

.. code:: python

  import asyncio
  import ausb

  async def ausb_dev_info(loop, vid, pid):
      c = ausb.Context(loop)
      device = c.device_get(vendor_id = vid, product_id = pid)
      
      print("Bus %03d Device %03d: ID %04x:%04x v.%03x usb v.%03x speed %d" % (
          device.bus, device.address, device.vendor_id, device.product_id,
          device.device_version, device.usb_version, device.speed))
      print(" Control Endpoint 00, MPS=%d" % (
          device.max_packet_size0))
      for cno, configuration in enumerate(device.configurations):
          print(" Configuration #%d" % (configuration.number))
          for ino, interface in enumerate(configuration):
              print("  Interface #%d" % (ino))
              for sno, setting in enumerate(interface):
                  print("   Alternate Setting %d" % (sno))
                  for endpoint in setting:
                      print("    %s %s Endpoint %02x, MPS=%d, interval=%d" % (endpoint.type.capitalize(), endpoint.direction.capitalize(), endpoint.number, endpoint.max_packet_size, endpoint.interval))
  
  if __name__ == "__main__":
      import sys
      loop = asyncio.get_event_loop()
      t = loop.create_task(ausb_dev_info(loop, int(sys.argv[1], 16), int(sys.argv[2], 16)))
      loop.run_until_complete(t)

Sample usage:

.. code:: shell

  $ python3 -m ausb.tool.dev_info 05ac 025a
  Bus 020 Device 007: ID 05ac:025a v.224 usb v.200 speed 2
   Control Endpoint 00, MPS=8
   Configuration #1
    Interface #0
     Alternate Setting 0
      Interrupt In Endpoint 03, MPS=10, interval=8
    Interface #1
     Alternate Setting 0
      Interrupt In Endpoint 01, MPS=64, interval=2
    Interface #2
     Alternate Setting 0
      Interrupt In Endpoint 04, MPS=8, interval=8

Opening a device
----------------

A device descriptor object (as spawned by Context, either from
iteration or getting device by its IDs) is the entry point for device
access:

.. code:: python

  ctx = Context(loop)
  my_ft2232hl = ctx.device_get(vendor_id = 0x0403, product_id = 0x6010)
  device_handle = my_ft2232hl.open()

Device handle object allows to do control-endpoint requests:

.. code:: python

  # Control OUT
  await device_handle.write(type, request, value, index, data)

  # Control IN
  data = await device_handle.read(type, request, value, index, size)

Device handle also allows to open an interface:

.. code:: python

  interface_handle = device_handle.interface_claim(0)

Endpoint interaction
--------------------

Interface owns the endpoints. Once insterface is claimed and a handle
is retrieved, endpoint handles can be retrieved from endpoint
descriptors.  There are two main possibilities:

* Get endpoints from interface descriptor by their address,

* Walk the Interface/Setting hierarchy.

The fastest way:

.. code:: python

  endpoint_descriptor = interface_handle.descriptor[0].endpoint_by_address(0x81)
  endpoint_handle = interface_handle.open(endpoint_descriptor)

  # OUT transfer (bulk or interrupt)
  await endpoint_handle.write(data)

  # IN transfer (bulk or interrupt)
  data = await endpoint_handle.read(size)

Here, `interface_handle.descriptor` is the InterfaceDescriptor and
`interface_handle.descriptor[0]` is the SettingDescriptor for first
alternate setting in interface

Timeouts, cancellation
----------------------

Timeouts are hidden from the API because they are merged with Asyncio
functionality.  Cancellation on read/write cancels the underlying
transfer, in a way you may write:

.. code:: python

  try:
     data = await asyncio.wait_for(endpoint_handle.read(size), timeout = 1.5)
  except asyncio.TimeoutError:
     data = None

Here, if timeout occurs, IN transfer will be cancelled.

Errors
------

There are 4 exception types that may happen on transfers:

* TransferError happends on generic transfer failure,
* TransferStalled happends when endpoint is stalled,
* DeviceError happens when device disappears during transfer,
* TransferOverflow happens if more data than expected is received.

There is no preset timeout on transfers, so ausb does not spawn
timeout errors on its own.

TODO
====

* Documentation

  * Full API documentation, better pydoc strings.

  * More examples (but needs some commonly-available hardware ?).

* Optimizations

  * Reusing transfer objects.

  * Allowing to pass a writable buffer for read requests.

* Support enhancements

  * Support and API for isochronous endpoints.

  * Proper API for Bulk IN streaming (having a pool of pending
    transfers, calling back some handler on reception).

  * Export protocol constants.

  * Support hotplugging detection.

* Asyncio enhancements

  * Mark more calls as async (device opening ?).

  * Maybe timeout integration is bad (race condition possible: asyncio timeout,
    USB transfer completion, asyncio task cancel, libusb backend
    handling on cancelled transfer).

License
=======

MIT, but you may probably conform to `python-libusb1 <usb1_>`_ and
`libusb-1 <libusb_>`_ licenses as well (LGPL-2.1).

.. _usb1: https://github.com/vpelletier/python-libusb1
.. _libusb: https://libusb.info
