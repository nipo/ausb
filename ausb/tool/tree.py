from .. import *
import usb1
import asyncio
from ..util.hub import *

async def device_dump(device):
    pfx = "    " * len(device.ports)
    
    try:
        handle = device.open()
    except:
        return

    try:
        product = device.product
        manufacturer = device.manufacturer
    except:
        product = ""
        manufacturer = ""

    print("%s%04x:%04x %s %s" % (
        pfx,
        device.vendor_id, device.product_id,
        manufacturer, product))

    if device.classes != (9, 0):
        return

    try:
        hub = await Hub.create(handle)
    except NotImplementedError:
        return

    ps, _ = await hub.status_get()
    print("%s  Hub Status %s" % (pfx, ps))

    for port in hub:
        ps, _ = await port.status_get()
        print("%s  * Port %d (%s) %s" % (pfx, port.index, "removable" if port.removable else "fixed", ps))

        try:
            child = device.context.device_get(ports = port.ports, bus = device.bus)
        except ValueError:
            continue

        await device_dump(child)

async def ausb_list(loop):
    c = Context(loop)
    for d in sorted(c.device_filter(ports = []), key = lambda x:x.bus):
        if d.port:
            continue
        await device_dump(d)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    t = loop.create_task(ausb_list(loop))
    loop.run_until_complete(t)
