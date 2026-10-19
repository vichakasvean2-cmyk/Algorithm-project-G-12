from __future__ import annotations

import math
import struct
import sys

from src.camera_control import CameraControl
from src.config import FPS, WINDOW_HEIGHT, WINDOW_WIDTH
from src.renderer import GameRenderer
from src.tiger_cows_game import TigerCowsGame

try:
    import pygame
except ImportError:  # pragma: no cover - runtime dependency check
    pygame = None


def _startup_sound_samples(sample_rate: int = 22050, duration: float = 0.7) -> bytes:
    total_samples = int(sample_rate * duration)
    fade_in_samples = int(sample_rate * 0.08)
    fade_out_samples = int(sample_rate * 0.24)
    sound_data = bytearray()

    for i in range(total_samples):
        t = i / sample_rate
        fade_in = min(1.0, i / fade_in_samples)
        fade_out = min(1.0, (total_samples - 1 - i) / fade_out_samples)
        fade_in = fade_in * fade_in * (3 - 2 * fade_in)
        fade_out = fade_out * fade_out * (3 - 2 * fade_out)
        decay = math.exp(-2.2 * t)
        tone = math.sin(2 * math.pi * 660 * t) * 0.7 + math.sin(2 * math.pi * 880 * t) * 0.3
        sample = int(tone * 0.3 * fade_in * fade_out * decay * 32767)
        sound_data.extend(struct.pack("<h", sample))

    return bytes(sound_data)


def play_startup_sound() -> None:
    if pygame is None:
        return

    try:
        if pygame.mixer.get_init() is None:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        sound = pygame.mixer.Sound(buffer=_startup_sound_samples())
        sound.set_volume(0.6)
        sound.play()
    except pygame.error as exc:
        print(f"Startup sound unavailable: {exc}")


def main() -> None:
    if pygame is None:
        print("The game requires pygame-ce. Install it with: python -m pip install pygame-ce")
        sys.exit(1)

    pygame.init()
    pygame.display.set_caption("Tigers and Cows")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    renderer = GameRenderer(screen)
    game = TigerCowsGame()
    camera = CameraControl()
    previous_pinching = False
    in_game = False

    def start_game() -> None:
        nonlocal in_game
        game.reset()
        in_game = True
        camera.set_smile_detection_enabled(False)
        play_startup_sound()

    try:
        running = True
        while running:
            camera_frame, camera_point, pinching, camera_status, camera_ready = camera.get_state()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        running = False
                    elif event.key in (pygame.K_ESCAPE, pygame.K_h):
                        if in_game:
                            in_game = False
                            camera.set_smile_detection_enabled(True)
                        else:
                            running = False
                    elif event.key in (pygame.K_SPACE, pygame.K_RETURN) and not in_game:
                        start_game()
                    elif event.key == pygame.K_r:
                        game.reset()
                    elif event.key == pygame.K_1:
                        game.set_level("Beginner")
                    elif event.key == pygame.K_2:
                        game.set_level("Normal")
                    elif event.key == pygame.K_3:
                        game.set_level("Hard")
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if not in_game:
                        level = renderer.home_level_at(event.pos)
                        if level is not None:
                            game.set_level(level)
                        elif renderer.home_start_at(event.pos):
                            start_game()
                    else:
                        level = renderer.level_at(event.pos)
                        if level is not None:
                            game.set_level(level)
                        else:
                            node = renderer.board_node_at(event.pos)
                            if node is not None and not renderer.is_animating(game):
                                game.click_node(node)

            smile_triggered = camera.consume_smile_trigger()
            if not in_game and smile_triggered:
                start_game()

            if (
                in_game
                and camera_point is not None
                and pinching
                and not previous_pinching
                and not renderer.is_animating(game)
            ):
                cursor_position = renderer.camera_point_to_board(camera_point)
                node = renderer.board_node_at(cursor_position)
                if node is not None:
                    game.click_node(node)
            previous_pinching = pinching

            if not camera_ready:
                camera_status = camera_status or "Starting camera..."
            elif (
                camera_point is None
                and "error" not in camera_status.lower()
                and "no webcam" not in camera_status.lower()
                and "install" not in camera_status.lower()
                and "could not" not in camera_status.lower()
            ):
                camera_status = "Show hand to camera"

            if in_game:
                renderer.render(
                    screen,
                    game,
                    camera_frame=camera_frame,
                    camera_point=camera_point,
                    pinching=pinching,
                    camera_status=camera_status,
                )
            else:
                renderer.render_home(screen, game, camera_frame=camera_frame, camera_status=camera_status)
            pygame.display.flip()
            clock.tick(FPS)
    finally:
        camera.close()
        pygame.quit()


if __name__ == "__main__":
    main()
