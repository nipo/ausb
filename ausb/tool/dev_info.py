from .. import *
import asyncio

async def ausb_dev_info(loop, vid, pid):
    c = Context(loop)
    device = c.device_get(vendor_id = vid, product_id = pid)
    
    print("Bus %03d Device %03d: ID %04x:%04x v.%03x usb v.%03x speed %d" % (
        device.bus, device.address, device.vendor_id, device.product_id,
        device.device_version, device.usb_version, device.speed))
    print(" Device classes: %02x %02x" % device.classes)
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
