# SPDX-License-Identifier: MIT
"""Android media session for :class:`audiodev.PCMOutput`.

Hooks into ``PCMOutput(session=…)`` so the first ``open()`` / ``write()``
acquires audio focus and starts a ``mediaPlayback`` foreground service, and
the last ``close()`` releases both. Non-Android imports are a no-op.

Requires pyjnius and a p4a service named ``mediaplayback`` with
``:foreground:foregroundServiceType=mediaPlayback`` (see pydevices-android-template).
"""

from __future__ import annotations

import sys
import threading

__all__ = ["AndroidMediaSession", "get_session"]

_LOCK = threading.RLock()
_SESSION = None


class AndroidMediaSession:
    """Duck-typed :class:`audiodev.AudioSession` for Android media hardening.

    Multiple ``PCMOutput`` instances may share one session; FGS + focus stay
    up while any owner is open.
    """

    def __init__(self):
        self._owners = []
        self.codec = None
        self.duplex = True
        self._focus_listener = None
        self._started = False

    def get_codec(self):
        return self.codec

    def acquire(self, owner, direction):
        with _LOCK:
            if owner in self._owners:
                return self.codec
            if not self._owners:
                self._start_media()
            self._owners.append(owner)
            return self.codec

    def release(self, owner):
        with _LOCK:
            if owner in self._owners:
                self._owners.remove(owner)
            if not self._owners and self._started:
                self._stop_media()

    def _start_media(self):
        if sys.platform != "android":
            self._started = True
            return
        try:
            from jnius import PythonJavaClass, autoclass, java_method
        except ImportError as exc:
            raise RuntimeError(
                "Android audio_out needs pyjnius (add pyjnius to the APK)"
            ) from exc

        class _FocusListener(PythonJavaClass):
            __javainterfaces__ = [
                "android/media/AudioManager$OnAudioFocusChangeListener"
            ]

            @java_method("(I)V")
            def onAudioFocusChange(self, focus_change):
                pass

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        AudioManager = autoclass("android.media.AudioManager")
        activity = PythonActivity.mActivity
        if activity is None:
            raise RuntimeError("PythonActivity.mActivity is not ready")

        am = activity.getSystemService("audio")
        listener = _FocusListener()
        # Keep a hard ref so the JVM callback is not GC'd.
        self._focus_listener = listener
        result = am.requestAudioFocus(
            listener,
            AudioManager.STREAM_MUSIC,
            AudioManager.AUDIOFOCUS_GAIN,
        )
        if result == AudioManager.AUDIOFOCUS_REQUEST_FAILED:
            raise OSError("requestAudioFocus failed")

        pkg = activity.getPackageName()
        Service = autoclass(pkg + ".ServiceMediaplayback")
        # Notification keeps the mediaPlayback FGS visible (Android 14+).
        Service.start(
            activity,
            "",
            "PyDevices",
            "Playing audio",
            "",
        )
        self._started = True
        self._audio_manager = am

    def _stop_media(self):
        if sys.platform != "android":
            self._started = False
            return
        try:
            from jnius import autoclass

            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            am = getattr(self, "_audio_manager", None)
            listener = self._focus_listener
            if am is not None and listener is not None:
                try:
                    am.abandonAudioFocus(listener)
                except Exception:
                    pass
            if activity is not None:
                Service = autoclass(activity.getPackageName() + ".ServiceMediaplayback")
                Service.stop(activity)
        finally:
            self._focus_listener = None
            self._audio_manager = None
            self._started = False


def get_session():
    """Return the process-wide Android media session (created once)."""
    global _SESSION
    with _LOCK:
        if _SESSION is None:
            _SESSION = AndroidMediaSession()
        return _SESSION
