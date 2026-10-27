# Install micropython-lib packages

This index carries micropython-lib's packages too, so `mip.install("base64", index="https://PyDevices.github.io/mip")` works. You can also get them from upstream's own index, by freezing them into firmware, or by copying files. Upstream's [package management documentation](https://docs.micropython.org/en/latest/reference/packages.html) has more.

## From upstream's index

Leave out `index` and `mip` uses micropython-lib's own:

```python
import mip
mip.install("package-name")
```

With `mpremote`, from your computer:

```bash
mpremote connect /dev/ttyUSB0 mip install package-name
```

## Freeze into your firmware

If you build your own firmware, every package here has a `manifest.py` you can pull into your board's manifest with `require()`. See [Manifest files](https://docs.micropython.org/en/latest/reference/manifest.html#require).

## Copy the files by hand

Many packages are a single file. From a clone of this repository, to add `base64`, copy `python-stdlib/base64/base64.py` to `lib` on your board:

```bash
mpremote connect /dev/ttyUSB0 cp python-stdlib/base64/base64.py :/lib
```

A package that is a folder needs the folder. For `collections.defaultdict`, copy `collections/collections/__init__.py` and `collections-defaultdict/collections/defaultdict.py` into `lib/collections` on the board.

Copying by hand doesn't resolve dependencies. A package's `manifest.py` lists what else it needs.

## Package, module, library

micropython-lib uses these words carefully.

A *library* is a collection of installable packages, like micropython-lib or the Python standard library.

A *package* is something you install, with `mip` (or `pip` in CPython). It provides *modules* you import, and the names can differ: the `pyjwt` package provides the `jwt` module. "Package" also means a folder of `.py` files with an `__init__.py`, which is one way to write a module.

An *extension package* adds files to another package's folder. These have hyphenated names: `collections-defaultdict` adds `defaultdict` to the `collections` module.
