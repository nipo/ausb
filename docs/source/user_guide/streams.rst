Stream Wrappers
===============

ausb provides StreamReader/StreamWriter-compatible wrappers for USB endpoints, allowing you to use
familiar asyncio stream APIs with USB devices.

Why Stream Wrappers?
--------------------

USB endpoints have constraints that make direct reading/writing challenging:

* **IN endpoints** can only be read in multiples of max packet size (MPS)
* Reading arbitrary amounts (like 1 byte or 100 bytes) requires buffering
* Direct USB API is low-level and packet-oriented

Stream wrappers solve these problems by providing:

* **Buffered reading** - Internal buffer allows arbitrary-sized reads
* **Background reading** - Async task keeps buffer filled ahead of time
* **Flow control** - Prevents unbounded memory usage
* **Familiar API** - Standard asyncio StreamReader/StreamWriter interface

EndpointStreamReader
--------------------

The ``EndpointStreamReader`` wraps IN endpoints (bulk or interrupt) with buffering.

Architecture
~~~~~~~~~~~~

.. code-block:: text

   ┌─────────────────────────────────────┐
   │   Your Code                         │
   │   reader.read(100)                  │
   └──────────────┬──────────────────────┘
                  │
                  ▼
   ┌─────────────────────────────────────┐
   │   Internal Buffer                   │
   │   [................data............] │
   └──────────────┬──────────────────────┘
                  ▲
                  │
   ┌──────────────┴──────────────────────┐
   │   Background Reader Task            │
   │   while not closed:                 │
   │     data = await endpoint.read()    │
   │     buffer.append(data)             │
   └──────────────┬──────────────────────┘
                  │
                  ▼
   ┌─────────────────────────────────────┐
   │   USB Endpoint (packet-sized reads) │
   └─────────────────────────────────────┘

Creating a Reader
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Create with default 64KB buffer
   reader = endpoint.stream_reader()

   # Create with custom buffer size
   reader = endpoint.stream_reader(buffer_limit=131072)  # 128KB

   # Use as async context manager
   async with endpoint.stream_reader() as reader:
       data = await reader.read(100)
   # Automatically closed

Buffer Management
~~~~~~~~~~~~~~~~~

The ``buffer_limit`` parameter controls flow control:

* Background reader **pauses** when buffer ≥ ``buffer_limit``
* Background reader **resumes** when buffer < ``buffer_limit / 2``
* Default buffer limit is 64KB (65536 bytes)

Choose buffer size based on:

* **Small buffers** (8-16KB): Low memory usage, more CPU overhead
* **Medium buffers** (64-128KB): Balanced (recommended)
* **Large buffers** (512KB-1MB): High-throughput devices, bulk transfers

Reading Methods
~~~~~~~~~~~~~~~

**read(n=-1)**

Read up to n bytes from buffer:

.. code-block:: python

   # Read up to 64 bytes
   data = await reader.read(64)

   # Read all available buffered data
   data = await reader.read(-1)
   # or
   data = await reader.read()

**readexactly(n)**

Read exactly n bytes, waiting for background task if needed:

.. code-block:: python

   # Read exactly 256 bytes (blocks until available)
   data = await reader.readexactly(256)

   # Raises asyncio.IncompleteReadError on EOF
   try:
       data = await reader.readexactly(1000)
   except asyncio.IncompleteReadError as e:
       print(f"Only got {len(e.partial)} bytes before EOF")

**readline()**

Read until newline (efficient with buffering):

.. code-block:: python

   # Read line from device
   line = await reader.readline()
   text = line.decode('utf-8')

**Iteration**

Iterate over data chunks:

.. code-block:: python

   async for chunk in reader:
       process(chunk)
       if should_stop:
           break

Cleanup
~~~~~~~

Always close the reader when done:

.. code-block:: python

   # Manual cleanup
   reader = endpoint.stream_reader()
   try:
       data = await reader.read(100)
   finally:
       await reader.close()

   # Or use context manager (recommended)
   async with endpoint.stream_reader() as reader:
       data = await reader.read(100)

EndpointStreamWriter
--------------------

The ``EndpointStreamWriter`` wraps OUT endpoints for buffered writing.

Creating a Writer
~~~~~~~~~~~~~~~~~

.. code-block:: python

   writer = endpoint.stream_writer()

Writing Methods
~~~~~~~~~~~~~~~

**write(data)**

Buffer data for writing (synchronous):

.. code-block:: python

   writer.write(b"Hello, ")
   writer.write(b"device!")
   # Data is buffered, not sent yet

**drain()**

Flush buffered data to USB (asynchronous):

.. code-block:: python

   writer.write(b"Hello, device!")
   await writer.drain()  # Actually sends to USB

**writelines(lines)**

Write multiple chunks:

.. code-block:: python

   lines = [b"line1\n", b"line2\n", b"line3\n"]
   writer.writelines(lines)
   await writer.drain()

Cleanup
~~~~~~~

.. code-block:: python

   writer.close()
   await writer.wait_closed()  # Flushes remaining data

Chunking
~~~~~~~~

The writer automatically chunks data by max packet size:

.. code-block:: python

   # Endpoint has MPS=64 bytes
   writer = endpoint.stream_writer()
   writer.write(b"x" * 200)  # 200 bytes
   await writer.drain()
   # Sends as: 64 + 64 + 64 + 8 bytes

Complete Example
----------------

Bidirectional communication using both reader and writer:

.. code-block:: python

   import asyncio
   import ausb

   async def communicate():
       async with ausb.Context() as ctx:
           device = ctx.device_get(vendor_id=0x1234, product_id=0x5678)
           handle = device.open()
           interface = handle.interface_claim(0)

           # Setup reader and writer
           in_ep = interface.open(interface.descriptor.endpoint_by_address(0x81))
           out_ep = interface.open(interface.descriptor.endpoint_by_address(0x02))

           async with in_ep.stream_reader(buffer_limit=65536) as reader:
               writer = out_ep.stream_writer()

               # Send commands and read responses
               for i in range(10):
                   # Send command
                   command = f"QUERY {i}\n".encode()
                   writer.write(command)
                   await writer.drain()

                   # Read response (efficient thanks to buffering)
                   response = await reader.readline()
                   print(f"Response {i}: {response.decode().strip()}")

               # Cleanup
               writer.close()
               await writer.wait_closed()

   asyncio.run(communicate())

Performance Tips
----------------

1. **Use appropriate buffer sizes**

   .. code-block:: python

      # For high-throughput bulk transfers
      reader = endpoint.stream_reader(buffer_limit=1048576)  # 1MB

      # For low-rate interrupt endpoints
      reader = endpoint.stream_reader(buffer_limit=8192)  # 8KB

2. **Batch writes when possible**

   .. code-block:: python

      # Good - batch multiple writes
      for data in chunks:
          writer.write(data)
      await writer.drain()

      # Less efficient - drain after each write
      for data in chunks:
          writer.write(data)
          await writer.drain()  # Avoid this

3. **Use context managers**

   .. code-block:: python

      # Automatic cleanup, prevents resource leaks
      async with endpoint.stream_reader() as reader:
          data = await reader.read(1000)

4. **Choose read method wisely**

   .. code-block:: python

      # For exact amounts
      data = await reader.readexactly(256)

      # For "up to" amounts (returns immediately if data available)
      data = await reader.read(256)

      # For line-oriented protocols
      line = await reader.readline()

Troubleshooting
---------------

**Reader not receiving data**

Make sure the background task started:

.. code-block:: python

   # Background task starts on first read
   reader = endpoint.stream_reader()
   # ... do nothing ...  # Background task NOT started yet

   data = await reader.read(10)  # NOW background task starts

**Memory usage growing**

Reduce buffer_limit:

.. code-block:: python

   # Large buffer might accumulate too much data
   reader = endpoint.stream_reader(buffer_limit=1048576)

   # Try smaller buffer
   reader = endpoint.stream_reader(buffer_limit=65536)

**Reader hanging at close**

Make sure to actually call close:

.. code-block:: python

   # Missing await!
   reader.close()  # Wrong

   await reader.close()  # Correct

See Also
--------

* :doc:`../api/streams` - API reference
* :doc:`handles` - Endpoint handles
* :doc:`context` - Context and device management
