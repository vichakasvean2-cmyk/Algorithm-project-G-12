import unittest
import array
import threading
from types import SimpleNamespace
from unittest.mock import Mock, patch

import main
from src.camera_control import CameraControl
from src.renderer import GameRenderer


class MainTests(unittest.TestCase):
    def test_startup_sound_has_a_soft_attack_and_fade_out(self):
        samples = array.array("h")
        samples.frombytes(main._startup_sound_samples())

        self.assertEqual(samples[0], 0)
        self.assertEqual(samples[-1], 0)
        self.assertGreater(max(abs(sample) for sample in samples), 1000)
        self.assertLess(max(abs(sample) for sample in samples[:220]), 1000)
        self.assertLess(max(abs(sample) for sample in samples[-220:]), 1000)

    def test_camera_points_map_to_mirrored_board_coordinates(self):
        self.assertEqual(GameRenderer.camera_point_to_board((0.0, 0.0)), (520, 232))
        self.assertEqual(GameRenderer.camera_point_to_board((1.0, 1.0)), (136, 616))
        self.assertEqual(GameRenderer.camera_point_to_board((0.5, 0.5)), (328, 424))

    def test_board_square_click_maps_to_its_existing_game_node(self):
        self.assertEqual(GameRenderer.board_node_at((136, 232)), 0)
        self.assertEqual(GameRenderer.board_node_at((200, 296)), 5)
        self.assertIsNone(GameRenderer.board_node_at((600, 700)))

    def test_level_buttons_map_to_difficulty_levels(self):
        self.assertEqual(GameRenderer.level_at((700, 240)), "Beginner")
        self.assertEqual(GameRenderer.level_at((900, 240)), "Normal")
        self.assertEqual(GameRenderer.level_at((1100, 240)), "Hard")
        self.assertIsNone(GameRenderer.level_at((700, 280)))

    def test_home_buttons_map_to_levels_and_start(self):
        self.assertEqual(GameRenderer.home_level_at((200, 360)), "Beginner")
        self.assertEqual(GameRenderer.home_level_at((400, 360)), "Normal")
        self.assertEqual(GameRenderer.home_level_at((600, 360)), "Hard")
        self.assertIsNone(GameRenderer.home_level_at((200, 420)))
        self.assertTrue(GameRenderer.home_start_at((400, 500)))
        self.assertFalse(GameRenderer.home_start_at((400, 560)))

    def setUp(self):
        self.pygame = Mock()
        self.pygame.QUIT = 1
        self.pygame.KEYDOWN = 2
        self.pygame.MOUSEBUTTONDOWN = 3
        self.pygame.K_ESCAPE = 27
        self.pygame.K_h = 104
        self.pygame.K_q = 113
        self.pygame.K_r = 114
        self.pygame.K_1 = 49
        self.pygame.K_2 = 50
        self.pygame.K_3 = 51
        self.pygame.K_SPACE = 32
        self.pygame.K_RETURN = 13
        self.pygame.display.set_mode.return_value = object()
        self.pygame.time.Clock.return_value = Mock()
        self.game = Mock()
        self.renderer = Mock()
        self.renderer.board_node_at.return_value = 5
        self.renderer.level_at.return_value = None
        self.renderer.home_level_at.return_value = None
        self.renderer.home_start_at.return_value = False
        self.renderer.is_animating.return_value = False
        self.camera = Mock()
        self.camera.get_state.return_value = (None, None, False, "Trying camera 0 (Media Foundation)...", False)
        self.camera.consume_smile_trigger.return_value = False
        self.patchers = (
            patch.object(main, "pygame", self.pygame),
            patch.object(main, "TigerCowsGame", return_value=self.game),
            patch.object(main, "GameRenderer", return_value=self.renderer),
            patch.object(main, "CameraControl", return_value=self.camera),
        )
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_board_click_is_sent_to_game(self):
        self.pygame.event.get.side_effect = [
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 500))],
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(200, 300))],
            [SimpleNamespace(type=self.pygame.QUIT)],
        ]
        self.renderer.home_start_at.return_value = True

        main.main()

        self.game.click_node.assert_called_once_with(5)
        self.pygame.quit.assert_called_once_with()

    def test_camera_startup_progress_is_displayed(self):
        self.pygame.event.get.return_value = [SimpleNamespace(type=self.pygame.QUIT)]
        self.camera.get_state.return_value = (
            None,
            None,
            False,
            "Trying camera 0 (Media Foundation)...",
            False,
        )

        main.main()

        self.renderer.render_home.assert_called_once()
        self.assertEqual(
            self.renderer.render_home.call_args.kwargs["camera_status"],
            "Trying camera 0 (Media Foundation)...",
        )

    def test_reset_key_resets_game(self):
        self.pygame.event.get.side_effect = [
            [SimpleNamespace(type=self.pygame.KEYDOWN, key=self.pygame.K_r)],
            [SimpleNamespace(type=self.pygame.QUIT)],
        ]

        main.main()

        self.game.reset.assert_called_once_with()

    def test_level_shortcut_changes_difficulty(self):
        self.pygame.event.get.side_effect = [
            [SimpleNamespace(type=self.pygame.KEYDOWN, key=self.pygame.K_1)],
            [SimpleNamespace(type=self.pygame.QUIT)],
        ]

        main.main()

        self.game.set_level.assert_called_once_with("Beginner")

    def test_level_button_changes_difficulty_without_placing_a_piece(self):
        self.pygame.event.get.side_effect = [
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(700, 240))],
            [SimpleNamespace(type=self.pygame.QUIT)],
        ]
        self.renderer.home_level_at.return_value = "Beginner"

        main.main()

        self.game.set_level.assert_called_once_with("Beginner")
        self.game.click_node.assert_not_called()

    def test_smile_starts_the_selected_level(self):
        self.pygame.event.get.side_effect = [[], [SimpleNamespace(type=self.pygame.QUIT)]]
        self.camera.consume_smile_trigger.side_effect = [True, False]
        with patch.object(main, "play_startup_sound") as play_sound:
            main.main()

        self.game.reset.assert_called_once_with()
        play_sound.assert_called_once_with()
        self.camera.set_smile_detection_enabled.assert_called_once_with(False)
        self.assertEqual(self.renderer.render.call_count, 2)
        self.renderer.render_home.assert_not_called()

    def test_smile_trigger_is_consumed_only_once(self):
        camera = CameraControl.__new__(CameraControl)
        camera._lock = threading.Lock()
        camera._smile_triggered = True
        camera._smile_detection_enabled = True

        self.assertTrue(camera.consume_smile_trigger())
        self.assertFalse(camera.consume_smile_trigger())
        camera._smile_triggered = True
        camera.set_smile_detection_enabled(False)
        self.assertFalse(camera._smile_detection_enabled)
        self.assertFalse(camera.consume_smile_trigger())

    def test_start_button_enters_game(self):
        self.pygame.event.get.side_effect = [
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 500))],
            [SimpleNamespace(type=self.pygame.QUIT)],
        ]
        self.renderer.home_start_at.return_value = True

        with patch.object(main, "play_startup_sound"):
            main.main()

        self.game.reset.assert_called_once_with()
        self.camera.set_smile_detection_enabled.assert_called_once_with(False)
        self.assertEqual(self.renderer.render.call_count, 2)
        self.renderer.render_home.assert_not_called()

    def test_pinching_on_a_board_dot_sends_move_to_game_once(self):
        self.pygame.event.get.side_effect = [
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 500))],
            [],
            [SimpleNamespace(type=self.pygame.QUIT)],
        ]
        self.renderer.home_start_at.return_value = True
        self.camera.get_state.side_effect = [
            (None, (0.5, 0.5), False, "Show your hand", True),
            (None, (0.5, 0.5), True, "Show your hand", True),
            (None, (0.5, 0.5), False, "Show your hand", True),
        ]
        self.renderer.camera_point_to_board.return_value = (300, 350)

        with patch.object(main, "play_startup_sound"):
            main.main()

        self.renderer.camera_point_to_board.assert_called_once_with((0.5, 0.5))
        self.game.click_node.assert_called_once_with(5)
        self.camera.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
