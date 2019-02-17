from .. import *
import asyncio

async def ausb_list(loop):
    c = Context(loop)
    for d in c:
        try:
            product = d.product
            manufacturer = d.manufacturer
        except:
            product = ""
            manufacturer = ""
        print("Bus %03d Device %03d: ID %04x:%04x %s %s" % (
            d.bus, d.address, d.vendor_id, d.product_id, manufacturer, product))
    
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    t = loop.create_task(ausb_list(loop))
    loop.run_until_complete(t)
