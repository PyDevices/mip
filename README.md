# PyDevices MIP package index

This micropython-lib fork builds an installable package index containing both
precompiled `.mpy` bytecode and raw `.py` source at:

```text
https://PyDevices.github.io/mip
```

This repository documents the package manager itself. Product repositories
document which product or board package to choose.

## Install from a network-enabled MicroPython device

```python
import mip

mip.install("package-name", index="https://PyDevices.github.io/mip")
```

`mip` installs into the runtime's default library destination unless `target`
is supplied. Use `mpy=False` to request portable `.py` source instead of
MicroPython bytecode.

```python
mip.install(
    "package-name",
    index="https://PyDevices.github.io/mip",
    target="lib",
    mpy=False,
)
```

## Install with the MicroPython command line

Hosted MicroPython ports can run the package manager as a module:

```bash
micropython -m mip install \
  --index https://PyDevices.github.io/mip \
  package-name
```

Use `--target lib` for an explicit workspace destination and `--no-mpy` for a
source-only tree.

## Install onto a connected device with mpremote

```bash
mpremote connect /dev/ttyUSB0 mip install \
  --index https://PyDevices.github.io/mip \
  package-name
```

`mpremote mip` resolves and transfers the package from the host, so the board
does not need its own network connection.

## Install a raw GitHub package

`mip` also accepts GitHub files and directories. Pass the index when a raw
package has named dependencies that should resolve here:

```python
mip.install(
    "github:OWNER/REPOSITORY/path/to/package",
    index="https://PyDevices.github.io/mip",
)
```

The live index intentionally exposes only each package's current `latest`
manifest. Releases replace the current entry rather than accumulating a public
history of versioned manifests.

## Usage (Standard Upstream Packages)

To install standard, upstream `micropython-lib` standard library or ecosystem packages, there are four main options. For more information see the [Package management documentation](https://docs.micropython.org/en/latest/reference/packages.html) documentation.


### On a network-enabled device

As of MicroPython v1.20 (and nightly builds since October 2022), boards
with WiFi and Ethernet support include the `mip` package manager.

```py
>>> import mip
>>> mip.install("package-name")
```

### Using `mpremote` from your PC

`mpremote` is the officially-supported tool for interacting with a MicroPython
device and, since v0.4.0, support for installing micropython-lib packages is
provided by using the `mip` command.

```bash
$ mpremote connect /dev/ttyUSB0 mip install package-name
```

See the [mpremote documentation](https://docs.micropython.org/en/latest/reference/mpremote.html).

### Freeze into your firmware

If you are building your own firmware, all packages in this repository include
a `manifest.py` that can be included into your board manifest via the
`require()` command. See [Manifest files](https://docs.micropython.org/en/latest/reference/manifest.html#require) for
more information.

### Copy the files manually

Many micropython-lib packages are just single-file modules, and you can
quickly get started by copying the relevant Python file to your device. For
example, to add the `base64` library, you can directly copy
`python-stdlib/base64/base64.py` to the `lib` directory on your device.

This can be done using `mpremote`, for example:

```bash
$ mpremote connect /dev/ttyUSB0 cp python-stdlib/base64/base64.py :/lib
```

For packages that are implemented as a package directory, you'll need to copy
the directory instead. For example, to add `collections.defaultdict`, copy
`collections/collections/__init__.py` and
`collections-defaultdict/collections/defaultdict.py` to a directory named
`lib/collections` on your device.

Note that unlike the other three approaches based on `mip` or `manifest.py`,
you will need to manually resolve dependencies. You can inspect the relevant
`manifest.py` file to view the list of dependencies for a given package.

## Contributing

We use [GitHub Discussions](https://github.com/micropython/micropython/discussions)
as our forum, and [Discord](https://micropython.org/discord) for chat. These
are great places to ask questions and advice from the community or to discuss your
MicroPython-based projects.

The [MicroPython Wiki](https://github.com/micropython/micropython/wiki) is
also used for micropython-lib.

For bugs and feature requests, please [raise an issue](https://github.com/micropython/micropython-lib/issues/new).

We welcome pull requests to add new packages, fix bugs, or add features.
Please be sure to follow the
[Contributor's Guidelines & Code Conventions](CONTRIBUTING.md). Note that
MicroPython is licensed under the [MIT license](LICENSE) and all contributions
should follow this license.

### Future plans (and new contributor ideas)

* Develop a set of example programs using these packages.
* Develop more MicroPython packages for common tasks.
* Expand unit testing coverage.
* Add support for referencing remote/third-party repositories.

## Notes on terminology

The terms *library*, *package*, and *module* are overloaded and lead to some
confusion. The interpretation used in by the MicroPython project is that:

A *library* is a collection of installable packages, e.g. [The Python Standard
  Library](https://docs.python.org/3/library/), or micropython-lib.

A *package* can refer to two things. The first meaning, "library package", is
something that can be installed from a library, e.g. via `mip` (or `pip` in
CPython/PyPI). Packages provide *modules* that can be imported. The ambiguity
here is that the module provided by the package does not necessarily have to
have the same name, e.g. the `pyjwt` package provides the `jwt` module. In
CPython, the `pyserial` package providing the `serial` module is another
common example.

A *module* is something that can be imported. For example, "the *os* module".

A module can be implemented either as a single file, typically also called
a *module* or "single-file module", or as a *package* (the second meaning),
which in this context means a directory containing multiple `.py` files
(usually at least an `__init__.py`).

In micropython-lib, we also have the concept of an *extension package* which
is a library package that extends the functionality of another package, by
adding additional files to the same package directory. These packages have
hyphenated names. For example, the `collections-defaultdict` package extends
the `collections` package to add the `defaultdict` class to the `collections`
module.
