#!/usr/bin/env python3
"""Regenerate the list of PyDevices packages this index publishes.

Writes packages.json and rewrites the PACKAGES block in README.md. The set of
packages is derived from pydevices-lock.json (every profile the publication
sync builds), and the data for each -- version, description, license -- comes
from the index's own index.json, never from PyPI or TestPyPI.

Stdlib only; runs in the deploy workflow against the freshly built index and
by hand against the live one:

    python3 scripts/update_package_list.py                        # live index
    python3 scripts/update_package_list.py --index /path/index.json

The output is deterministic: given the same index it rewrites byte-identical
files, so a deploy that changed nothing commits nothing.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_URL = "https://PyDevices.github.io/mip"
LIVE_INDEX_JSON = f"{INDEX_URL}/index.json"

README_START = "<!-- PACKAGES: START -->"
README_END = "<!-- PACKAGES: END -->"

# Which packages a lockfile profile publishes, as index paths.
#
# The "pydevices" profile is the one profile that publishes MORE THAN ONE
# package: synchronize_pydevices() in PyDevices/.github's
# scripts/synchronize_mip_package.py writes micropython/pydevices/pydevices
# (all of lib/) and micropython/pydevices/pydevices-desktop (utils/ plus the
# desktop board config). Every other profile publishes exactly one package,
# named after the profile, at micropython/<profile>. If synchronize_pydevices
# ever grows a third package, this table is the one place to say so; the
# mismatch check below reports the index entry until it is.
MULTI_PACKAGE_PROFILES = {
    "pydevices": ("micropython/pydevices/pydevices", "micropython/pydevices/pydevices-desktop"),
}


def packages_for_profile(profile: str) -> tuple[str, ...]:
    """Index paths the publication sync writes for one lockfile profile."""
    return MULTI_PACKAGE_PROFILES.get(profile, (f"micropython/{profile}",))


def derive_expected(lock: dict) -> list[dict]:
    """The package set, in lockfile order, with its source pin attached."""
    expected = []
    for profile, entry in lock.items():
        for path in packages_for_profile(profile):
            expected.append(
                {
                    "name": path.rsplit("/", 1)[1],
                    "profile": profile,
                    "path": path,
                    "repository": entry["repository"],
                    "ref": entry["ref"],
                }
            )
    return expected


def load_index(source: str) -> dict:
    path = Path(source)
    if path.is_file():
        print(f"reading index from build output: {path}")
        return json.loads(path.read_text(encoding="utf-8"))
    if source.startswith(("http://", "https://")):
        print(f"no local index at {source!r}; fetching the live index from {source}")
        with urllib.request.urlopen(source, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    raise SystemExit(f"index not found: {source}")


def is_pydevices_published(path: str, lock: dict) -> bool:
    """Whether an index path belongs to a PyDevices publication profile.

    micropython/<profile> and anything beneath it. The micropython-lib packages
    the index also carries (python-stdlib/*, micropython/bluetooth/aioble, ...)
    are upstream's and never match.
    """
    parts = path.split("/")
    return len(parts) >= 2 and parts[0] == "micropython" and parts[1] in lock


def check_against_index(expected: list[dict], index: dict, lock: dict) -> list[str]:
    """Both directions: every derived package in the index, every PyDevices index entry derived."""
    problems = []
    by_path = {p["path"]: p for p in index["packages"]}
    expected_paths = {p["path"] for p in expected}
    for package in expected:
        if package["path"] not in by_path:
            problems.append(
                f"{package['name']}: derived from lockfile profile {package['profile']!r} "
                f"but {package['path']} is not in the index"
            )
    for path, entry in sorted(by_path.items()):
        if is_pydevices_published(path, lock) and path not in expected_paths:
            problems.append(
                f"{entry['name']}: in the index at {path} under a PyDevices profile "
                f"but not derived from the lockfile (see MULTI_PACKAGE_PROFILES)"
            )
    return problems


def build_packages(expected: list[dict], index: dict) -> list[dict]:
    by_path = {p["path"]: p for p in index["packages"]}
    packages = []
    for package in expected:
        entry = by_path.get(package["path"])
        packages.append(
            {
                "name": package["name"],
                "version": entry["version"] if entry else "(not yet published)",
                "description": entry["description"] if entry else "",
                "license": entry["license"] if entry else "",
                "path": package["path"],
                "profile": package["profile"],
                "repository": package["repository"],
                "ref": package["ref"],
                "repository_url": f"https://github.com/{package['repository']}",
                "release_url": f"https://github.com/{package['repository']}/releases/tag/{package['ref']}",
                "install": f'mip.install("{package["name"]}", index="{INDEX_URL}")',
                "published": entry is not None,
            }
        )
    return packages


def index_updated_date(index: dict) -> str:
    # The index's own build time, not the wall clock: the same index must
    # produce the same bytes. Day granularity on purpose -- build.py stamps
    # "updated" with the wall clock, so a full timestamp would make every
    # deploy commit a change even when no package moved.
    updated = _dt.datetime.fromtimestamp(int(index["updated"]), tz=_dt.timezone.utc)
    return updated.strftime("%Y-%m-%d")


def _rel(path: Path) -> str:
    """Repo-relative for the usual case; absolute when pointed elsewhere."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render_readme_block(packages: list[dict], index_updated: str) -> str:
    lines = [
        README_START,
        "These are the PyDevices packages this index publishes, each built from the",
        "source tag pinned in `pydevices-lock.json`; the micropython-lib packages the",
        "index also carries are upstream's.",
        "",
        "| Package | Version | Description | Source |",
        "| --- | --- | --- | --- |",
    ]
    for p in packages:
        source = f"[{p['repository']} @ {p['ref']}]({p['release_url']})"
        lines.append(
            f"| `{p['name']}` | {_cell(p['version'])} | {_cell(p['description'])} | {source} |"
        )
    lines += [
        "",
        "```python",
        "import mip",
        "",
    ]
    lines += [p["install"] for p in packages]
    lines += [
        "```",
        "",
        "<sub>Generated by `scripts/update_package_list.py` from the index itself",
        f"(built {index_updated}); `packages.json` carries the same data. Both are",
        "rewritten on every deploy -- do not edit by hand.</sub>",
        README_END,
    ]
    return "\n".join(lines)


def rewrite_readme(readme: Path, block: str) -> bool:
    content = readme.read_text(encoding="utf-8")
    start = content.find(README_START)
    end = content.find(README_END)
    if start == -1 or end == -1 or end < start:
        print(
            f"README has no {README_START} / {README_END} block; README left alone",
            file=sys.stderr,
        )
        return False
    updated = content[:start] + block + content[end + len(README_END) :]
    if updated != content:
        readme.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--index",
        default=LIVE_INDEX_JSON,
        help="index.json to read: a path (the deploy's build output) or a URL (default: the live index)",
    )
    parser.add_argument("--lockfile", type=Path, default=REPO_ROOT / "pydevices-lock.json")
    parser.add_argument("--readme", type=Path, default=REPO_ROOT / "README.md")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "packages.json")
    args = parser.parse_args()

    lock = json.loads(args.lockfile.read_text(encoding="utf-8"))
    index = load_index(args.index)
    expected = derive_expected(lock)

    problems = check_against_index(expected, index, lock)
    for problem in problems:
        print(f"MISMATCH: {problem}", file=sys.stderr)
    if not problems:
        print(
            f"package list matches the index: {len(expected)} packages from {len(lock)} profiles"
        )

    packages = build_packages(expected, index)
    index_updated = index_updated_date(index)
    document = {
        "index": INDEX_URL,
        "index_updated": index_updated,
        "source": args.index,
        "lockfile": args.lockfile.name,
        "packages": packages,
    }
    rendered = json.dumps(document, indent=2) + "\n"
    if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
        args.output.write_text(rendered, encoding="utf-8")
        print(f"wrote {_rel(args.output)}")
    else:
        print(f"{_rel(args.output)} unchanged")

    if rewrite_readme(args.readme, render_readme_block(packages, index_updated)):
        print(f"rewrote the PACKAGES block in {_rel(args.readme)}")
    else:
        print(f"{_rel(args.readme)} unchanged")

    for p in packages:
        print(f"  {p['name']:<18} {p['version']:<22} {p['repository']} @ {p['ref']}")


if __name__ == "__main__":
    main()
