from __future__ import annotations

import math
import struct
import sys
import time
# import pygame

from src.audio_manager import AudioManager
from src.camera_control import CameraControl
from src.config import FPS, WINDOW_HEIGHT, WINDOW_WIDTH
from src.renderer import GameRenderer
from pathlib import Path
from src.tiger_cows_game import TigerCowsGame

try:
    import pygame
except ImportError:  # pragma: no cover - runtime dependency check
    pygame = None

COUNTDOWN_SECONDS = 2

# if pygame.mixer.get_init() is None:
#     pygame.mixer.init()

# SOUND_PATH = Path(__file__).resolve().parent / "assets" / "test.ogg"

# print("Sound path:", SOUND_PATH)
# print("File exists:", SOUND_PATH.exists())

# TIGER_WIN_SOUND = pygame.mixer.Sound(str(SOUND_PATH))
# TIGER_WIN_SOUND.set_volume(88.0)


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
    audio = AudioManager()
    previous_hand_pinching = {}
    in_game = False
    settings_open = False
    countdown_started_at: float | None = None
    last_countdown_number = COUNTDOWN_SECONDS + 1
    last_announced_winner: str | None = None

    def start_game() -> None:
        nonlocal in_game, countdown_started_at, last_announced_winner
        game.reset()
        in_game = True
        countdown_started_at = None
        last_announced_winner = None
        camera.set_smile_detection_enabled(False)
        if audio.enabled:
            play_startup_sound()

    def request_start() -> None:
        nonlocal countdown_started_at, last_countdown_number
        if audio.enabled and audio.countdown_enabled:
            countdown_started_at = time.perf_counter()
            last_countdown_number = COUNTDOWN_SECONDS + 1
        else:
            start_game()

    def apply_node(node: int, gesture: bool = False) -> None:
        nonlocal last_announced_winner
        accepted = game.click_node(node)
        if not accepted:
            return

        winner = game.winner
        if winner is not None:
            if winner != last_announced_winner:
                result_sound = "draw" if winner == "Draw" else "applause"
                audio.play(result_sound)
                last_announced_winner = winner
        elif gesture:
            last_announced_winner = None
            audio.play("gesture")
        else:
            last_announced_winner = None

    def handle_camera_click(
        screen_position: tuple[int, int],
        board_position: tuple[int, int],
    ) -> None:
        nonlocal in_game, settings_open
        if settings_open:
            option = renderer.settings_option_at(screen_position)
            if option == "audio":
                audio.enabled = not audio.enabled
            elif option == "countdown":
                audio.countdown_enabled = not audio.countdown_enabled
            elif option == "gesture":
                audio.gesture_enabled = not audio.gesture_enabled
            elif option == "close":
                settings_open = False
            return

        if in_game and game.winner is not None and renderer.result_back_at(screen_position):
            in_game = False
            camera.set_smile_detection_enabled(True)
        elif renderer.settings_button_at(screen_position):
            settings_open = True
        elif not in_game:
            level = renderer.home_level_at(screen_position)
            if level is not None:
                game.set_level(level)
            elif renderer.home_start_at(screen_position):
                request_start()
        else:
            level = renderer.level_at(screen_position)
            if level is not None:
                game.set_level(level)
            elif game.winner is None and not renderer.is_animating(game):
                node = renderer.board_node_at(board_position)
                if node is not None:
                    apply_node(node, gesture=True)

    try:
        running = True
        while running:
            camera_frame, camera_point, pinching, camera_status, camera_ready = camera.get_state()
            hand_states = camera.get_hand_states()
            if not isinstance(hand_states, (tuple, list)):
                hand_states = ()
            if not hand_states and camera_point is not None:
                hand_states = (("primary", camera_point, pinching),)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        running = False
                    elif event.key == pygame.K_s:
                        settings_open = not settings_open
                    elif settings_open and event.key == pygame.K_ESCAPE:
                        settings_open = False
                    elif event.key in (pygame.K_ESCAPE, pygame.K_h):
                        if in_game:
                            in_game = False
                            camera.set_smile_detection_enabled(True)
                        else:
                            running = False
                    elif event.key in (pygame.K_SPACE, pygame.K_RETURN) and not in_game:
                        if not settings_open and countdown_started_at is None:
                            request_start()
                    elif event.key == pygame.K_r:
                        game.reset()
                    elif event.key == pygame.K_1:
                        game.set_level("Beginner")
                    elif event.key == pygame.K_2:
                        game.set_level("Normal")
                    elif event.key == pygame.K_3:
                        game.set_level("Hard")
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if settings_open:
                        option = renderer.settings_option_at(event.pos)
                        if option == "audio":
                            audio.enabled = not audio.enabled
                        elif option == "countdown":
                            audio.countdown_enabled = not audio.countdown_enabled
                        elif option == "gesture":
                            audio.gesture_enabled = not audio.gesture_enabled
                        elif option == "close":
                            settings_open = False
                    elif in_game and game.winner is not None and renderer.result_back_at(event.pos):
                        in_game = False
                        camera.set_smile_detection_enabled(True)
                    elif renderer.settings_button_at(event.pos):
                        settings_open = True
                    elif not in_game:
                        level = renderer.home_level_at(event.pos)
                        if level is not None:
                            game.set_level(level)
                        elif renderer.home_start_at(event.pos):
                            request_start()
                    else:
                        level = renderer.level_at(event.pos)
                        if level is not None:
                            game.set_level(level)
                        else:
                            node = renderer.board_node_at(event.pos)
                            if node is not None and not renderer.is_animating(game):
                                apply_node(node)

            smile_triggered = camera.consume_smile_trigger()
            if not in_game and not settings_open and countdown_started_at is None and smile_triggered:
                request_start()

            hand_positions = tuple(
                (
                    hand_id,
                    point,
                    hand_pinching,
                    renderer.camera_point_to_screen(point, screen.get_size()),
                )
                for hand_id, point, hand_pinching in hand_states
            )
            camera_ui_targets = {
                hand_id: renderer.camera_ui_target_at(
                    screen_position,
                    in_game,
                    settings_open,
                    game.winner is not None,
                )
                for hand_id, _, _, screen_position in hand_positions
            }

            countdown_value: int | None = None
            if countdown_started_at is not None:
                elapsed = time.perf_counter() - countdown_started_at
                if elapsed >= COUNTDOWN_SECONDS:
                    start_game()
                else:
                    countdown_value = COUNTDOWN_SECONDS - int(elapsed)
                    if countdown_value != last_countdown_number:
                        audio.play("countdown")
                        last_countdown_number = countdown_value

            current_hand_pinching = {}
            for hand_id, point, hand_pinching, screen_position in hand_positions:
                current_hand_pinching[hand_id] = hand_pinching
                if hand_pinching and not previous_hand_pinching.get(hand_id, False):
                    board_position = renderer.camera_point_to_board(point)
                    handle_camera_click(screen_position, board_position)
            previous_hand_pinching = current_hand_pinching

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
                    camera_hands=tuple(
                        (point, hand_pinching)
                        for hand_id, point, hand_pinching, _ in hand_positions
                        if not camera_ui_targets[hand_id]
                    ),
                    camera_status=camera_status,
                )
            else:
                renderer.render_home(screen, game, camera_frame=camera_frame, camera_status=camera_status)
            if countdown_value is not None:
                renderer.render_countdown(screen, countdown_value)
            if settings_open:
                renderer.render_settings_overlay(
                    screen,
                    audio_enabled=audio.enabled,
                    countdown_enabled=audio.countdown_enabled,
                    gesture_enabled=audio.gesture_enabled,
                    audio_available=audio.available,
                )
            for hand_id, _, hand_pinching, screen_position in hand_positions:
                if not in_game or settings_open or camera_ui_targets[hand_id]:
                    renderer.draw_camera_pointer(screen_position, hand_pinching)
            pygame.display.flip()
            clock.tick(FPS)
    finally:
        camera.close()
        pygame.quit()


if __name__ == "__main__":
    main()
