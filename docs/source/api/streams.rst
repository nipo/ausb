Stream Wrappers
===============

.. automodule:: ausb.handle
   :noindex:

EndpointStreamReader
--------------------

.. autoclass:: ausb.handle.EndpointStreamReader
   :members:
   :undoc-members:
   :special-members: __init__, __aenter__, __aexit__, __aiter__, __anext__
   :show-inheritance:

Overview
~~~~~~~~

The ``EndpointStreamReader`` provides an asyncio StreamReader-compatible interface for reading
from USB IN endpoints. It uses an internal buffer and background task to handle the USB constraint
that endpoints can only be read in multiples of max packet size.

**Key Features:**

* Internal buffering for arbitrary-sized reads
* Background task for continuous USB reading
* Flow control to prevent unbounded memory usage
* Lazy initialization (background task starts on first read)
* Async context manager support

**Buffer Management:**

The reader maintains an internal buffer that is filled by a background asyncio task. When the
buffer size exceeds ``buffer_limit``, the background reader pauses. Reading resumes when the
buffer drops below ``buffer_limit/2`` (low water mark).

**Usage Example:**

.. code-block:: python

   async with endpoint.stream_reader(buffer_limit=131072) as reader:
       # Read arbitrary amounts
       data = await reader.read(100)

       # Read exactly N bytes (waits for background task if needed)
       exact = await reader.readexactly(256)

       # Readline is efficient with buffering
       line = await reader.readline()

EndpointStreamWriter
--------------------

.. autoclass:: ausb.handle.EndpointStreamWriter
   :members:
   :undoc-members:
   :special-members: __init__
   :show-inheritance:

Overview
~~~~~~~~

The ``EndpointStreamWriter`` provides an asyncio StreamWriter-compatible interface for writing
to USB OUT endpoints.

**Key Features:**

* Buffering for efficient bulk writes
* Automatic chunking by max packet size
* Compatible with standard asyncio StreamWriter API

**Usage Example:**

.. code-block:: python

   writer = endpoint.stream_writer()
   writer.write(b"Hello, device!\\n")
   await writer.drain()
   writer.close()
   await writer.wait_closed()

Factory Methods
---------------

Stream wrappers are created using factory methods on endpoint objects:

.. code-block:: python

   # For IN endpoints
   reader = bulk_in_endpoint.stream_reader(buffer_limit=65536)
   reader = interrupt_in_endpoint.stream_reader(buffer_limit=65536)

   # For OUT endpoints
   writer = bulk_out_endpoint.stream_writer()
   writer = interrupt_out_endpoint.stream_writer()

See Also
--------

* :doc:`../user_guide/streams` - Detailed guide on using stream wrappers
* :doc:`handle` - Endpoint handle documentation
