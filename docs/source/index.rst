.. ausb documentation master file

Welcome to ausb's documentation!
=================================

**ausb** is a Python 3.5+ asyncio wrapper for libusb-1 that provides asynchronous USB device access.
It wraps the ``usb1`` Python package (which itself wraps libusb-1 via ctypes) to integrate USB
operations into asyncio event loops.

Features
--------

* Full asyncio integration for USB operations
* Support for bulk and interrupt transfers
* Device hotplug event monitoring
* StreamReader/StreamWriter wrappers for USB endpoints
* Comprehensive USB descriptor access
* Control transfer support (standard, class, vendor)
* USB hub control utilities
* Cypress FX2/FX3 firmware loading support

Quick Start
-----------

.. code-block:: python

   import asyncio
   import ausb

   async def main():
       async with ausb.Context() as ctx:
           # Find device by VID/PID
           device = ctx.device_get(vendor_id=0x1234, product_id=0x5678)

           # Open device and claim interface
           handle = device.open()
           interface = handle.interface_claim(0)

           # Open endpoint and create stream reader
           endpoint = interface.open(interface.descriptor.endpoint_by_address(0x81))
           async with endpoint.stream_reader() as reader:
               data = await reader.read(64)
               print(f"Received: {data.hex()}")

   asyncio.run(main())

Installation
------------

.. code-block:: bash

   pip install ausb

Requirements:

* Python 3.5 or later
* libusb-1 (system library)
* usb1 Python package
* asyncclick (for CLI tools)

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   quickstart
   user_guide/context
   user_guide/descriptors
   user_guide/handles
   user_guide/streams
   user_guide/hotplug
   user_guide/utilities

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/context
   api/descriptor
   api/handle
   api/streams
   api/constant
   api/exception
   api/util

.. toctree::
   :maxdepth: 1
   :caption: Additional Information

   examples
   changelog
   contributing
   license

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
