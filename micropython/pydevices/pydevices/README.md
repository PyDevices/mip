# pydevices

The portable PyDevices bundle installs the cross-platform display, audio, and
timing foundations from the canonical
[`PyDevices/pydevices`](https://github.com/PyDevices/pydevices) product
repository.

```bash
python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple \
  pydevices
```

The base bundle deliberately does not choose an application traffic
controller or a board configuration. Add `pydevices[events]` for the optional
`eventsys` controller, `pydevices[desktop]` for the desktop board, or
`pydevices[all]` for both. MCU applications select exactly one board package
with MIP.

Python imports and MIP package names remain unprefixed: `displaydev`,
`audiodev`, `multimer`, and optional `eventsys`.
