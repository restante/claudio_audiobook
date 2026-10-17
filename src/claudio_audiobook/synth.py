"""Kokoro synthesis with every option the model allows."""

from __future__ import annotations

from claudio_audiobook import espeak, model, voices
from claudio_audiobook.options import Options
from claudio_audiobook.text import CHARS_PER_SECOND

SAMPLE_RATE = 24000


class SynthError(RuntimeError):
    """The model could not produce audio; the message says what to do."""


class Synth:
    """Loads Kokoro once and renders text. Silence of a realistic length when the fake is on."""

    def __init__(self, variant: str = "full") -> None:
        self.variant = variant
        self._kokoro = None

    def _load(self):
        if self._kokoro is None:
            from kokoro_onnx import Kokoro
            from kokoro_onnx.config import EspeakConfig

            espeak.selfcheck()
            found = model.find(self.variant)
            if found is None:
                raise SynthError(
                    "Kokoro model not downloaded; run `claudio-audiobook download-model`"
                )
            self._kokoro = Kokoro(
                str(found[0]),
                str(found[1]),
                espeak_config=EspeakConfig(data_path=espeak.data_path()),
            )
        return self._kokoro

    def render(self, text: str, opts: Options):
        """(float32 samples, sample rate) for `text`."""
        import numpy as np

        if voices.fake():
            seconds = max(0.1, len(text) / CHARS_PER_SECOND / opts.speed)
            return np.zeros(int(seconds * SAMPLE_RATE), dtype="float32"), SAMPLE_RATE
        kokoro = self._load()
        voice = voices.blend(voices.parse(opts.voice), kokoro.get_voice_style)
        samples, rate = kokoro.create(
            text,
            voice=voice,
            speed=opts.speed,
            lang=opts.spoken_lang,
            trim=opts.trim,
            sentence_pause=opts.sentence_pause,
            clause_pause=opts.clause_pause,
        )
        if len(samples) == 0:
            raise SynthError("Kokoro produced no audio for this chapter")
        return samples.astype("float32"), rate


def create_synth(opts: Options):
    """The engine that renders text for these options: Kokoro by default, or Pocket TTS."""
    if opts.engine == "pocket":
        from claudio_audiobook.pocket import PocketSynth

        return PocketSynth()
    return Synth(opts.model)
