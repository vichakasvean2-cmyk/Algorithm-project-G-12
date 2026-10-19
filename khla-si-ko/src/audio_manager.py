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
    "win": ((523, 659, 784), 0.45),
    "lose": ((392, 330, 262), 0.5),
    "draw": ((440, 440), 0.42),
}


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
        if sound_name not in _SOUND_NOTES:
            raise ValueError(f"Unknown sound: {sound_name}")
        if not self.available or not self.enabled or pygame is None:
            return
        if sound_name == "countdown" and not self.countdown_enabled:
            return
        if sound_name == "gesture" and not self.gesture_enabled:
            return

        sound = self._sounds.get(sound_name)
        if sound is None:
            notes, duration = _SOUND_NOTES[sound_name]
            sound = pygame.mixer.Sound(buffer=_sound_samples(notes, duration))
            self._sounds[sound_name] = sound
        sound.play()
