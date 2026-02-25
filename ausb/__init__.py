__doc__ = """
Asyncio wrapper module for libusb1.

AUsb provides a pythonic interface to USB devices::

  import ausb

  ctx = ausb.Context()
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
"""

from .exception import *
from .context import *
from .stream import EndpointStreamReader, EndpointStreamWriter
from .handle import BulkPair
