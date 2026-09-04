#!/usr/bin/env python3
"""Regenerate the list of PyDevices packages this index publishes.

Writes packages.json and rewrites the PACKAGES block in README.md. The set of
packages is derived from pydevices-lock.json (every profile the publication
sync builds), and the data for each -- version, description, license -- comes
from the index's own index.json, never from PyPI or TestPyPI.

Stdlib only. The refresh-package-list workflow runs it after every deploy --
a publication or a docs push -- against the index that was just deployed; by
hand it reads the live index:

    python3 scripts/update_package_list.py                        # live index
    python3 scripts/update_package_list.py --index /path/index.json
    python3 scripts/update_package_list.py --self-check

--index is either an http(s) URL, which is fetched, or a file path, which must
exist. There is no fallback from a missing path to the live index.

The list must agree with the lockfile in both directions and in version: every
locked profile's packages must be in the index at the version the lockfile's
ref names, and every index entry the publication sync produced must be derived
from the lockfile. On any mismatch nothing is written and the exit status is 1,
so a stale index or a hand-edited lockfile never becomes a committed list.

The output is a pure function of the lockfile and the index's package entries
-- no timestamps, no paths -- so a rerun against the same index rewrites
byte-identical files and a deploy that changed nothing commits nothing.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import shutil
import sys
import tempfile
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
                    # The workflows' Verify steps compare the same way (${ref#v}).
                    "version": entry["ref"].removeprefix("v"),
                }
            )
    return expected


def load_index(source: str) -> dict:
    if source.startswith(("http://", "https://")):
        print(f"fetching the index from {source}")
        with urllib.request.urlopen(source, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    path = Path(source)
    if not path.is_file():
        raise SystemExit(f"index not found: {source} (a path must exist; a URL is fetched)")
    print(f"reading the index from {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def is_sync_output(path: str, lock: dict, repo_root: Path) -> bool:
    """Whether an index entry was produced by the publication sync.

    The deployed index is exactly the manifests committed in this repository
    (upstream micropython-lib: python-stdlib/*, micropython/bluetooth/aioble,
    ...) plus the trees the sync writes for the lockfile's profiles, which are
    never committed (see .gitignore). So an entry is the sync's if it sits
    under micropython/<profile> for a locked profile, or if no manifest.py is
    committed at its path -- the second rule catches a package the sync wrote
    under a name that is not a profile's.
    """
    parts = path.split("/")
    if len(parts) >= 2 and parts[0] == "micropython" and parts[1] in lock:
        return True
    return not (repo_root / path / "manifest.py").is_file()


def check_against_index(
    expected: list[dict], index: dict, lock: dict, repo_root: Path
) -> list[str]:
    """Every derived package in the index at the locked version; every sync entry derived."""
    problems = []
    by_path = {p["path"]: p for p in index["packages"]}
    expected_paths = {p["path"] for p in expected}
    for package in expected:
        entry = by_path.get(package["path"])
        if entry is None:
            problems.append(
                f"{package['name']}: derived from lockfile profile {package['profile']!r} "
                f"but {package['path']} is not in the index"
            )
        elif entry["version"] != package["version"]:
            problems.append(
                f"{package['name']}: index has {entry['version']}, lockfile pins "
                f"{package['repository']} @ {package['ref']}"
            )
    for path, entry in sorted(by_path.items()):
        if path not in expected_paths and is_sync_output(path, lock, repo_root):
            problems.append(
                f"{entry['name']}: in the index at {path} but not derived from the lockfile "
                f"(see MULTI_PACKAGE_PROFILES)"
            )
    return problems


def build_packages(expected: list[dict], index: dict) -> list[dict]:
    by_path = {p["path"]: p for p in index["packages"]}
    packages = []
    for package in expected:
        entry = by_path[package["path"]]
        packages.append(
            {
                "name": package["name"],
                "version": entry["version"],
                "description": entry["description"],
                "license": entry["license"],
                "path": package["path"],
                "profile": package["profile"],
                "repository": package["repository"],
                "ref": package["ref"],
                "repository_url": f"https://github.com/{package['repository']}",
                "release_url": f"https://github.com/{package['repository']}/releases/tag/{package['ref']}",
                "install": f'mip.install("{package["name"]}", index="{INDEX_URL}")',
            }
        )
    return packages


def _rel(path: Path) -> str:
    """Repo-relative for the usual case; absolute when pointed elsewhere."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render_readme_block(packages: list[dict]) -> str:
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
        "<sub>Generated by `scripts/update_package_list.py` from the index itself;",
        "`packages.json` carries the same data. Both are rewritten after every",
        "deploy -- do not edit by hand.</sub>",
        README_END,
    ]
    return "\n".join(lines)


def render_packages_json(packages: list[dict]) -> str:
    return json.dumps({"index": INDEX_URL, "packages": packages}, indent=2) + "\n"


def readme_block_span(content: str) -> tuple[int, int] | None:
    start = content.find(README_START)
    end = content.find(README_END)
    if start == -1 or end == -1 or end < start:
        return None
    return start, end + len(README_END)


def refresh(
    index: dict, lock: dict, readme: Path, output: Path, repo_root: Path = REPO_ROOT
) -> int:
    """Check, then write both files, or write nothing. Returns the exit status."""
    expected = derive_expected(lock)
    problems = check_against_index(expected, index, lock, repo_root)
    readme_content = readme.read_text(encoding="utf-8")
    span = readme_block_span(readme_content)
    if span is None:
        problems.append(f"{_rel(readme)} has no {README_START} / {README_END} block")
    if problems:
        for problem in problems:
            print(f"MISMATCH: {problem}", file=sys.stderr)
        print(f"nothing written: {len(problems)} problem(s)", file=sys.stderr)
        return 1
    print(f"package list matches the index: {len(expected)} packages from {len(lock)} profiles")

    packages = build_packages(expected, index)

    rendered = render_packages_json(packages)
    if not output.exists() or output.read_text(encoding="utf-8") != rendered:
        output.write_text(rendered, encoding="utf-8")
        print(f"wrote {_rel(output)}")
    else:
        print(f"{_rel(output)} unchanged")

    start, end = span
    updated = readme_content[:start] + render_readme_block(packages) + readme_content[end:]
    if updated != readme_content:
        readme.write_text(updated, encoding="utf-8")
        print(f"rewrote the PACKAGES block in {_rel(readme)}")
    else:
        print(f"{_rel(readme)} unchanged")

    for p in packages:
        print(f"  {p['name']:<18} {p['version']:<10} {p['repository']} @ {p['ref']}")
    return 0


# --- self-check ---------------------------------------------------------------


def _entry(name: str, version: str, path: str, description: str = "") -> dict:
    return {
        "name": name,
        "version": version,
        "author": "",
        "description": description or f"{name} description",
        "license": "MIT",
        "versions": {},
        "path": path,
    }


def self_check() -> int:
    """Prove the checks can fail: plant each fault and require it to be reported.

    Uses this checkout for the committed-manifest rule, so the two upstream
    entries below are real paths from the working tree.
    """
    upstream = [
        sorted(REPO_ROOT.glob("python-stdlib/*/manifest.py"))[0].parent,
        sorted(REPO_ROOT.glob("micropython/*/manifest.py"))[0].parent,
    ]
    upstream_entries = [_entry(p.name, "0.1.0", str(p.relative_to(REPO_ROOT))) for p in upstream]
    for p in upstream:
        # A locked profile must never shadow an upstream package in this check.
        assert p.name not in ("pydevices", "palettes"), p

    lock = {
        "pydevices": {"repository": "PyDevices/pydevices", "ref": "v0.3.8"},
        "palettes": {"repository": "PyDevices/palettes", "ref": "v0.0.13"},
    }
    healthy = [
        _entry("pydevices", "0.3.8", "micropython/pydevices/pydevices"),
        _entry("pydevices-desktop", "0.3.8", "micropython/pydevices/pydevices-desktop"),
        _entry("palettes", "0.0.13", "micropython/palettes", "wheel | cube"),
        *upstream_entries,
    ]

    def index_of(entries: list[dict]) -> dict:
        return {"v": 2, "updated": 1788478216, "packages": entries}

    failures: list[str] = []
    passed = 0

    def case(
        name: str,
        index: dict,
        readme_text: str,
        expect_rc: int,
        expect_written: bool | None = None,
        expect_problem: str = "",
    ) -> tuple[str, str]:
        nonlocal passed
        readme = work / "README.md"
        output = work / "packages.json"
        readme.write_text(readme_text, encoding="utf-8")
        before = (readme.read_text(), output.read_text() if output.exists() else None)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = refresh(index, lock, readme, output, REPO_ROOT)
        after = (readme.read_text(), output.read_text() if output.exists() else None)
        problems = []
        if rc != expect_rc:
            problems.append(f"exit {rc}, expected {expect_rc}")
        if expect_written is True and after == before:
            problems.append("expected files to change, nothing did")
        if expect_written is False and after != before:
            problems.append("expected nothing written, files changed")
        if expect_problem and expect_problem not in err.getvalue():
            problems.append(f"stderr lacks {expect_problem!r}: {err.getvalue().strip()!r}")
        if problems:
            failures.append(f"{name}: " + "; ".join(problems))
        else:
            passed += 1
            print(f"ok: {name}")
        return after

    work = Path(tempfile.mkdtemp(prefix="update_package_list-selfcheck-"))
    try:
        marked = f"# x\n\n## Packages\n\n{README_START}\nstale\n{README_END}\n\n## After\n"

        readme_text, packages_text = case(
            "healthy index is written", index_of(healthy), marked, 0, expect_written=True
        )
        block = readme_text[readme_text.index(README_START) : readme_text.index(README_END)]
        for must in (
            "| `pydevices` | 0.3.8 |",
            "| `pydevices-desktop` | 0.3.8 |",
            "| `palettes` | 0.0.13 | wheel \\| cube |",
            "https://github.com/PyDevices/palettes/releases/tag/v0.0.13",
            'mip.install("pydevices-desktop", index="https://PyDevices.github.io/mip")',
        ):
            if must not in block:
                failures.append(f"README block lacks {must!r}")
        if "stale" in block or not readme_text.endswith("\n\n## After\n"):
            failures.append("README outside the block was not preserved")
        doc = json.loads(packages_text)
        names = [p["name"] for p in doc["packages"]]
        if names != ["pydevices", "pydevices-desktop", "palettes"]:
            failures.append(f"packages.json order/content wrong: {names}")
        if set(doc) != {"index", "packages"}:
            failures.append(f"packages.json carries environment-dependent keys: {sorted(doc)}")

        # Same index again: byte-identical, nothing rewritten.
        again = case(
            "rerun is byte-identical", index_of(healthy), readme_text, 0, expect_written=False
        )
        if again != (readme_text, packages_text):
            failures.append("rerun changed bytes")

        planted = [dict(e, version="0.0.99") if e["name"] == "palettes" else e for e in healthy]
        case(
            "version behind the lockfile is a mismatch",
            index_of(planted),
            readme_text,
            1,
            expect_written=False,
            expect_problem="palettes: index has 0.0.99, lockfile pins PyDevices/palettes @ v0.0.13",
        )
        case(
            "locked package missing from the index is a mismatch",
            index_of([e for e in healthy if e["name"] != "palettes"]),
            readme_text,
            1,
            expect_written=False,
            expect_problem="palettes: derived from lockfile profile 'palettes'",
        )
        case(
            "sync output nested under a profile but not derived is a mismatch",
            index_of(
                [
                    *healthy,
                    _entry("pydevices-extra", "0.0.1", "micropython/pydevices/pydevices-extra"),
                ]
            ),
            readme_text,
            1,
            expect_written=False,
            expect_problem="pydevices-extra: in the index at micropython/pydevices/pydevices-extra",
        )
        case(
            "sync output with no committed manifest is a mismatch",
            index_of(
                [*healthy, _entry("pydevices-extra", "0.0.1", "micropython/pydevices-extra")]
            ),
            readme_text,
            1,
            expect_written=False,
            expect_problem="pydevices-extra: in the index at micropython/pydevices-extra",
        )
        case(
            "README without markers is a failure, packages.json untouched",
            index_of(healthy),
            "# x\n\nno markers here\n",
            1,
            expect_written=False,
            expect_problem="has no <!-- PACKAGES: START -->",
        )
        case(
            "END before START is a failure",
            index_of(healthy),
            f"# x\n{README_END}\n{README_START}\n",
            1,
            expect_written=False,
            expect_problem="has no <!-- PACKAGES: START -->",
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)

    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    if failures:
        print(
            f"self-check failed: {len(failures)} failure(s), {passed} case(s) passed",
            file=sys.stderr,
        )
        return 1
    print(f"self-check passed: {passed} cases")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--index",
        default=LIVE_INDEX_JSON,
        help="index.json to read: an existing file path (the deploy's artifact) "
        "or an http(s) URL, fetched (default: the live index). No fallback between the two.",
    )
    parser.add_argument("--lockfile", type=Path, default=REPO_ROOT / "pydevices-lock.json")
    parser.add_argument("--readme", type=Path, default=REPO_ROOT / "README.md")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "packages.json")
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="plant each fault the checks exist for and require it to be reported; writes nothing",
    )
    args = parser.parse_args()

    if args.self_check:
        return self_check()

    lock = json.loads(args.lockfile.read_text(encoding="utf-8"))
    index = load_index(args.index)
    return refresh(index, lock, args.readme, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
