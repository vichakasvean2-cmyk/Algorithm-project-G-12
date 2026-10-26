import unittest
import array
import threading
from types import SimpleNamespace
from unittest.mock import Mock, patch

import main
from src.camera_control import CameraControl
from src.renderer import GameRenderer
from src.audio_manager import AudioManager


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
        self.assertEqual(GameRenderer.camera_point_to_screen((0.5, 0.61), (1280, 720)), (640, 439))

    def test_board_square_click_maps_to_its_existing_game_node(self):
        self.assertEqual(GameRenderer.board_node_at((136, 232)), 0)
        self.assertEqual(GameRenderer.board_node_at((200, 296)), 5)
        self.assertIsNone(GameRenderer.board_node_at((600, 700)))

    def test_home_start_button_has_no_level_selection(self):
        self.assertTrue(GameRenderer.home_start_at((400, 400)))
        self.assertFalse(GameRenderer.home_start_at((400, 500)))

    def test_settings_buttons_map_to_their_options(self):
        self.assertTrue(GameRenderer.settings_button_at((900, 600)))
        self.assertTrue(GameRenderer.settings_button_at((1100, 620)))
        self.assertFalse(GameRenderer.settings_button_at((700, 600)))
        self.assertEqual(GameRenderer.settings_option_at((500, 300)), "audio")
        self.assertEqual(GameRenderer.settings_option_at((500, 370)), "countdown")
        self.assertEqual(GameRenderer.settings_option_at((500, 440)), "gesture")
        self.assertEqual(GameRenderer.settings_option_at((600, 510)), "close")
        self.assertIsNone(GameRenderer.settings_option_at((900, 300)))
        self.assertTrue(GameRenderer.result_back_at((640, 440)))
        self.assertFalse(GameRenderer.result_back_at((640, 500)))

    def test_camera_ui_target_detects_home_settings_game_and_result_controls(self):
        self.assertFalse(GameRenderer.camera_ui_target_at((200, 360), False, False, False))
        self.assertTrue(GameRenderer.camera_ui_target_at((400, 400), False, False, False))
        self.assertTrue(GameRenderer.camera_ui_target_at((900, 600), False, False, False))
        self.assertFalse(GameRenderer.camera_ui_target_at((1100, 240), True, False, False))
        self.assertTrue(GameRenderer.camera_ui_target_at((640, 440), True, False, True))
        self.assertTrue(GameRenderer.camera_ui_target_at((780, 300), True, True, False))
        self.assertFalse(GameRenderer.camera_ui_target_at((640, 440), True, False, False))

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
        self.pygame.K_s = 115
        self.pygame.display.set_mode.return_value = Mock()
        self.pygame.display.set_mode.return_value.get_size.return_value = (1280, 720)
        self.pygame.time.Clock.return_value = Mock()
        self.game = Mock()
        self.game.winner = None
        self.game.turn = "cows"
        self.renderer = Mock()
        self.renderer.board_node_at.return_value = 5
        self.renderer.home_start_at.return_value = False
        self.renderer.settings_button_at.return_value = False
        self.renderer.settings_option_at.return_value = None
        self.renderer.result_back_at.return_value = False
        self.renderer.camera_point_to_screen.return_value = (640, 440)
        self.renderer.camera_ui_target_at.side_effect = GameRenderer.camera_ui_target_at
        self.renderer.is_animating.return_value = False
        self.camera = Mock()
        self.camera.get_state.return_value = (None, None, False, "Trying camera 0 (Media Foundation)...", False)
        self.camera.get_hand_side.return_value = "Right"
        self.camera.consume_smile_trigger.return_value = False
        self.audio = Mock()
        self.audio.enabled = True
        self.audio.available = True
        self.audio.countdown_enabled = False
        self.audio.gesture_enabled = True
        self.patchers = (
            patch.object(main, "pygame", self.pygame),
            patch.object(main, "TigerCowsGame", return_value=self.game),
            patch.object(main, "GameRenderer", return_value=self.renderer),
            patch.object(main, "CameraControl", return_value=self.camera),
            patch.object(main, "AudioManager", return_value=self.audio),
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

    def test_number_shortcut_does_not_change_fixed_game(self):
        self.pygame.event.get.side_effect = [
            [SimpleNamespace(type=self.pygame.KEYDOWN, key=self.pygame.K_1)],
            [SimpleNamespace(type=self.pygame.QUIT)],
        ]

        main.main()

        self.game.reset.assert_not_called()

    def test_removed_level_control_does_not_change_game(self):
        self.pygame.event.get.side_effect = [
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(700, 240))],
            [SimpleNamespace(type=self.pygame.QUIT)],
        ]
        main.main()

        self.game.reset.assert_not_called()
        self.game.click_node.assert_not_called()

    def test_smile_starts_the_game(self):
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
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 400))],
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
        self.audio.play.assert_called_once_with("gesture")
        self.camera.close.assert_called_once_with()

    def _test_camera_hand_controls_turn(self, turn, hand_side, should_move):
        self.game.turn = turn
        self.camera.get_hand_side.return_value = hand_side
        self.pygame.event.get.side_effect = [
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 400))],
            [],
            [SimpleNamespace(type=self.pygame.QUIT)],
        ]
        self.renderer.home_start_at.return_value = True
        self.camera.get_state.side_effect = [
            (None, None, False, "Show your hand", True),
            (None, (0.5, 0.5), True, "Show your hand", True),
            (None, None, False, "Show your hand", True),
        ]

        main.main()

        if should_move:
            self.game.click_node.assert_called_once_with(5)
        else:
            self.game.click_node.assert_not_called()

    def test_left_hand_controls_tiger_turn(self):
        self._test_camera_hand_controls_turn("tigers", "Left", True)

    def test_right_hand_cannot_control_tiger_turn(self):
        self._test_camera_hand_controls_turn("tigers", "Right", False)

    def test_left_hand_cannot_control_cow_turn(self):
        self._test_camera_hand_controls_turn("cows", "Left", False)

    def test_right_hand_controls_cow_turn(self):
        self._test_camera_hand_controls_turn("cows", "Right", True)

    def test_settings_overlay_toggles_audio_options(self):
        self.pygame.event.get.side_effect = [
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(900, 600))],
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(500, 300))],
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(500, 370))],
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(500, 440))],
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(600, 510))],
            [SimpleNamespace(type=self.pygame.QUIT)],
        ]
        self.renderer.settings_button_at.side_effect = [True]
        self.renderer.settings_option_at.side_effect = ["audio", "countdown", "gesture", "close"]

        main.main()

        self.assertFalse(self.audio.enabled)
        self.assertTrue(self.audio.countdown_enabled)
        self.assertFalse(self.audio.gesture_enabled)
        self.assertEqual(self.renderer.render_settings_overlay.call_count, 4)

    def test_countdown_delays_start_and_plays_countdown_sound(self):
        self.pygame.event.get.side_effect = [
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 500))],
            [SimpleNamespace(type=self.pygame.QUIT)],
        ]
        self.renderer.home_start_at.return_value = True
        self.audio.countdown_enabled = True

        with patch("main.time.perf_counter", side_effect=[10.0, 10.1, 10.2]):
            main.main()

        self.game.reset.assert_not_called()
        self.audio.play.assert_called_once_with("countdown")
        self.renderer.render_countdown.assert_any_call(
            self.pygame.display.set_mode.return_value,
            2,
        )
        self.assertEqual(self.renderer.render_countdown.call_count, 2)

    def test_completed_round_plays_result_sound(self):
        self.pygame.event.get.side_effect = [
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 500))],
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(200, 300))],
            [SimpleNamespace(type=self.pygame.QUIT)],
        ]
        self.renderer.home_start_at.return_value = True

        def win_game(_node):
            self.game.winner = "Cows"
            return True

        self.game.click_node.side_effect = win_game

        main.main()

        self.audio.play.assert_called_once_with("win")

    def _assert_result_back_returns_home(self, winner):
        self.pygame.event.get.side_effect = [
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 500))],
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(200, 300))],
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(640, 440))],
            [SimpleNamespace(type=self.pygame.QUIT)],
        ]
        self.renderer.home_start_at.return_value = True
        self.renderer.result_back_at.return_value = True
        self.game.click_node.side_effect = lambda _node: setattr(self.game, "winner", winner) or True

        main.main()

        self.camera.set_smile_detection_enabled.assert_any_call(True)
        self.assertEqual(self.renderer.render_home.call_count, 2)
        self.assertEqual(self.renderer.render.call_count, 2)

    def test_cows_result_has_back_to_home_button(self):
        self._assert_result_back_returns_home("Cows")

    def test_tigers_result_has_back_to_home_button(self):
        self._assert_result_back_returns_home("Tigers")

    def test_camera_pinch_on_result_back_button_returns_home(self):
        self.pygame.event.get.side_effect = [
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 500))],
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(200, 300))],
            [],
            [SimpleNamespace(type=self.pygame.QUIT)],
        ]
        self.renderer.home_start_at.return_value = True
        self.renderer.result_back_at.return_value = True
        self.game.click_node.side_effect = lambda _node: setattr(self.game, "winner", "Tigers") or True
        self.camera.get_state.side_effect = [
            (None, None, False, "Show your hand", True),
            (None, None, False, "Show your hand", True),
            (None, (0.5, 0.61), True, "Show your hand", True),
            (None, (0.5, 0.61), False, "Show your hand", True),
        ]

        main.main()

        self.renderer.camera_point_to_screen.assert_any_call(
            (0.5, 0.61),
            (1280, 720),
        )
        self.camera.set_smile_detection_enabled.assert_any_call(True)
        self.assertEqual(self.renderer.render_home.call_count, 2)

    def test_camera_pinch_starts_game_without_level_selection(self):
        self.pygame.event.get.side_effect = [[], [], [SimpleNamespace(type=self.pygame.QUIT)]]
        self.camera.get_state.side_effect = [
            (None, (0.5, 0.5), True, "Show your hand", True),
            (None, (0.5, 0.5), False, "Show your hand", True),
            (None, None, False, "Show your hand", True),
        ]
        self.renderer.camera_point_to_screen.side_effect = [(400, 400), (400, 400)]
        self.renderer.home_start_at.side_effect = GameRenderer.home_start_at
        self.renderer.settings_button_at.side_effect = GameRenderer.settings_button_at

        main.main()

        self.game.reset.assert_called_once_with()
        self.camera.set_smile_detection_enabled.assert_called_once_with(False)

    def test_camera_pinch_uses_board_input_instead_of_difficulty_selection(self):
        self.pygame.event.get.side_effect = [
            [SimpleNamespace(type=self.pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 500))],
            [],
            [],
            [SimpleNamespace(type=self.pygame.QUIT)],
        ]
        self.renderer.home_start_at.return_value = True
        self.renderer.camera_point_to_screen.side_effect = [
            (1100, 240), (1100, 240), (1100, 240),
        ]
        self.renderer.settings_button_at.side_effect = GameRenderer.settings_button_at
        self.camera.get_state.side_effect = [
            (None, None, False, "Show your hand", True),
            (None, (0.5, 0.5), True, "Show your hand", True),
            (None, (0.5, 0.5), False, "Show your hand", True),
            (None, None, False, "Show your hand", True),
        ]

        main.main()

        self.game.click_node.assert_called_once_with(5)

    def test_camera_pinch_can_open_settings_and_toggle_audio(self):
        self.pygame.event.get.side_effect = [[], [], [], [], [SimpleNamespace(type=self.pygame.QUIT)]]
        self.camera.get_state.side_effect = [
            (None, (0.5, 0.5), True, "Show your hand", True),
            (None, (0.5, 0.5), False, "Show your hand", True),
            (None, (0.5, 0.5), True, "Show your hand", True),
            (None, (0.5, 0.5), False, "Show your hand", True),
            (None, None, False, "Show your hand", True),
        ]
        self.renderer.camera_point_to_screen.side_effect = [
            (900, 600), (900, 600), (780, 300), (780, 300), (780, 300),
        ]
        self.renderer.settings_button_at.side_effect = GameRenderer.settings_button_at
        self.renderer.settings_option_at.side_effect = GameRenderer.settings_option_at

        main.main()

        self.assertFalse(self.audio.enabled)


if __name__ == "__main__":
    unittest.main()
