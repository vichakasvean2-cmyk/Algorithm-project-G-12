from __future__ import annotations

import math
from array import array

try:
    import pygame
except ImportError:  # pragma: no cover
    pygame = None


_SOUND_NOTES = {
    "countdown": ((660,), 0.12),
    "gesture": ((880, 1175), 0.12),
    "draw": ((440, 440), 0.42),
}
_PROCEDURAL_SOUNDS = {"applause"}


def _sound_samples(notes: tuple[int, ...], duration: float, sample_rate: int = 22050) -> bytes:
    samples = array("h")
    note_duration = duration / len(notes)
    note_samples = int(sample_rate * note_duration)
    fade_samples = max(1, int(sample_rate * 0.015))

    for frequency in notes:
        for index in range(note_samples):
            fade_in = min(1.0, index / fade_samples)
            fade_out = min(1.0, (note_samples - index - 1) / fade_samples)
            envelope = min(fade_in, fade_out)
            value = int(5000 * math.sin(2 * math.pi * frequency * index / sample_rate) * envelope)
            samples.append(value)

    return samples.tobytes()


def _applause_samples(sample_rate: int = 22050, duration: float = 2.4) -> bytes:
    total_samples = int(sample_rate * duration)
    mix = [0.0] * total_samples
    state = 0x5EED
    event_time = 0.05

    while event_time < duration - 0.12:
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        interval = 0.065 + (state % 1000) / 1000 * 0.11
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        amplitude = 6500 + (state % 5500)
        start = int(event_time * sample_rate)
        clap_length = int(sample_rate * 0.09)
        for offset in range(clap_length):
            index = start + offset
            if index >= total_samples:
                break
            state = (state * 1103515245 + 12345) & 0x7FFFFFFF
            noise = (state / 0x7FFFFFFF) * 2 - 1
            decay = math.exp(-offset / (sample_rate * 0.018))
            mix[index] += amplitude * noise * decay
        event_time += interval

    peak = max((abs(value) for value in mix), default=1)
    scale = 18000 / peak if peak else 1
    samples = array("h", (int(value * scale) for value in mix))
    return samples.tobytes()


class AudioManager:
    def __init__(self) -> None:
        self.available = False
        self.enabled = False
        self.countdown_enabled = True
        self.gesture_enabled = True
        self._sounds = {}
        if pygame is None:
            return

        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        except pygame.error as exc:
            print(f"Audio unavailable: {exc}")
            return

        self.available = True
        self.enabled = True

    def play(self, sound_name: str) -> None:
        if sound_name not in _SOUND_NOTES and sound_name not in _PROCEDURAL_SOUNDS:
            raise ValueError(f"Unknown sound: {sound_name}")
        if not self.available or not self.enabled or pygame is None:
            return
        if sound_name == "countdown" and not self.countdown_enabled:
            return
        if sound_name == "gesture" and not self.gesture_enabled:
            return

        sound = self._sounds.get(sound_name)
        if sound is None:
            if sound_name == "applause":
                samples = _applause_samples()
            else:
                notes, duration = _SOUND_NOTES[sound_name]
                samples = _sound_samples(notes, duration)
            sound = pygame.mixer.Sound(buffer=samples)
            self._sounds[sound_name] = sound
        sound.play()
