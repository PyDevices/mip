# micropython-lib

This repository houses standard library and ecosystem packages for MicroPython, and serves as the **PyDevices MIP Package Index**, serving both precompiled **`.mpy`** bytecode and raw **`.py`** source packages from:
**`https://PyDevices.github.io/micropython-lib/mip/PyDevices`**

---

## Installing PyDevices Packages

PyDevices packages (`pydevices`, `palettes`, `pdwidgets`, `pygraphics`) and their dependencies can be installed using MicroPython's native package manager (`mip`) or `mpremote` with our custom index URL.

### 1. Onto a Local Desktop Filesystem (Preferred for CPython/Simulation)
To quickly set up a local desktop simulation and development workspace, download `micropython` or `micropython.exe` to your machine and run the following three commands to generate a ready-to-use workspace:

```bash
# On Linux / macOS
mkdir -p ~/.micropython && cd ~/.micropython
micropython -m mip install --target lib --index https://PyDevices.github.io/micropython-lib/mip/PyDevices github:PyDevices/pydevices/board_configs/desktop

# On Windows (cmd.exe)
mkdir "%USERPROFILE%\.micropython" && cd "%USERPROFILE%\.micropython"
micropython.exe -m mip install --target lib --index https://PyDevices.github.io/micropython-lib/mip/PyDevices github:PyDevices/pydevices/board_configs/desktop
```

#### Preferred Path Configuration
For details on the preferred `PYTHONPATH` and `MICROPYPATH` environment variables and the rationale behind their layout, see [Preferred Path Configuration in the pydevices README](https://github.com/PyDevices/pydevices#preferred-path-configuration).



### 2. Onto a Connected Hardware Board (via PC)
To flash packages directly onto a board connected via USB serial, use the official `mpremote` CLI tool:

```bash
mpremote mip install --index https://PyDevices.github.io/micropython-lib/mip/PyDevices pdwidgets
```

### 3. On a Network-Enabled Board (WiFi / Ethernet)
Run the built-in `mip` package manager directly from the microcontroller's REPL prompt:

```python
import mip
mip.install("pdwidgets", index="https://PyDevices.github.io/micropython-lib/mip/PyDevices")
```

---

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

## Installing packages from forks

It is possible to use the `mpremote mip install` or `mip.install()` methods to
install packages built from a
[fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/about-forks)
of micropython-lib, if the fork's owner has opted in.

This can be useful to install packages from a pending Pull Request, for example.

First, the owner of the fork must opt-in as described under
[Publishing packages from forks](CONTRIBUTING.md#publishing-packages-from-forks).

After this has happened, each time someone pushes to a branch in that fork then
GitHub Actions will automatically publish the packages to a GitHub Pages site.

To install these packages, use commands such as:

```bash
$ mpremote connect /dev/ttyUSB0 mip install --index https://USERNAME.github.io/micropython-lib/mip/BRANCH_NAME PACKAGE_NAME
```

Or from a networked device:

```py
import mip
mip.install(PACKAGE_NAME, index="https://USERNAME.github.io/micropython-lib/mip/BRANCH_NAME")
```

(Where `USERNAME`, `BRANCH_NAME` and `PACKAGE_NAME` are replaced with the owner
of the fork, the branch the packages were built from, and the package name.)

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

