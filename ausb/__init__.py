__doc__ = """
Asyncio wrapper module for libusb1.

AUsb provides a pythonic interface to USB devices::

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
"""

from .exception import *
from .context import *
