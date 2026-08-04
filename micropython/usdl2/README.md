# usdl2

Native and pure-Python **SDL2 subset** for Python (`import usdl2`) — CPython
wheels (Linux, Windows, Android), MicroPython / CircuitPython user C modules,
plus a ctypes/ffi fallback. Public names are **SDL2 symbols only**.

| Product | Pip / MIP | Role |
|---------|-----------|------|
| **usdl2** | TestPyPI `usdl2` | Native C extension (prefer on desktop/Android when available) |
| **usdl2** | MIP `usdl2` | Pure-Python fallback (same public API) |

One release tag `vX.Y.Z` publishes both delivery paths at that version. See [PUBLISHING.md](docs/PUBLISHING.md).

Choose the native module when you want the fastest path on desktop, Windows, Android, or embedded firmware. Choose the pure-Python fallback when you need the same SDL2-shaped API but want a simpler install path or a runtime that cannot load the compiled extension. In both cases, the public contract is the same: start with `import usdl2`, then use the SDL symbol you need from the module namespace.

## Documentation

See [docs/](docs/index.md) for native vs Python modules and pip/MIP install.

## Install

### Native (TestPyPI)

```bash
pip install \
  -i https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  usdl2
```

Requires a system-installed **SDL2** shared library at runtime (`libSDL2.so` / `SDL2.dll`). usdl2 wheels do not bundle SDL2. Android APKs use wheels tagged `android_21_*` with the APK’s p4a SDL2 bootstrap — see [pydisplay_android](https://github.com/PyDevices/pydisplay_android).

### Pure Python (MIP / micropython-lib)

```python
import mip
mip.install("usdl2", index="https://PyDevices.github.io/micropython-lib/mip/PyDevices")
```

### MicroPython (MIP)

```python
import mip
mip.install("usdl2", index="https://PyDevices.github.io/micropython-lib/mip/PyDevices")
```

### Quick check

```bash
python -c "import usdl2; assert hasattr(usdl2, 'SDL_PumpEvents'); print('ok')"
```

## What you get

- SDL2 functions, constants, and macros (`SDL_Init`, `SDL_CreateWindow`, `SDL_PumpEvents`, `SDL_DEFINE_PIXELFORMAT`, …)
- Type constructors for SDL structs (`SDL_Rect`, `SDL_Event`, …)
- Same public contract on MicroPython, CircuitPython unix, and CPython

Firmware / editable builds: see **Build from source** below.

## Links

- [Source](https://github.com/PyDevices/usdl2)
- [Issues](https://github.com/PyDevices/usdl2/issues)
- Related: [displaysys](https://test.pypi.org/project/displaysys/), [pydisplay](https://github.com/PyDevices/pydisplay)

## License

MIT — see [LICENSE](LICENSE).

---

## Build from source

### Layout

```text
usdl2/
  micropython.mk / circuitpython.mk / setup.py   # build glue (stay at root)
  src/usdl2_mp.c                                 # MicroPython + CircuitPython
  src/usdl2_cpy.c                                # CPython Extension
  src/usdl2.h, usdl2_module_globals.inc, …       # headers with C sources
  lib/usdl2.py                                   # pure-Python fallback
  docs/                                          # native vs Python, pip / MIP
  tests/                                         # unit tests only
  tools/                                         # developer smoke + helpers
  scripts/                                       # maintainer / CI publish
```

### SDL2 at build time

#### Linux / unix

```bash
sudo apt install libsdl2-dev   # pkg-config sdl2
```

#### Windows — two trees under `SDL2_DEV`

Do **not** vendor SDL2 in this repo. Download official devel ZIPs from [libsdl.org releases](https://github.com/libsdl-org/SDL/releases):

| Consumer | ZIP | Example unpack | `SDL2_DEV` |
|----------|-----|----------------|------------|
| `micropython.exe` (MinGW) | `SDL2-devel-*-mingw.zip` | `../../other/SDL2-2.30.10` from cmods (`x86_64-w64-mingw32/` inside) | that path |
| `python.exe` (MSVC) | `SDL2-devel-*-VC.zip` | `C:\SDL2-2.30.10-VC` (`include/` + `lib/x64/`) | that path |

`micropython.mk` links MinGW SDL2 **statically**. CPython wheels/extensions need `SDL2.dll` on `PATH` at runtime (from `lib/x64` of the VC tree).

If you need `SDL2.dll` for Windows runtime, use the official SDL release page:
[SDL 2.32.4 release](https://github.com/libsdl-org/SDL/releases?page=3#release-release-2.32.4)

`SDL2.dll` can be provided either by:
- placing it on `PATH`, or
- placing it in the current working directory of the process.

From WSL, set a Windows-visible path before `pip.exe`:

```bash
# MSVC tree copied to the Windows drive for reliable builds
export SDL2_DEV='C:\SDL2-2.30.10-VC'
cmd.exe /c "set SDL2_DEV=$SDL2_DEV&& pip.exe install -e $(wslpath -w "$PWD")"
cmd.exe /c "set PATH=C:\SDL2-2.30.10-VC\lib\x64;%PATH%&& python.exe $(wslpath -w tools/test_usdl2.py)"
```

See also [`tools/sdl2_dev_env.sh`](tools/sdl2_dev_env.sh).

### MicroPython

```bash
# unix
cd micropython/ports/unix && make USER_C_MODULES=../../..
# windows (MinGW)
export SDL2_DEV=../../other/SDL2-2.30.10
cd micropython/ports/windows && make USER_C_MODULES=../../..
```

Or from [cmods](https://github.com/PyDevices/cmods): `./build_mp.sh --port unix|windows --variant standard`.

```bash
./micropython/ports/unix/build-standard/micropython usdl2/tools/test_usdl2.py
./micropython/ports/windows/build-standard/micropython.exe usdl2/tools/test_usdl2.py
```

### CircuitPython (unix)

```bash
./apply_cp_unix_usdl_patches.sh --apply
../lv_circuitpython_mod/build_cp.sh --port unix --variant coverage
../circuitpython/ports/unix/build-coverage/micropython tools/test_usdl2.py
```

### CPython (editable)

```bash
# unix
pip install -e .
xvfb-run -a python3 tools/test_usdl2.py

# windows — see SDL2_DEV table above + pip.exe / python.exe
```

### Android wheels

CI publishes `android_21_arm64_v8a` and `android_21_x86_64` wheels (`cp313` / `cp314`) to TestPyPI. Local reproduction:

```bash
export ANDROID_HOME=~/.buildozer/android/platform/android-sdk
export ANDROID_NDK_HOME=~/.buildozer/android/platform/android-ndk-r28c
echo "0.0.0.dev" > VERSION
./scripts/ci_prepare_sdl2_android.sh
pipx run cibuildwheel --platform android
```

APK packaging lives in [pydisplay_android](https://github.com/PyDevices/pydisplay_android).

### Smoke test

`tools/test_usdl2.py` exercises init, window/renderer, packed rects, `SDL_Event` layout, timers, and `SDL_PumpEvents` on every runtime above.
