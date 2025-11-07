import asyncclick as click
import asyncio
import logging
import sys
        
@click.group()
@click.option('-v', '--verbose', count = True, help = "More verbosity")
@click.option('-q', '--quiet', count = True, help = "Less verbosity")
@click.pass_context
async def cli(ctx, verbose, quiet):
    base_level = "ERROR"
    base_level_int = logging._nameToLevel[base_level]
    levels = list(sorted(set(logging._levelToName.keys())))
    current = levels.index(base_level_int)
    target = min(max(0, current + quiet - verbose), len(levels)-1)

    handler = logging.StreamHandler()
    root = logging.getLogger('')
    root.addHandler(handler)
    root.setLevel(levels[target])
    if quiet - verbose:
        root.log(levels[target], "Logging level set to %s", logging.getLevelName(levels[target]))
        for level in levels:
            root.log(level, "Sample for level %s", logging._levelToName[level])
    @ctx.call_on_close
    def collect():
        import gc
        gc.collect()
            
@cli.command()
async def tree():
    from . import Context
    from .tool.tree import TreeDumper

    async with Context() as ctx:
        await (await TreeDumper.create(ctx)).dump()
            
@cli.command()
async def monitor():
    from . import Context, ConnectionEvent, DisconnectionEvent

    async with Context() as ctx:
        async for event in ctx.hotplug_events():
            if isinstance(event, ConnectionEvent):
                print(f"Connected:    {event.device}", end="")
                try:
                    product = event.device.product or "(unknown)"
                    manufacturer = event.device.manufacturer or "(unknown)"
                    print(f" - {manufacturer} {product}")
                except:
                    print(" (unable to read descriptor)")
            else:
                print(f"Disconnected: {event.device}")

@cli.command()
@click.argument("vid", type = str)
@click.argument("pid", type = str)
async def dev_info(vid, pid):
    from . import Context

    vid = int(vid, 16)
    pid = int(pid, 16)

    async with Context() as c:
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

@cli.command(name = "list")
async def list_():
    from . import Context

    async with Context() as ctx:
        for device in ctx:
            try:
                product = device.product
                manufacturer = device.manufacturer
            except:
                product = ""
                manufacturer = ""
            print(f"Bus {device.bus:03d} Device {device.address:03d}: ID {device.vendor_id:04x}:{device.product_id:04x} {manufacturer} {product}")

def main():
    cli()
