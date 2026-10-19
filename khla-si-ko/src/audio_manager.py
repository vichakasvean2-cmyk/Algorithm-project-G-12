from __future__ import annotations

import math
from array import array

try:
    import pygame
except ImportError:  # pragma: no cover
    pygame = None


class AudioManager:
    def __init__(self) -> None:
        self.enabled = False
        if pygame is None:
            return
        try:
            pygame.mixer.init()
            self.enabled = True
        except Exception:
            self.enabled = False

    def play(self, sound_name: str) -> None:
        if not self.enabled or pygame is None:
            return

        if sound_name == "win":
            sample_rate = 22050
            samples = array("h")
            for i in range(sample_rate // 3):
                value = int(1800 * math.sin(2 * math.pi * 440 * i / sample_rate))
                samples.append(value)
            sound = pygame.mixer.Sound(buffer=samples.tobytes())
            sound.play()
        elif sound_name == "tie":
            sample_rate = 22050
            samples = array("h")
            for i in range(sample_rate // 6):
                value = int(1200 * math.sin(2 * math.pi * 220 * i / sample_rate))
                samples.append(value)
            sound = pygame.mixer.Sound(buffer=samples.tobytes())
            sound.play()
