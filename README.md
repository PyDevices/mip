# PyDevices MIP package index

> **This index is generated — do not edit package trees by hand.**
> `pydevices-lock.json` is the source of truth: component repositories
> publish through a serialized dispatch queue
> (`process-mip-publication-request.yml`), each publication pins an exact
> source tag in the lockfile, and every deploy re-syncs **all** locked
> sources before publishing. Anything under the package directories is
> build output, and `packages.json` plus the "Packages in this index"
> block below are regenerated after every deploy; the only meaningful
> edits here are to the lockfile via the queue, the workflows,
> `scripts/`, and this documentation.


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

`mip` installs into the interpreter's default library destination unless `target`
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

## Packages in this index

<!-- PACKAGES: START -->
These are the PyDevices packages this index publishes, each built from the
source tag pinned in `pydevices-lock.json`; the micropython-lib packages the
index also carries are upstream's.

| Package | Version | Description | Source |
| --- | --- | --- | --- |
| `pydevices` | 0.7.7 | Portable display, audio, event, and timing foundations for PyDevices | [PyDevices/pydevices @ v0.7.7](https://github.com/PyDevices/pydevices/releases/tag/v0.7.7) |
| `pydevices-desktop` | 0.7.7 | Complete PyDevices desktop stack and board configuration | [PyDevices/pydevices @ v0.7.7](https://github.com/PyDevices/pydevices/releases/tag/v0.7.7) |
| `bledev` | 0.7.7 | Portable async Bluetooth Low Energy for PyDevices, over aioble on boards | [PyDevices/pydevices @ v0.7.7](https://github.com/PyDevices/pydevices/releases/tag/v0.7.7) |
| `midiports` | 0.7.7 | MIDI ports for adafruit_midi: USB device, UART, and a computer's own MIDI ports. | [PyDevices/pydevices @ v0.7.7](https://github.com/PyDevices/pydevices/releases/tag/v0.7.7) |
| `usb-core` | 0.7.7 | usb.core and usb.util: talk to USB devices from a host board, in PyUSB's shape. | [PyDevices/pydevices @ v0.7.7](https://github.com/PyDevices/pydevices/releases/tag/v0.7.7) |
| `usb-device-audio` | 0.7.7 | USB audio (UAC2) sound card on machine.USBDevice's streaming endpoints. | [PyDevices/pydevices @ v0.7.7](https://github.com/PyDevices/pydevices/releases/tag/v0.7.7) |
| `usb-device-msc` | 0.7.7 | USB mass storage device (Bulk-Only Transport, SCSI) over a MicroPython block device. | [PyDevices/pydevices @ v0.7.7](https://github.com/PyDevices/pydevices/releases/tag/v0.7.7) |
| `usb-device-video` | 0.7.7 | USB video (UVC) webcam on machine.USBDevice's streaming endpoints. | [PyDevices/pydevices @ v0.7.7](https://github.com/PyDevices/pydevices/releases/tag/v0.7.7) |
| `usb-hid` | 0.7.7 | CircuitPython's usb_hid on MicroPython, over usb-device-hid, for adafruit_hid. | [PyDevices/pydevices @ v0.7.7](https://github.com/PyDevices/pydevices/releases/tag/v0.7.7) |
| `usb-host-audio` | 0.7.7 | Play to a USB speaker or record from a USB microphone on this board's host port, over usb.core, alone or as audiodev outputs and inputs. | [PyDevices/pydevices @ v0.7.7](https://github.com/PyDevices/pydevices/releases/tag/v0.7.7) |
| `usb-host-cdc` | 0.7.7 | Talk to a USB serial device (CDC-ACM) on this board's host port, over usb.core. | [PyDevices/pydevices @ v0.7.7](https://github.com/PyDevices/pydevices/releases/tag/v0.7.7) |
| `usb-host-hid` | 0.7.7 | Keys, mouse buttons and movement from a keyboard or mouse plugged into this board's USB host port, named the way adafruit_hid names them. | [PyDevices/pydevices @ v0.7.7](https://github.com/PyDevices/pydevices/releases/tag/v0.7.7) |
| `usb-host-msc` | 0.7.7 | Mount a USB flash drive plugged into this board's host port, over usb.core. | [PyDevices/pydevices @ v0.7.7](https://github.com/PyDevices/pydevices/releases/tag/v0.7.7) |
| `usb-host-net` | 0.7.7 | Internet over USB: a phone's USB tethering on this board's host port, as a network interface. | [PyDevices/pydevices @ v0.7.7](https://github.com/PyDevices/pydevices/releases/tag/v0.7.7) |
| `usb-host-video` | 0.7.7 | Stream a webcam plugged into this board's USB host port, over usb.core. | [PyDevices/pydevices @ v0.7.7](https://github.com/PyDevices/pydevices/releases/tag/v0.7.7) |
| `hmilink` | 0.7.7 | Any screen as a device's front panel: one document, ops, telemetry and events over any transport. | [PyDevices/pydevices @ v0.7.7](https://github.com/PyDevices/pydevices/releases/tag/v0.7.7) |
| `palettes` | 0.0.14 | Color palette toolkit for PyDevices (wheel, cube, material_design) | [PyDevices/palettes @ v0.0.14](https://github.com/PyDevices/palettes/releases/tag/v0.0.14) |
| `pdwidgets` | 0.0.24 | Cross-platform widget toolkit for PyDevices | [PyDevices/pdwidgets @ v0.0.24](https://github.com/PyDevices/pdwidgets/releases/tag/v0.0.24) |
| `pygraphics` | 0.1.1 | Pure-Python pygraphics for MicroPython/CircuitPython/CPython (FrameBuffer, Draw, fonts); import as pygraphics | [PyDevices/pygraphics @ v0.1.1](https://github.com/PyDevices/pygraphics/releases/tag/v0.1.1) |
| `audioinstruments` | 0.4.1 | 55 synthio instruments for PyDevices (drum machines and synthesizers); import as audioinstruments | [PyDevices/audiocomponents @ v0.4.1](https://github.com/PyDevices/audiocomponents/releases/tag/v0.4.1) |
| `audioeffects` | 0.4.1 | Effect classes for PyDevices audio (delay, drive, dynamics, eq, modulation, pitch, reverb); import as audioeffects | [PyDevices/audiocomponents @ v0.4.1](https://github.com/PyDevices/audiocomponents/releases/tag/v0.4.1) |

```python
import mip

mip.install("pydevices", index="https://PyDevices.github.io/mip")
mip.install("pydevices-desktop", index="https://PyDevices.github.io/mip")
mip.install("bledev", index="https://PyDevices.github.io/mip")
mip.install("midiports", index="https://PyDevices.github.io/mip")
mip.install("usb-core", index="https://PyDevices.github.io/mip")
mip.install("usb-device-audio", index="https://PyDevices.github.io/mip")
mip.install("usb-device-msc", index="https://PyDevices.github.io/mip")
mip.install("usb-device-video", index="https://PyDevices.github.io/mip")
mip.install("usb-hid", index="https://PyDevices.github.io/mip")
mip.install("usb-host-audio", index="https://PyDevices.github.io/mip")
mip.install("usb-host-cdc", index="https://PyDevices.github.io/mip")
mip.install("usb-host-hid", index="https://PyDevices.github.io/mip")
mip.install("usb-host-msc", index="https://PyDevices.github.io/mip")
mip.install("usb-host-net", index="https://PyDevices.github.io/mip")
mip.install("usb-host-video", index="https://PyDevices.github.io/mip")
mip.install("hmilink", index="https://PyDevices.github.io/mip")
mip.install("palettes", index="https://PyDevices.github.io/mip")
mip.install("pdwidgets", index="https://PyDevices.github.io/mip")
mip.install("pygraphics", index="https://PyDevices.github.io/mip")
mip.install("audioinstruments", index="https://PyDevices.github.io/mip")
mip.install("audioeffects", index="https://PyDevices.github.io/mip")
```

<sub>Generated by `scripts/update_package_list.py` from the index itself;
`packages.json` carries the same data. Both are rewritten after every
deploy -- do not edit by hand.</sub>
<!-- PACKAGES: END -->

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

What's planned next is in [ROADMAP.md](ROADMAP.md).

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
