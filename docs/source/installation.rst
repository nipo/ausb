Installation
============

Requirements
------------

**System Requirements:**

* Python 3.5 or later
* libusb-1.0 (system library)

**Python Dependencies:**

* usb1 - Python wrapper for libusb-1
* asyncclick - For CLI tools (optional)

Installing libusb
-----------------

ausb requires libusb-1.0 to be installed on your system.

Ubuntu/Debian
~~~~~~~~~~~~~

.. code-block:: bash

   sudo apt-get install libusb-1.0-0 libusb-1.0-0-dev

Fedora/RHEL
~~~~~~~~~~~

.. code-block:: bash

   sudo dnf install libusb

macOS
~~~~~

Using Homebrew:

.. code-block:: bash

   brew install libusb

Windows
~~~~~~~

Download and install libusb from the official website:
https://libusb.info/

Or use a package manager like Chocolatey:

.. code-block:: bash

   choco install libusb

Installing ausb
---------------

From PyPI (when available)
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install ausb

From Source
~~~~~~~~~~~

Clone the repository and install in development mode:

.. code-block:: bash

   git clone https://github.com/your-repo/ausb.git
   cd ausb
   pip install -e .

With CLI Tools
~~~~~~~~~~~~~~

To install with CLI utilities:

.. code-block:: bash

   pip install -e .[cli]

Verifying Installation
----------------------

Verify that ausb is correctly installed:

.. code-block:: python

   import ausb
   print(ausb.__doc__)

You can also test the CLI tools:

.. code-block:: bash

   ausb --help
   ausb tree

Permissions
-----------

Linux
~~~~~

On Linux, you may need to set up udev rules to access USB devices without root privileges.

Create a file ``/etc/udev/rules.d/99-usb-permissions.rules``:

.. code-block:: text

   # Allow users in plugdev group to access USB devices
   SUBSYSTEM=="usb", MODE="0666", GROUP="plugdev"

Then reload udev rules:

.. code-block:: bash

   sudo udevadm control --reload-rules
   sudo udevadm trigger

Add your user to the plugdev group:

.. code-block:: bash

   sudo usermod -a -G plugdev $USER

Log out and log back in for the changes to take effect.

macOS
~~~~~

On macOS, you may need to run Python with elevated privileges or disable System Integrity Protection
for certain USB devices. Generally, user-space access is available for most USB devices.

Windows
~~~~~~~

On Windows, you may need to install a WinUSB driver for your device using tools like Zadig:
https://zadig.akeo.ie/

Troubleshooting
---------------

Import Error: No module named 'usb1'
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Make sure usb1 is installed:

.. code-block:: bash

   pip install usb1

ImportError: Unable to load libusb
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This means libusb-1.0 is not installed or not in the library path. Install libusb-1.0
using your system package manager (see above).

Permission Denied when accessing USB device
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See the Permissions section above for your operating system.
