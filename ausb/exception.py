import usb1

__all__ = ["Error",
           "TransferError", "TransferTimeout", "TransferStalled",
           "DeviceError", "TransferOverflow",
           "map_usb_error"]

class Error(Exception):
    pass

class TransferError(Error):
    pass
class TransferTimeout(Error):
    pass
class TransferStalled(Error):
    pass
class DeviceError(Error):
    pass
class TransferOverflow(Error):
    pass

def map_usb_error(func, *args, **kwargs):
    """Call func, mapping usb1 exceptions to ausb exceptions."""
    try:
        return func(*args, **kwargs)
    except usb1.USBErrorTimeout:
        raise TransferTimeout()
    except usb1.USBErrorPipe:
        raise TransferStalled()
    except usb1.USBErrorNoDevice:
        raise DeviceError()
    except usb1.USBErrorOverflow:
        raise TransferOverflow()
    except usb1.USBError as e:
        raise TransferError(str(e)) from e
