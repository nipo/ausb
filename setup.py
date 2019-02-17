from setuptools import setup, find_packages

setup(
    name = "ausb",
    version = "0.1",
    description = "Asyncio wrapper for libusb-1",
    author = "Nicolas Pouillon",
    author_email = "nipo@ssji.net",
    license = "BSD",
    classifiers = [
        "Development Status :: 4 - Beta",
        "Programming Language :: Python",
    ],
    packages = find_packages(),
    install_requires = ["libusb1"],
)
