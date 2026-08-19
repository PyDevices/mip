# appdev

`appdev` is the optional **application coordinator, hardware input aggregator, timer manager, display refresh controller, and main run loop** for Python applications in the PyDevices ecosystem (MicroPython, CircuitPython, CPython, PyScript, and Jupyter).

It bridges neutral hardware definitions (`board_config`), timer backends (`multimer`), standard SDL2/PyGame event types (`events`, `keys`), and display drivers (`displaydev`) into an intuitive, zero-async-boilerplate application lifecycle.

---

## Quick Start

```python
import board_config
import appdev
import events

app = appdev.App(board_config)

@app.on(events.KEYDOWN)
def on_key(e):
    print("Key pressed:", e.key)

@app.every(20)
def on_frame(timer=None):
    # Render animation or update physics every 20ms
    pass

app.run()
```

---

## Constructor

### `appdev.App(board_config=None, *, displays=None, host_read=None, touch_read=None, touch_rotation_table=None, refresh_period=None, timer_async=None)`

Instantiates the application coordinator.

#### Arguments:
* **`board_config`** *(optional)*: A board configuration module or namespace exporting hardware attributes (e.g. `display_drv`, `host_read`, `touch_read`, `touch_rotation_table`, `keypad_read`, `encoder_read`, `encoder_button_read`, `joystick_driver`, `joystick_emulate_digital`, `timer_async`).
* **`displays`** *(sequence, optional)*: Sequence of `displaydev` driver instances. Index 0 is primary. If omitted, extracted from `board_config.display_drv`.
* **`host_read`** *(callable, optional)*: Polling callable returning raw OS/host events (SDL2/PyGame).
* **`touch_read`** *(callable, optional)*: Polling callable returning touch point tuples `(x, y[, ...])`.
* **`touch_rotation_table`** *(4-item tuple, optional)*: Bitmask quadrant rotation table for touch mapping (defaults to standard 0/90/180/270° orientation mask).
* **`refresh_period`** *(int, optional)*: Milliseconds between `display.show()` presentation ticks. Defaults to `33` ms (approx 30 FPS) if any attached display has `needs_refresh=True`. Pass `0` or negative to disable periodic refresh.
* **`timer_async`** *(bool, optional)*: Force async timer (`multimer.AsyncTimer`) or synchronous timer (`multimer.auto.Timer`). Auto-detected from display requirements (e.g. PyScript / Jupyter canvas) or `board_config.timer_async` if omitted.

---

## Public API Reference

### 1. Event Subscriptions

#### `app.on(event_type_or_list, callback=None)`
Subscribe a callback to one or more event types. Can be used as a direct method call or as a decorator.
```python
# Direct method call:
app.on(events.KEYDOWN, on_key)
app.on([events.MOUSEBUTTONDOWN, events.MOUSEBUTTONUP], on_touch)

# Decorator:
@app.on(events.QUIT)
def on_quit(e):
    print("Quitting...")
```

#### `app.off(event_type_or_list, callback)`
Unsubscribe a previously registered callback from one or more event types.
```python
app.off(events.KEYDOWN, on_key)
```

---

### 2. Periodic Timers & Tasks

#### `app.every(ms, callback=None)`
Schedule a periodic callback to run approximately every `ms` milliseconds. Automatically manages sync vs. async timers with no `async_` parameter required. Can also be used as a decorator.
```python
# Direct registration:
sub = app.every(20, on_tick)

# Decorator:
@app.every(1000)
def heartbeat(timer=None):
    print("1 second elapsed")

# Cancel subscription:
sub.cancel()
```

#### `app.stop_timer()`
Stops the underlying shared timer and cancels all periodic `every()` subscriptions and display refresh tasks.

---

### 3. Execution & Run Loop

#### `app.run(tick_ms=10)`
The single universal entry point at the bottom of application scripts. It transparently handles all runtime environments:
* **Async host with active loop** (PyScript / WASM / Jupyter Notebook): Arms the deferred async timer and refresh, then returns immediately so the browser/notebook loop drives the app.
* **Async host without active loop** (Desktop async): Executes `asyncio.run()` until quit.
* **Sync host in interactive REPL** (MicroPython / CPython `-i` with interrupt timers): Returns immediately, keeping the interactive REPL live and responsive while timers run in the background.
* **Sync host in script mode**: Enters a low-overhead sleep loop until `app.quit_requested` is `True`.

#### `app.run_async(coro_or_fn)`
Executes an asynchronous coroutine or factory function under the application's async environment.

#### `app.request_quit(code=None)`
Request clean application shutdown and teardown.
* **`code`** *(int, optional)*: Exit code passed to `sys.exit()` after teardown finishes. If omitted, exits cleanly with status 0.

#### `app.before_quit` *(property / setter)*
Optional callable (e.g. `lv.deinit`) executed during teardown before displays are deinitialized.

---

### 4. Display Coordination & GUI Framework Interfacing

#### `app.pause_refresh()`
Pauses runtime-driven `display.show()` calls. Used by GUI frameworks (such as `pdwidgets` or `LVGL`) that present frames manually. Returns a claim object with `.release()`.

#### `app.resume_refresh()`
Resumes runtime-driven `display.show()` presentation.

#### `app.refresh_paused()`
Context manager that pauses auto-refresh within a code block:
```python
with app.refresh_paused():
    custom_direct_frame_draw()
```

#### `app.displays`
Tuple of attached `displaydev` driver instances (index 0 is primary).

#### `app.primary`
Primary `displaydev` driver, or `None`.

#### `app.add_display(drv)` / `app.remove_display(drv)`
Attach or detach secondary display drivers.

---

### 5. Input Devices & Manual Polling

#### `app.poll()`
Polls all registered devices, pumps timer queues, dispatches pending events to listeners, and returns a list of polled `events.*` namedtuples. (Normally driven automatically by `app.run()`).

#### Manual Device Registration:
* **`app.add_touch(read, *, display=None, rotation_table=None)`** &rarr; returns `Touch`
* **`app.add_keypad(read)`** &rarr; returns `Keypad`
* **`app.add_encoder(read, *, button_read=None, button=2)`** &rarr; returns `Encoder`
* **`app.add_joystick(joystick_driver, *, emulate_digital=None, digital_threshold=0.5)`** &rarr; returns `Joystick`
* **`app.register(device)`** / **`app.unregister(device)`** &rarr; registers any custom object implementing `.poll()`.

---

### 6. Mappers & Helpers

#### `appdev.TouchGrid(app, x, y, w, h, cols=3, rows=3, keys=None, translate=None, on_press=None, on_release=None)`
Maps a screen rectangle into a grid of button/key IDs.
* `grid.read()`: Returns list of keys pressed since last read (edge triggered).
* `grid.read_held()`: Returns list of keys currently held down (level triggered).

#### `appdev.JoyMap(app, joymap)`
Maps joystick hats and buttons to continuous held key codes.
* `joymap.read()`: Returns list of currently held mapped key codes.

#### `appdev.App.current()`
Returns the active `App` singleton instance (or `None`).

---

