from .. import *
import asyncio
import sys
import signal
from ..util import fx
import functools

async def fx3_load(loop, bus, address, firmware_filename):
    c = Context(loop)
    dd = c.device_get(bus = bus, address = address)
    device = dd.open()
    fx3 = fx.Fx3(device)
    firmware = fx.FirmwareImage.from_file(firmware_filename)
    await fx3.firmware_load(firmware)

def stopper(signame, loop):
    for task in asyncio.Task.all_tasks():
        task.cancel()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    for signame in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(getattr(signal, signame),
                                functools.partial(stopper, signame, loop))
    
    t = loop.create_task(fx3_load(loop,
                                  int(sys.argv[1], 10),
                                  int(sys.argv[2], 10),
                                  sys.argv[3]))
    loop.run_until_complete(t)
