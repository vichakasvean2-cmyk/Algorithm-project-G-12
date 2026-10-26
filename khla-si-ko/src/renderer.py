from __future__ import annotations

import math
import time

try:
    import pygame
except ImportError:  
    pygame = None

from src.tiger_cows_game import BOARD_SIZE, COW, COW_COUNT, TIGER, TigerCowsGame

BOARD_LEFT = 72
BOARD_TOP = 168
BOARD_SPACING = 128
CELL_SIZE = BOARD_SPACING
BOARD_FRAME = 18
TIGER_MOVE_ANIMATION_SECONDS = 0.82
TIGER_JUMP_ANIMATION_SECONDS = 1.25
COW_MOVE_ANIMATION_SECONDS = 0.52

WOOD_DARK = (65, 38, 22)
WOOD_LIGHT = (184, 132, 71)
GOLD = (229, 177, 73)
CREAM = (247, 224, 174)
TEXT_DARK = (59, 34, 19)


def _interpolate_position(
    start: tuple[int, int],
    end: tuple[int, int],
    progress: float,
) -> tuple[int, int]:
    progress = max(0.0, min(1.0, progress))
    eased_progress = progress * progress * progress * (progress * (progress * 6 - 15) + 10)
    return (
        round(start[0] + (end[0] - start[0]) * eased_progress),
        round(start[1] + (end[1] - start[1]) * eased_progress),
    )


def _move_animation_duration(move: tuple[int, int, str]) -> float:
    source, destination, piece = move
    distance = math.hypot(
        (destination % BOARD_SIZE) - (source % BOARD_SIZE),
        (destination // BOARD_SIZE) - (source // BOARD_SIZE),
    )
    if piece == TIGER:
        if distance > 1:
            return TIGER_JUMP_ANIMATION_SECONDS
        return TIGER_MOVE_ANIMATION_SECONDS
    return COW_MOVE_ANIMATION_SECONDS


class GameRenderer:
    def __init__(self, screen):
        self.screen = screen
        self._fonts = {}
        self._animated_move_count = -1
        self._animation_started_at = 0.0
        self._result_winner: str | None = None
        self._result_started_at = 0.0
        self._background = self._make_wood_background(screen.get_size())

    @staticmethod
    def _node_center(node: int) -> tuple[int, int]:
        row, column = divmod(node, BOARD_SIZE)
        return (
            BOARD_LEFT + column * CELL_SIZE + CELL_SIZE // 2,
            BOARD_TOP + row * CELL_SIZE + CELL_SIZE // 2,
        )

    @staticmethod
    def board_node_at(position: tuple[int, int]) -> int | None:
        x, y = position
        column = (x - BOARD_LEFT) // CELL_SIZE
        row = (y - BOARD_TOP) // CELL_SIZE
        if not (0 <= row < BOARD_SIZE and 0 <= column < BOARD_SIZE):
            return None
        return row * BOARD_SIZE + column

    @staticmethod
    @staticmethod
    def home_start_at(position: tuple[int, int]) -> bool:
        x, y = position
        return 250 <= x <= 690 and 360 <= y <= 450

    @staticmethod
    def settings_button_at(position: tuple[int, int]) -> bool:
        x, y = position
        return (850 <= x <= 1115 and 590 <= y <= 625) or (988 <= x <= 1228 and 598 <= y <= 641)

    @staticmethod
    def result_back_at(position: tuple[int, int]) -> bool:
        x, y = position
        return 530 <= x <= 750 and 420 <= y <= 465

    @staticmethod
    def settings_option_at(position: tuple[int, int]) -> str | None:
        x, y = position
        if not 420 <= x <= 860:
            return None
        if 275 <= y <= 325:
            return "audio"
        if 345 <= y <= 395:
            return "countdown"
        if 415 <= y <= 465:
            return "gesture"
        if 485 <= y <= 530:
            return "close"
        return None

    @staticmethod
    def camera_point_to_board(point: tuple[float, float]) -> tuple[int, int]:
        x, y = point
        x = max(0.0, min(1.0, 1.0 - x))
        y = max(0.0, min(1.0, y))
        return (
            round(BOARD_LEFT + CELL_SIZE // 2 + x * CELL_SIZE * (BOARD_SIZE - 1)),
            round(BOARD_TOP + CELL_SIZE // 2 + y * CELL_SIZE * (BOARD_SIZE - 1)),
        )

    @staticmethod
    def camera_point_to_screen(
        point: tuple[float, float],
        screen_size: tuple[int, int],
    ) -> tuple[int, int]:
        x, y = point
        x = max(0.0, min(1.0, 1.0 - x))
        y = max(0.0, min(1.0, y))
        return round(x * (screen_size[0] - 1)), round(y * (screen_size[1] - 1))

    @staticmethod
    def camera_ui_target_at(
        position: tuple[int, int],
        in_game: bool,
        settings_open: bool,
        game_over: bool,
    ) -> bool:
        if settings_open:
            return GameRenderer.settings_option_at(position) is not None
        if in_game:
            return (
                GameRenderer.settings_button_at(position)
                or (game_over and GameRenderer.result_back_at(position))
            )
        return (
            GameRenderer.settings_button_at(position)
            or GameRenderer.home_start_at(position)
        )

    def draw_camera_pointer(self, position: tuple[int, int], pinching: bool = False) -> None:
        color = (255, 222, 82) if pinching else (94, 233, 161)
        pygame.draw.circle(self.screen, color, position, 18, 3)
        pygame.draw.circle(self.screen, color, position, 5 if pinching else 3)

    @staticmethod
    def _make_wood_background(size: tuple[int, int]):
        background = pygame.Surface(size)
        background.fill((119, 76, 41))
        width, height = size
        grain_colors = ((126, 82, 45), (105, 65, 35), (132, 87, 49))
        for y in range(5, height, 11):
            offset = (y * 17 % 21) - 10
            pygame.draw.line(
                background,
                grain_colors[(y // 11) % len(grain_colors)],
                (0, y),
                (width, y + offset),
                1,
            )
        for y in range(88, height, 220):
            pygame.draw.line(background, (91, 55, 30), (0, y), (width, y), 2)
            pygame.draw.line(background, (145, 99, 54), (0, y + 3), (width, y + 3), 1)
        return background

    def _draw_text(
        self,
        text: str,
        x: int,
        y: int,
        size: int = 25,
        color=CREAM,
        bold: bool = False,
        center: bool = False,
        serif: bool = False,
    ) -> None:
        font_key = (size, bold, serif)
        font = self._fonts.get(font_key)
        if font is None:
            font_name = "Georgia" if serif else None
            font = pygame.font.SysFont(font_name, size, bold=bold)
            self._fonts[font_key] = font
        surface = font.render(text, True, color)
        position = (x - surface.get_width() // 2, y) if center else (x, y)
        self.screen.blit(surface, position)

    def _draw_wrapped_text(
        self,
        text: str,
        x: int,
        y: int,
        max_width: int,
        size: int,
        color,
        line_spacing: int,
    ) -> None:
        font_key = (size, False, False)
        font = self._fonts.get(font_key)
        if font is None:
            font = pygame.font.SysFont(None, size)
            self._fonts[font_key] = font

        lines = []
        current_line = ""
        for word in text.split():
            candidate = f"{current_line} {word}".strip()
            if current_line and font.size(candidate)[0] > max_width:
                lines.append(current_line)
                current_line = word
            else:
                current_line = candidate
        if current_line:
            lines.append(current_line)

        for index, line in enumerate(lines):
            self._draw_text(line, x, y + index * line_spacing, size=size, color=color)

    def _draw_piece(self, piece: str, center: tuple[int, int], selected: bool = False) -> None:
        x, y = center
        if selected:
            pygame.draw.circle(self.screen, (255, 222, 82), center, 51)
            pygame.draw.circle(self.screen, (255, 245, 186), center, 45, 3)

        pygame.draw.ellipse(self.screen, (24, 16, 12), (x - 37, y + 31, 74, 17))
        if piece == TIGER:
            self._draw_tiger(x, y)
        else:
            self._draw_cow(x, y)

    def _draw_tiger(self, x: int, y: int) -> None:
        pygame.draw.polygon(self.screen, (116, 53, 23), ((x - 29, y - 20), (x - 26, y - 43), (x - 8, y - 27)))
        pygame.draw.polygon(self.screen, (116, 53, 23), ((x + 29, y - 20), (x + 26, y - 43), (x + 8, y - 27)))
        pygame.draw.circle(self.screen, (225, 111, 37), (x - 23, y - 24), 11)
        pygame.draw.circle(self.screen, (225, 111, 37), (x + 23, y - 24), 11)
        pygame.draw.circle(self.screen, (234, 133, 44), (x, y), 36)
        pygame.draw.ellipse(self.screen, (255, 222, 164), (x - 20, y - 1, 40, 27))
        pygame.draw.line(self.screen, (77, 38, 22), (x - 6, y - 34), (x - 2, y - 25), 3)
        pygame.draw.line(self.screen, (77, 38, 22), (x + 6, y - 34), (x + 2, y - 25), 3)
        pygame.draw.polygon(self.screen, (77, 38, 22), ((x - 25, y - 22), (x - 13, y - 17), (x - 20, y - 10)))
        pygame.draw.polygon(self.screen, (77, 38, 22), ((x + 25, y - 22), (x + 13, y - 17), (x + 20, y - 10)))
        pygame.draw.circle(self.screen, (255, 255, 236), (x - 12, y - 7), 7)
        pygame.draw.circle(self.screen, (255, 255, 236), (x + 12, y - 7), 7)
        pygame.draw.circle(self.screen, (32, 24, 18), (x - 11, y - 6), 3)
        pygame.draw.circle(self.screen, (32, 24, 18), (x + 11, y - 6), 3)
        pygame.draw.polygon(self.screen, (70, 38, 27), ((x - 5, y + 8), (x + 5, y + 8), (x, y + 13)))
        pygame.draw.arc(self.screen, (79, 42, 27), (x - 12, y + 8, 12, 12), 3.1, 5.8, 2)
        pygame.draw.arc(self.screen, (79, 42, 27), (x, y + 8, 12, 12), 3.1, 5.8, 2)

    def _draw_cow(self, x: int, y: int) -> None:
        pygame.draw.polygon(self.screen, (248, 223, 164), ((x - 24, y - 25), (x - 33, y - 40), (x - 12, y - 35)))
        pygame.draw.polygon(self.screen, (248, 223, 164), ((x + 24, y - 25), (x + 33, y - 40), (x + 12, y - 35)))
        pygame.draw.ellipse(self.screen, (248, 245, 222), (x - 34, y - 31, 68, 66))
        pygame.draw.ellipse(self.screen, (38, 35, 31), (x - 25, y - 22, 17, 20))
        pygame.draw.ellipse(self.screen, (38, 35, 31), (x + 11, y - 12, 16, 21))
        pygame.draw.circle(self.screen, (255, 255, 247), (x - 11, y - 5), 6)
        pygame.draw.circle(self.screen, (255, 255, 247), (x + 11, y - 5), 6)
        pygame.draw.circle(self.screen, (31, 27, 24), (x - 10, y - 4), 3)
        pygame.draw.circle(self.screen, (31, 27, 24), (x + 10, y - 4), 3)
        pygame.draw.ellipse(self.screen, (231, 142, 151), (x - 18, y + 7, 36, 21))
        pygame.draw.circle(self.screen, (146, 79, 86), (x - 8, y + 17), 2)
        pygame.draw.circle(self.screen, (146, 79, 86), (x + 8, y + 17), 2)

    def _animation_state(self, game: TigerCowsGame) -> tuple[tuple[int, int, str], float] | None:
        if game.last_move is None:
            return None

        now = time.perf_counter()
        if game.move_count != self._animated_move_count:
            self._animated_move_count = game.move_count
            self._animation_started_at = now

        progress = (now - self._animation_started_at) / _move_animation_duration(game.last_move)
        if progress >= 1:
            return None
        return game.last_move, max(0.0, progress)

    def is_animating(self, game: TigerCowsGame) -> bool:
        return self._animation_state(game) is not None

    def _draw_board(self, game: TigerCowsGame) -> None:
        animation = self._animation_state(game)
        animated_move = animation[0] if animation is not None else None

        board_rect = pygame.Rect(
            BOARD_LEFT - BOARD_FRAME,
            BOARD_TOP - BOARD_FRAME,
            BOARD_SIZE * CELL_SIZE + BOARD_FRAME * 2,
            BOARD_SIZE * CELL_SIZE + BOARD_FRAME * 2,
        )
        pygame.draw.rect(self.screen, (53, 31, 19), board_rect.inflate(8, 8), border_radius=10)
        pygame.draw.rect(self.screen, WOOD_LIGHT, board_rect, border_radius=8)
        pygame.draw.rect(self.screen, WOOD_DARK, board_rect, 5, border_radius=8)
        pygame.draw.rect(self.screen, CREAM, board_rect.inflate(-8, -8), 2, border_radius=6)

        targets = set(game.legal_targets(game.selected_node)) if game.selected_node is not None else set()
        for row in range(BOARD_SIZE):
            for column in range(BOARD_SIZE):
                node = row * BOARD_SIZE + column
                rect = pygame.Rect(
                    BOARD_LEFT + column * CELL_SIZE,
                    BOARD_TOP + row * CELL_SIZE,
                    CELL_SIZE,
                    CELL_SIZE,
                )
                tile_color = (47, 30, 23) if (row + column) % 2 else (151, 91, 39)
                pygame.draw.rect(self.screen, tile_color, rect)
                pygame.draw.rect(self.screen, (91, 55, 30), rect, 1)
                pygame.draw.line(self.screen, (tile_color[0] + 18, tile_color[1] + 13, tile_color[2] + 9),
                                 (rect.x + 8, rect.y + 8), (rect.right - 8, rect.y + 8), 1)

                center = self._node_center(node)
                is_available_placement = (
                    game.turn == "cows"
                    and game.cows_remaining > 0
                    and game.board[node] is None
                )
                if node in targets:
                    pygame.draw.rect(self.screen, (91, 231, 123), rect.inflate(-12, -12), 5, border_radius=10)
                elif is_available_placement:
                    pygame.draw.rect(self.screen, (238, 192, 91), rect.inflate(-18, -18), 2, border_radius=10)
                if node == game.selected_node:
                    pygame.draw.rect(self.screen, (255, 226, 103), rect.inflate(-8, -8), 5, border_radius=10)

                piece = game.board[node]
                if animated_move is not None and node == animated_move[1]:
                    piece = None
                if piece is not None:
                    self._draw_piece(piece, center, selected=node == game.selected_node)

        if animated_move is not None:
            source, destination, piece = animated_move
            progress = animation[1]
            position = _interpolate_position(
                self._node_center(source),
                self._node_center(destination),
                progress,
            )
            if piece == TIGER:
                eased_progress = progress * progress * progress * (progress * (progress * 6 - 15) + 10)
                hop_height = round(15 * math.sin(math.pi * eased_progress))
                position = (position[0], position[1] - hop_height)
            self._draw_piece(piece, position)

    def _draw_panel(self, rect, fill=(111, 69, 36)) -> None:
        pygame.draw.rect(self.screen, (54, 32, 20), rect.inflate(6, 6), border_radius=18)
        pygame.draw.rect(self.screen, (202, 151, 82), rect, border_radius=16)
        pygame.draw.rect(self.screen, fill, rect.inflate(-8, -8), border_radius=12)
        pygame.draw.rect(self.screen, (225, 190, 127), rect.inflate(-12, -12), 1, border_radius=10)

    def _draw_camera_preview(self, camera_frame, camera_status: str) -> None:
        preview_rect = pygame.Rect(988, 268, 240, 165)
        pygame.draw.rect(self.screen, (40, 27, 20), preview_rect.inflate(8, 8), border_radius=12)
        pygame.draw.rect(self.screen, (25, 22, 18), preview_rect, border_radius=8)
        if camera_frame is not None:
            mirrored_frame = camera_frame[:, :, ::-1].copy()
            frame_surface = pygame.image.frombuffer(
                mirrored_frame.tobytes(), camera_frame.shape[1::-1], "RGB"
            )
            frame_surface = pygame.transform.flip(frame_surface, True, False)
            self.screen.blit(pygame.transform.scale(frame_surface, preview_rect.size), preview_rect)
        else:
            status_lines = (camera_status[:28], camera_status[28:56])
            for index, line in enumerate(status_lines):
                if line:
                    self._draw_text(line, preview_rect.x + 10, preview_rect.y + 62 + index * 25, size=17)
        pygame.draw.rect(self.screen, GOLD, preview_rect, 2, border_radius=8)
        self._draw_text("CAMERA", preview_rect.centerx, preview_rect.bottom + 9, size=17, bold=True, center=True)

    def _draw_settings_button(self, rect: tuple[int, int, int, int]) -> None:
        button = pygame.Rect(rect)
        pygame.draw.rect(self.screen, (78, 49, 30), button, border_radius=8)
        pygame.draw.rect(self.screen, GOLD, button, 2, border_radius=8)
        self._draw_text("SETTINGS  (S)", button.centerx, button.y + 7, size=17, bold=True, center=True)

    def render_settings_overlay(
        self,
        screen,
        audio_enabled: bool,
        countdown_enabled: bool,
        gesture_enabled: bool,
        audio_available: bool,
    ) -> None:
        if pygame is None:
            return

        shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        shade.fill((20, 12, 7, 190))
        screen.blit(shade, (0, 0))
        panel = pygame.Rect(390, 165, 500, 390)
        self._draw_panel(panel, fill=(96, 57, 31))
        self._draw_text("AUDIO SETTINGS", panel.centerx, 194, size=31, color=GOLD, bold=True, center=True)

        options = (
            ("Audio", audio_enabled, "audio"),
            ("Countdown sound", countdown_enabled, "countdown"),
            ("Gesture confirmation", gesture_enabled, "gesture"),
        )
        for index, (label, enabled, _) in enumerate(options):
            y = 280 + index * 70
            self._draw_text(label, 435, y + 8, size=21, color=CREAM, bold=True)
            state = "ON" if enabled else "OFF"
            button = pygame.Rect(730, y, 115, 43)
            pygame.draw.rect(self.screen, (130, 91, 45) if enabled else (64, 43, 31), button, border_radius=9)
            pygame.draw.rect(self.screen, GOLD, button, 2, border_radius=9)
            self._draw_text(state, button.centerx, button.y + 9, size=19, color=CREAM, bold=True, center=True)

        if not audio_available:
            self._draw_text("Audio device unavailable", panel.centerx, 490, size=16, color=(255, 184, 138), center=True)
        close_button = pygame.Rect(535, 505, 210, 38)
        pygame.draw.rect(self.screen, (78, 49, 30), close_button, border_radius=9)
        pygame.draw.rect(self.screen, GOLD, close_button, 2, border_radius=9)
        self._draw_text("CLOSE  (S / Esc)", close_button.centerx, close_button.y + 8,
                        size=17, color=CREAM, bold=True, center=True)

    def render_countdown(self, screen, count: int) -> None:
        if pygame is None:
            return

        shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        shade.fill((20, 12, 7, 150))
        screen.blit(shade, (0, 0))
        panel = pygame.Rect(445, 240, 390, 245)
        self._draw_panel(panel, fill=(96, 57, 31))
        self._draw_text("GET READY", panel.centerx, 270, size=30, color=GOLD, bold=True, center=True)
        pulse = 1 + 0.05 * math.sin(time.perf_counter() * 7)
        self._draw_text(str(count), panel.centerx, 319, size=round(106 * pulse), color=CREAM,
                        bold=True, center=True)

    def _draw_result_animation(self, game: TigerCowsGame) -> None:
        if game.winner != self._result_winner:
            self._result_winner = game.winner
            self._result_started_at = time.perf_counter()
        if game.winner is None:
            return

        now = time.perf_counter()
        elapsed = now - self._result_started_at
        shade = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        shade.fill((20, 12, 7, 145))
        self.screen.blit(shade, (0, 0))

        center = (self.screen.get_width() // 2, self.screen.get_height() // 2)
        pulse = math.sin(elapsed * 4)
        radius = round(48 + 8 * pulse)
        color = (150, 224, 130) if game.winner == "Cows" else (255, 191, 92)
        if game.winner == "Draw":
            color = (190, 190, 220)
        pygame.draw.circle(self.screen, color, center, radius, 4)

        panel = pygame.Rect(300, 235, 680, 250)
        self._draw_panel(panel, fill=(96, 57, 31))
        result = "DRAW!" if game.winner == "Draw" else f"{game.winner.upper()} WIN!"
        self._draw_text(result, panel.centerx, panel.y + 43, size=42, color=color, bold=True, center=True)
        self._draw_wrapped_text(game.status, panel.x + 55, panel.y + 113, panel.width - 110,
                                24, CREAM, 30)
        back_button = pygame.Rect(530, 420, 220, 45)
        pygame.draw.rect(self.screen, (78, 49, 30), back_button, border_radius=9)
        pygame.draw.rect(self.screen, GOLD, back_button, 2, border_radius=9)
        self._draw_text("BACK TO HOME", back_button.centerx, back_button.y + 11,
                        size=18, color=CREAM, bold=True, center=True)

    def render_home(self, screen, game: TigerCowsGame, camera_frame=None, camera_status: str = "Starting camera...") -> None:
        if pygame is None:
            return

        screen.blit(self._background, (0, 0))
        title_rect = pygame.Rect(18, 14, screen.get_width() - 36, 62)
        pygame.draw.rect(screen, (50, 29, 18), title_rect.inflate(4, 4), border_radius=9)
        pygame.draw.rect(screen, WOOD_LIGHT, title_rect, border_radius=7)
        pygame.draw.rect(screen, WOOD_DARK, title_rect.inflate(-7, -7), 2, border_radius=5)
        self._draw_text("KLA SI KO", title_rect.centerx, title_rect.y + 7, size=43,
                        color=(75, 45, 25), bold=True, center=True, serif=True)
        self._draw_text("KLA SI KO", title_rect.centerx, title_rect.y + 4, size=43,
                        color=CREAM, bold=True, center=True, serif=True)

        self._draw_panel(pygame.Rect(55, 98, screen.get_width() - 110, 586), fill=(117, 75, 40))
        self._draw_text("WELCOME, PLAYER!", 148, 143, size=24, color=GOLD, bold=True)
        self._draw_text("Ready for a challenge?", 148, 188, size=39, color=CREAM, bold=True, serif=True)
        self._draw_text("Trap the tigers or capture all 12 cows.", 150, 244, size=22, color=(249, 228, 190))
        self._draw_text("You can also press SPACE or click the button.", 150, 278, size=19, color=(225, 199, 156))

        start_button = pygame.Rect(250, 360, 440, 90)
        pygame.draw.rect(self.screen, (55, 32, 20), start_button.inflate(6, 6), border_radius=20)
        pygame.draw.rect(self.screen, (226, 174, 76), start_button, border_radius=17)
        pygame.draw.rect(self.screen, (255, 226, 148), start_button.inflate(-8, -8), 2, border_radius=13)
        self._draw_text("START CHALLENGE", start_button.centerx, start_button.y + 12, size=31,
                        color=TEXT_DARK, bold=True, center=True)
        self._draw_text("SMILE AT THE CAMERA TO PLAY", start_button.centerx, start_button.y + 52, size=17,
                        color=(93, 55, 28), bold=True, center=True)

        right_card = pygame.Rect(790, 136, 385, 496)
        self._draw_panel(right_card, fill=(96, 57, 31))
        self._draw_text("YOUR GAME", right_card.centerx, 158, size=23, color=GOLD, bold=True, center=True)
        self._draw_text(f"{COW_COUNT} COWS  ·  4 TIGERS", right_card.centerx, 194,
                        size=19, color=CREAM, bold=True, center=True)

        preview_rect = pygame.Rect(850, 236, 265, 185)
        pygame.draw.rect(self.screen, (40, 27, 20), preview_rect.inflate(8, 8), border_radius=12)
        pygame.draw.rect(self.screen, (25, 22, 18), preview_rect, border_radius=8)
        if camera_frame is not None:
            mirrored_frame = camera_frame[:, :, ::-1].copy()
            frame_surface = pygame.image.frombuffer(
                mirrored_frame.tobytes(), camera_frame.shape[1::-1], "RGB"
            )
            frame_surface = pygame.transform.flip(frame_surface, True, False)
            screen.blit(pygame.transform.scale(frame_surface, preview_rect.size), preview_rect)
        else:
            self._draw_wrapped_text(camera_status, preview_rect.x + 12, preview_rect.y + 57,
                                    preview_rect.width - 24, 17, CREAM, 21)
        pygame.draw.rect(self.screen, GOLD, preview_rect, 2, border_radius=8)
        self._draw_text("CAMERA PREVIEW", preview_rect.centerx, preview_rect.bottom + 9,
                        size=17, bold=True, center=True)
        self._draw_text("Smile and hold for a moment", right_card.centerx, 460, size=18,
                        color=(249, 228, 190), center=True)
        self._draw_text("Left hand: tigers. Right hand: cows.", right_card.centerx, 493, size=16,
                        color=(225, 199, 156), center=True)
        self._draw_text("Press Q to quit", right_card.centerx, 566, size=16,
                        color=(225, 199, 156), center=True)
        self._draw_settings_button((850, 590, 265, 32))

    def render(
        self,
        screen,
        game: TigerCowsGame,
        camera_frame=None,
        camera_point: tuple[float, float] | None = None,
        pinching: bool = False,
        camera_status: str = "Starting camera...",
    ) -> None:
        if pygame is None:
            return

        screen.blit(self._background, (0, 0))

        title_rect = pygame.Rect(18, 14, screen.get_width() - 36, 62)
        pygame.draw.rect(screen, (50, 29, 18), title_rect.inflate(4, 4), border_radius=9)
        pygame.draw.rect(screen, WOOD_LIGHT, title_rect, border_radius=7)
        pygame.draw.rect(screen, WOOD_DARK, title_rect.inflate(-7, -7), 2, border_radius=5)
        self._draw_text("KLA SI KO", title_rect.centerx, title_rect.y + 7, size=43,
                        color=(75, 45, 25), bold=True, center=True, serif=True)
        self._draw_text("KLA SI KO", title_rect.centerx, title_rect.y + 4, size=43,
                        color=CREAM, bold=True, center=True, serif=True)

        self._draw_panel(pygame.Rect(54, 88, 552, 48), fill=(169, 111, 48))
        self._draw_text("COWS", 73, 101, size=19, color=TEXT_DARK, bold=True)
        self._draw_text(f"To place: {game.cows_remaining}", 153, 101, size=18, color=CREAM, bold=True)
        self._draw_text(f"Captured: {game.cows_captured} / 12", 354, 101, size=18, color=CREAM, bold=True)

        board_rect = pygame.Rect(
            BOARD_LEFT - BOARD_FRAME - 8,
            BOARD_TOP - BOARD_FRAME - 8,
            BOARD_SIZE * CELL_SIZE + (BOARD_FRAME + 8) * 2,
            BOARD_SIZE * CELL_SIZE + (BOARD_FRAME + 8) * 2,
        )
        self._draw_panel(board_rect)
        self._draw_board(game)

        panel_rect = pygame.Rect(628, 91, screen.get_width() - 656, 598)
        self._draw_panel(panel_rect, fill=(117, 75, 40))
        tigers_on_board = sum(piece == TIGER for piece in game.board)
        cows_on_board = sum(piece == COW for piece in game.board)

        card_width = 273
        for x, heading, detail, accent in (
            (650, "COWS", f"On board: {cows_on_board}  |  Captured: {game.cows_captured}", (245, 221, 178)),
            (938, "TIGERS", f"On board: {tigers_on_board}", (245, 157, 70)),
        ):
            self._draw_panel(pygame.Rect(x, 106, card_width, 77), fill=(132, 81, 38))
            self._draw_text(heading, x + 17, 118, size=23, color=accent, bold=True)
            self._draw_text(detail, x + 17, 151, size=16, color=CREAM)

        self._draw_text("HOW TO PLAY", 654, 203, size=27, color=CREAM, bold=True)
        instructions = (
            "Camera: left hand tigers; right hand cows.",
            "Cows: pinch a glowing empty square.",
            "Tigers: pinch a tiger, then a green square.",
            "Pinch the selected tiger again to cancel.",
            "Mouse: menus only; hands move pieces.",
            "Cows trap; tigers capture by jumping.",
            "R: restart     Esc/H: home",
        )
        for index, instruction in enumerate(instructions):
            self._draw_text(instruction, 654, 241 + index * 29, size=17, color=(249, 228, 190))

        turn_label = "GAME OVER" if game.game_over else f"{game.turn.upper()}' TURN"
        turn_color = (255, 219, 92) if not game.game_over else (139, 235, 136)
        self._draw_panel(pygame.Rect(650, 511, 308, 75), fill=(102, 59, 30))
        self._draw_text(turn_label, 668, 519, size=24, color=turn_color, bold=True)
        self._draw_wrapped_text(game.status, 668, 547, 270, 15, CREAM, 17)

        self._draw_camera_preview(camera_frame, camera_status)
        if camera_point is not None:
            hand_x, hand_y = self.camera_point_to_board(camera_point)
            cursor_color = (255, 222, 82) if pinching else (94, 233, 161)
            pygame.draw.circle(screen, cursor_color, (hand_x, hand_y), 23, 4)
            if pinching:
                pygame.draw.circle(screen, cursor_color, (hand_x, hand_y), 8)

        self._draw_text("Mouse clicks work too  |  Esc/H: home  |  Q: quit", 654, 650, size=17, color=CREAM)
        self._draw_settings_button((988, 603, 240, 36))
        self._draw_result_animation(game)
