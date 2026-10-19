import unittest

from src.renderer import (
    COW_MOVE_ANIMATION_SECONDS,
    TIGER_JUMP_ANIMATION_SECONDS,
    TIGER_MOVE_ANIMATION_SECONDS,
    _interpolate_position,
    _move_animation_duration,
)
from src.tiger_cows_game import COW, TIGER


class MovementAnimationTests(unittest.TestCase):
    def test_animation_starts_at_source_and_ends_at_destination(self):
        self.assertEqual(_interpolate_position((100, 145), (245, 145), 0), (100, 145))
        self.assertEqual(_interpolate_position((100, 145), (245, 145), 1), (245, 145))

    def test_animation_eases_at_start_and_end(self):
        position = _interpolate_position((0, 0), (100, 100), 0.5)
        self.assertEqual(position, (50, 50))
        early_position = _interpolate_position((0, 0), (100, 0), 0.1)
        self.assertLess(early_position[0], 10)

    def test_animation_progress_is_clamped(self):
        self.assertEqual(_interpolate_position((1, 2), (3, 4), -1), (1, 2))
        self.assertEqual(_interpolate_position((1, 2), (3, 4), 2), (3, 4))

    def test_tiger_animation_moves_gradually_at_game_frame_rate(self):
        positions = [
            _interpolate_position((100, 100), (228, 100), frame / 60)[0]
            for frame in range(61)
        ]
        frame_steps = [end - start for start, end in zip(positions, positions[1:])]

        self.assertEqual(positions[0], 100)
        self.assertEqual(positions[-1], 228)
        self.assertTrue(all(step >= 0 for step in frame_steps))
        self.assertLessEqual(max(frame_steps), 5)

    def test_tiger_and_capture_animations_last_longer_than_cow_move(self):
        self.assertEqual(_move_animation_duration((0, 1, TIGER)), TIGER_MOVE_ANIMATION_SECONDS)
        self.assertEqual(_move_animation_duration((0, 2, TIGER)), TIGER_JUMP_ANIMATION_SECONDS)
        self.assertEqual(_move_animation_duration((5, 6, COW)), COW_MOVE_ANIMATION_SECONDS)


if __name__ == "__main__":
    unittest.main()
