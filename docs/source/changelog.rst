Changelog
=========

Version 0.1.0 (Unreleased)
--------------------------

**Features:**

* Initial release of ausb
* Full asyncio integration for USB operations
* Support for bulk and interrupt transfers
* Device hotplug event monitoring
* StreamReader/StreamWriter wrappers for USB endpoints with buffering
* Comprehensive USB descriptor access
* Control transfer support (standard, class, vendor)
* USB hub control utilities
* Cypress FX2/FX3 firmware loading support
* CLI tools for device management

**API:**

* ``ausb.Context`` - Main entry point with asyncio integration
* ``ausb.handle`` - Device, Interface, and Endpoint handles
* ``ausb.descriptor`` - USB descriptor hierarchy
* ``ausb.util.fx`` - Cypress FX2/FX3 support
* ``ausb.util.hub`` - USB hub control
* ``ausb.exception`` - USB transfer exceptions

**Documentation:**

* Complete Sphinx documentation
* User guides for all major features
* API reference for all modules
* Examples and quick start guide
