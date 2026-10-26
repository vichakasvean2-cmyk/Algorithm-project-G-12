from __future__ import annotations

import math
import struct
import sys
import time

from src.audio_manager import AudioManager
from src.camera_control import CameraControl
from src.config import FPS, WINDOW_HEIGHT, WINDOW_WIDTH
from src.renderer import GameRenderer
from src.tiger_cows_game import TigerCowsGame

try:
    import pygame
except ImportError:  
    pygame = None

COUNTDOWN_SECONDS = 2


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
    pygame.display.set_caption("Kla Si Ko")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    renderer = GameRenderer(screen)
    game = TigerCowsGame()
    camera = CameraControl()
    audio = AudioManager()
    previous_pinching = False
    previous_hand_side: str | None = None
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
                result_sound = "draw" if winner == "Draw" else "win" if winner == "Cows" else "lose"
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
            if renderer.home_start_at(screen_position):
                request_start()
        else:
            if game.winner is None and not renderer.is_animating(game):
                node = renderer.board_node_at(board_position)
                if node is not None:
                    apply_node(node, gesture=True)

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
                        if renderer.home_start_at(event.pos):
                            request_start()

            smile_triggered = camera.consume_smile_trigger()
            if not in_game and not settings_open and countdown_started_at is None and smile_triggered:
                request_start()

            camera_screen_position = (
                renderer.camera_point_to_screen(camera_point, screen.get_size())
                if camera_point is not None
                else None
            )
            hand_side = camera.get_hand_side()
            camera_ui_target = (
                camera_screen_position is not None
                and renderer.camera_ui_target_at(
                    camera_screen_position,
                    in_game,
                    settings_open,
                    game.winner is not None,
                )
            )

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

            if camera_screen_position is not None and pinching and (
                not previous_pinching or hand_side != previous_hand_side
            ):
                board_position = renderer.camera_point_to_board(camera_point)
                if (
                    not in_game
                    or camera_ui_target
                    or (game.turn == "tigers" and hand_side == "Left")
                    or (game.turn == "cows" and hand_side == "Right")
                ):
                    handle_camera_click(camera_screen_position, board_position)
            previous_pinching = pinching
            previous_hand_side = hand_side

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
                    camera_point=None if camera_ui_target else camera_point,
                    pinching=pinching,
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
            if camera_screen_position is not None and (
                not in_game or settings_open or camera_ui_target
            ):
                renderer.draw_camera_pointer(camera_screen_position, pinching)
            pygame.display.flip()
            clock.tick(FPS)
    finally:
        camera.close()
        pygame.quit()


if __name__ == "__main__":
    main()
