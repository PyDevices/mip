# Install a package

Every install names the index with `https://PyDevices.github.io/mip`. The [package list](../reference/packages.md) has every name you can install.

## On a board with a network connection

MicroPython 1.20 and later include `mip` on boards with Wi-Fi or Ethernet. Connect to your network, then:

```python
import mip

mip.install("package-name", index="https://PyDevices.github.io/mip")
```

The package goes into the interpreter's default library folder unless you pass `target`. You get `.mpy` bytecode by default; pass `mpy=False` for portable `.py` source:

```python
mip.install(
    "package-name",
    index="https://PyDevices.github.io/mip",
    target="lib",
    mpy=False,
)
```

## From your computer, onto a board on USB

`mpremote` fetches the package on your computer and copies it to the board, so the board doesn't need a network:

```bash
mpremote connect /dev/ttyUSB0 mip install \
  --index https://PyDevices.github.io/mip \
  package-name
```

See the [mpremote documentation](https://docs.micropython.org/en/latest/reference/mpremote.html) for how to name your board's port.

## With the unix or Windows port

A MicroPython build for your computer can run the package manager as a module:

```bash
micropython -m mip install \
  --index https://PyDevices.github.io/mip \
  package-name
```

Add `--target lib` to choose the folder and `--no-mpy` for source only.

## From GitHub

`mip` also takes a GitHub file or folder. Pass the index too, so the package's dependencies resolve from here:

```python
mip.install(
    "github:OWNER/REPOSITORY/path/to/package",
    index="https://PyDevices.github.io/mip",
)
```
