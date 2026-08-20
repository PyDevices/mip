"""PWM / buzzer adapter for :class:`audiodev.ToneOutput`."""

from audiodev import ToneOutput


def _resolve(value):
    return value() if callable(value) else value


class PWMToneOutput(ToneOutput):
    """Tone output around a PWM pin or an object with ``play`` / ``stop``."""

    def __init__(self, pwm, *, session=None, power=None):
        super().__init__(session=session, power=power)
        self._pwm_factory = pwm
        self._pwm = None

    @property
    def pwm(self):
        return self._pwm

    def _open(self):
        self._pwm = _resolve(self._pwm_factory)
        if hasattr(self._pwm, "open"):
            self._pwm.open()

    def _close(self):
        pwm = self._pwm
        self._pwm = None
        if pwm is None:
            return
        if hasattr(pwm, "close"):
            pwm.close()
        elif hasattr(pwm, "deinit"):
            pwm.deinit()

    def _play(self, frequency, level):
        pwm = self._pwm
        if hasattr(pwm, "play"):
            pwm.play(frequency, level)
            return
        pwm.freq(int(frequency))
        duty = level * 32768 // 100
        if hasattr(pwm, "duty_u16"):
            pwm.duty_u16(duty)
        else:
            pwm.duty(level * 512 // 100)

    def _stop(self):
        pwm = self._pwm
        if hasattr(pwm, "stop"):
            pwm.stop()
        elif hasattr(pwm, "duty_u16"):
            pwm.duty_u16(0)
        else:
            pwm.duty(0)


def audio_out(pwm, *, session=None, power=None):
    """Build a :class:`PWMToneOutput` around *pwm* (instance or factory)."""
    return PWMToneOutput(pwm, session=session, power=power)
