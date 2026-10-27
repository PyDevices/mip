# How the index is built

The index is a fork of [micropython-lib](https://github.com/micropython/micropython-lib) whose build publishes upstream's packages and PyDevices' packages together, to GitHub Pages at `https://PyDevices.github.io/mip`. Every package is built twice: as `.mpy` bytecode, and as `.py` source for `mpy=False`.

## Nobody edits the package trees

[`pydevices-lock.json`](../../pydevices-lock.json) is the source of truth. It pins each PyDevices package to an exact release tag in the repository that owns it. Everything under the package folders is build output.

When a repository releases, it sends a publication request. Requests run one at a time through [`process-mip-publication-request.yml`](../../.github/workflows/process-mip-publication-request.yml), and each one updates the package's pin in the lockfile. Every deploy then syncs all the pinned sources again before it publishes, so one release can't leave another package stale. The lockfile also says which repository may publish each package, and a request from any other repository is refused.

After each deploy, [`scripts/update_package_list.py`](../../scripts/update_package_list.py) reads the live index back and rewrites `packages.json` and the [package list](../reference/packages.md), so the list always matches what's actually being served.

## Only the latest version

The index lists each package's current version and nothing older. A release replaces the entry instead of adding another.
