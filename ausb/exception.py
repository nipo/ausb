__all__ = ["Error",
           "TransferError", "TransferTimeout", "TransferStalled",
           "DeviceError", "TransferOverflow"]

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
