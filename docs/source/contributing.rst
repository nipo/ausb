Contributing
============

Contributions to ausb are welcome! This page describes how to contribute to the project.

Getting Started
---------------

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a new branch for your feature or bugfix
4. Make your changes
5. Run tests (when available)
6. Submit a pull request

Development Setup
-----------------

Install in development mode:

.. code-block:: bash

   git clone https://github.com/your-username/ausb.git
   cd ausb
   pip install -e .

Install documentation dependencies:

.. code-block:: bash

   pip install -r docs/requirements.txt

Building Documentation
----------------------

Build the HTML documentation:

.. code-block:: bash

   cd docs
   make html

View the built documentation at ``docs/build/html/index.html``.

Code Style
----------

* Follow PEP 8 style guide
* Use meaningful variable and function names
* Add docstrings to all public functions and classes
* Keep lines under 100 characters when practical

Commit Messages
---------------

* Use clear, descriptive commit messages
* Start with a verb in present tense (e.g., "Add feature" not "Added feature")
* Keep the first line under 72 characters
* Add more details in the body if needed

Testing
-------

When tests are available:

.. code-block:: bash

   pytest

Documentation
-------------

Update documentation when:

* Adding new features
* Changing APIs
* Fixing bugs that affect usage

Submitting Pull Requests
-------------------------

1. Ensure your code follows the style guide
2. Update documentation as needed
3. Add tests for new features (when test framework is available)
4. Ensure all tests pass
5. Submit a pull request with a clear description

Bug Reports
-----------

When reporting bugs, include:

* ausb version
* Python version
* Operating system
* libusb version
* Steps to reproduce
* Expected behavior
* Actual behavior
* Any error messages

Feature Requests
----------------

Feature requests are welcome! Please describe:

* The problem you're trying to solve
* Your proposed solution
* Any alternative solutions you've considered
* Additional context

License
-------

By contributing to ausb, you agree that your contributions will be licensed under the same license
as the project (MIT License).

Questions?
----------

If you have questions about contributing, open an issue on GitHub.
