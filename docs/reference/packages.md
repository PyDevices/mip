# Packages in this index

The list below is rewritten after every deploy, and the same data is in [`packages.json`](../../packages.json). The index also carries all of micropython-lib; [installing those](../guides/install-micropython-lib-packages.md) works the same way.

<!-- PACKAGES: START -->
These are the PyDevices packages this index publishes, each built from the
source tag pinned in `pydevices-lock.json`; the micropython-lib packages the
index also carries are upstream's.

| Package | Version | Description | Source |
| --- | --- | --- | --- |
| `pydevices` | 0.7.8 | Portable display, audio, event, and timing foundations for PyDevices | [PyDevices/pydevices @ v0.7.8](https://github.com/PyDevices/pydevices/releases/tag/v0.7.8) |
| `pydevices-desktop` | 0.7.8 | Complete PyDevices desktop stack and board configuration | [PyDevices/pydevices @ v0.7.8](https://github.com/PyDevices/pydevices/releases/tag/v0.7.8) |
| `bledev` | 0.7.8 | Portable async Bluetooth Low Energy for PyDevices, over aioble on boards | [PyDevices/pydevices @ v0.7.8](https://github.com/PyDevices/pydevices/releases/tag/v0.7.8) |
| `midiports` | 0.7.8 | MIDI ports for adafruit_midi: USB device, UART, and a computer's own MIDI ports. | [PyDevices/pydevices @ v0.7.8](https://github.com/PyDevices/pydevices/releases/tag/v0.7.8) |
| `usb-core` | 0.7.8 | usb.core and usb.util: talk to USB devices from a host board, in PyUSB's shape. | [PyDevices/pydevices @ v0.7.8](https://github.com/PyDevices/pydevices/releases/tag/v0.7.8) |
| `usb-device-audio` | 0.7.8 | USB audio (UAC2) sound card on machine.USBDevice's streaming endpoints. | [PyDevices/pydevices @ v0.7.8](https://github.com/PyDevices/pydevices/releases/tag/v0.7.8) |
| `usb-device-msc` | 0.7.8 | USB mass storage device (Bulk-Only Transport, SCSI) over a MicroPython block device. | [PyDevices/pydevices @ v0.7.8](https://github.com/PyDevices/pydevices/releases/tag/v0.7.8) |
| `usb-device-video` | 0.7.8 | USB video (UVC) webcam on machine.USBDevice's streaming endpoints. | [PyDevices/pydevices @ v0.7.8](https://github.com/PyDevices/pydevices/releases/tag/v0.7.8) |
| `usb-hid` | 0.7.8 | CircuitPython's usb_hid on MicroPython, over usb-device-hid, for adafruit_hid. | [PyDevices/pydevices @ v0.7.8](https://github.com/PyDevices/pydevices/releases/tag/v0.7.8) |
| `usb-host-audio` | 0.7.8 | Play to a USB speaker or record from a USB microphone on this board's host port, over usb.core, alone or as audiodev outputs and inputs. | [PyDevices/pydevices @ v0.7.8](https://github.com/PyDevices/pydevices/releases/tag/v0.7.8) |
| `usb-host-cdc` | 0.7.8 | Talk to a USB serial device (CDC-ACM) on this board's host port, over usb.core. | [PyDevices/pydevices @ v0.7.8](https://github.com/PyDevices/pydevices/releases/tag/v0.7.8) |
| `usb-host-hid` | 0.7.8 | Keys, mouse buttons and movement from a keyboard or mouse plugged into this board's USB host port, named the way adafruit_hid names them. | [PyDevices/pydevices @ v0.7.8](https://github.com/PyDevices/pydevices/releases/tag/v0.7.8) |
| `usb-host-msc` | 0.7.8 | Mount a USB flash drive plugged into this board's host port, over usb.core. | [PyDevices/pydevices @ v0.7.8](https://github.com/PyDevices/pydevices/releases/tag/v0.7.8) |
| `usb-host-net` | 0.7.8 | Internet over USB: a phone's USB tethering on this board's host port, as a network interface. | [PyDevices/pydevices @ v0.7.8](https://github.com/PyDevices/pydevices/releases/tag/v0.7.8) |
| `usb-host-video` | 0.7.8 | Stream a webcam plugged into this board's USB host port, over usb.core. | [PyDevices/pydevices @ v0.7.8](https://github.com/PyDevices/pydevices/releases/tag/v0.7.8) |
| `hmilink` | 0.7.8 | Any screen as a device's front panel: one document, ops, telemetry and events over any transport. | [PyDevices/pydevices @ v0.7.8](https://github.com/PyDevices/pydevices/releases/tag/v0.7.8) |
| `palettes` | 0.0.14 | Color palette toolkit for PyDevices (wheel, cube, material_design) | [PyDevices/palettes @ v0.0.14](https://github.com/PyDevices/palettes/releases/tag/v0.0.14) |
| `pdwidgets` | 0.0.24 | Cross-platform widget toolkit for PyDevices | [PyDevices/pdwidgets @ v0.0.24](https://github.com/PyDevices/pdwidgets/releases/tag/v0.0.24) |
| `pygraphics` | 0.1.2 | Pure-Python pygraphics for MicroPython/CircuitPython/CPython (FrameBuffer, Draw, fonts); import as pygraphics | [PyDevices/pygraphics @ v0.1.2](https://github.com/PyDevices/pygraphics/releases/tag/v0.1.2) |
| `audioinstruments` | 0.5.0 | 55 synthio instruments for PyDevices (drum machines and synthesizers); import as audioinstruments | [PyDevices/audioinstruments @ v0.5.0](https://github.com/PyDevices/audioinstruments/releases/tag/v0.5.0) |
| `audioeffects` | 0.5.0 | Effect classes for PyDevices audio (delay, drive, dynamics, eq, modulation, pitch, reverb); import as audioeffects | [PyDevices/audioeffects @ v0.5.0](https://github.com/PyDevices/audioeffects/releases/tag/v0.5.0) |

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
