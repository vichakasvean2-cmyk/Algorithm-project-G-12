import unittest
from unittest.mock import Mock, patch

from src import audio_manager


class AudioManagerTests(unittest.TestCase):
    def test_sound_samples_are_nonempty_and_silent_at_both_ends(self):
        samples = audio_manager._sound_samples((440, 660), 0.2)

        self.assertGreater(len(samples), 0)
        self.assertEqual(samples[:2], b"\x00\x00")
        self.assertEqual(samples[-2:], b"\x00\x00")

    def test_applause_samples_are_nonempty_and_silent_at_both_ends(self):
        samples = audio_manager._applause_samples()

        self.assertGreater(len(samples), 0)
        self.assertEqual(samples[:2], b"\x00\x00")
        self.assertEqual(samples[-2:], b"\x00\x00")

    def test_sounds_are_cached_and_played_when_enabled(self):
        fake_pygame = Mock()
        fake_pygame.mixer.get_init.return_value = (22050, -16, 1)
        sound = Mock()
        fake_pygame.mixer.Sound.return_value = sound

        with patch.object(audio_manager, "pygame", fake_pygame):
            manager = audio_manager.AudioManager()
            manager.play("applause")
            manager.play("applause")

        fake_pygame.mixer.Sound.assert_called_once()
        self.assertEqual(sound.play.call_count, 2)

    def test_optional_sounds_can_be_disabled_independently(self):
        fake_pygame = Mock()
        fake_pygame.mixer.get_init.return_value = (22050, -16, 1)
        with patch.object(audio_manager, "pygame", fake_pygame):
            manager = audio_manager.AudioManager()
            manager.countdown_enabled = False
            manager.gesture_enabled = False
            manager.play("countdown")
            manager.play("gesture")

        fake_pygame.mixer.Sound.assert_not_called()

    def test_unknown_sound_name_is_reported(self):
        manager = audio_manager.AudioManager.__new__(audio_manager.AudioManager)
        manager.available = False
        manager.enabled = False

        with self.assertRaises(ValueError):
            manager.play("unknown")


if __name__ == "__main__":
    unittest.main()
