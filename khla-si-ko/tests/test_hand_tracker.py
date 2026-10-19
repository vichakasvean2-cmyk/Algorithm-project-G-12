import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import src.hand_tracker as hand_tracker_module
from src.hand_tracker import HandTracker


class HandTrackerTests(unittest.TestCase):
    def test_smile_score_uses_both_sides_of_smile(self):
        blendshapes = [
            SimpleNamespace(category_name="mouthSmileLeft", score=0.8),
            SimpleNamespace(category_name="mouthSmileRight", score=0.7),
        ]

        self.assertEqual(HandTracker._smile_score(blendshapes), 0.7)

    def test_smile_must_be_held_before_it_triggers_once(self):
        tracker = HandTracker.__new__(HandTracker)
        tracker._smile_started_at = None
        tracker._smiling = False
        tracker.smile_triggered = False

        self.assertFalse(tracker._update_smile(0.8, 1.0))
        self.assertFalse(tracker._update_smile(0.8, 1.7))
        self.assertTrue(tracker._update_smile(0.8, 1.81))
        self.assertFalse(tracker._update_smile(0.8, 1.9))
        self.assertFalse(tracker._update_smile(0.2, 2.0))
        self.assertFalse(tracker._smiling)

    def test_detect_smile_uses_face_blendshapes(self):
        tracker = HandTracker.__new__(HandTracker)
        tracker.face_landmarker = Mock()
        tracker._smile_started_at = None
        tracker._smiling = False
        tracker.smile_triggered = False
        tracker.face_landmarker.detect.return_value = SimpleNamespace(
            face_blendshapes=[[
                SimpleNamespace(category_name="mouthSmileLeft", score=0.8),
                SimpleNamespace(category_name="mouthSmileRight", score=0.75),
            ]]
        )
        cv2 = SimpleNamespace(COLOR_BGR2RGB=1, cvtColor=Mock(return_value=object()))
        mp = SimpleNamespace(
            Image=Mock(return_value=object()),
            ImageFormat=SimpleNamespace(SRGB=2),
        )

        with (
            patch.object(hand_tracker_module, "cv2", cv2),
            patch.object(hand_tracker_module, "mp", mp),
        ):
            self.assertFalse(tracker.detect_smile(object(), now=4.0))
            self.assertTrue(tracker.detect_smile(object(), now=4.9))

    def test_detect_returns_index_finger_point_and_pinch_state(self):
        frame = object()
        rgb = object()
        image = object()
        landmarks = [SimpleNamespace(x=0.2, y=0.3) for _ in range(21)]
        landmarks[8] = SimpleNamespace(x=0.4, y=0.5)
        landmarks[4] = SimpleNamespace(x=0.42, y=0.51)

        landmarker = Mock()
        landmarker.detect.return_value = SimpleNamespace(hand_landmarks=[landmarks])
        cv2 = SimpleNamespace(COLOR_BGR2RGB=1, cvtColor=Mock(return_value=rgb))
        mp = SimpleNamespace(
            Image=Mock(return_value=image),
            ImageFormat=SimpleNamespace(SRGB=2),
        )
        tracker = HandTracker.__new__(HandTracker)
        tracker.landmarker = landmarker
        tracker.error = None
        tracker._pinching = False

        with (
            patch.object(hand_tracker_module, "cv2", cv2),
            patch.object(hand_tracker_module, "mp", mp),
        ):
            self.assertEqual(tracker.detect(frame), ((0.4, 0.5), True))

        cv2.cvtColor.assert_called_once_with(frame, cv2.COLOR_BGR2RGB)
        landmarker.detect.assert_called_once_with(image)

    def test_detect_reports_not_pinching_when_fingers_are_apart(self):
        landmarks = [SimpleNamespace(x=0.2, y=0.3) for _ in range(21)]
        landmarks[8] = SimpleNamespace(x=0.4, y=0.5)
        landmarks[4] = SimpleNamespace(x=0.6, y=0.7)
        landmarker = Mock()
        landmarker.detect.return_value = SimpleNamespace(hand_landmarks=[landmarks])
        tracker = HandTracker.__new__(HandTracker)
        tracker.landmarker = landmarker
        tracker._pinching = False

        with (
            patch.object(hand_tracker_module, "cv2", SimpleNamespace(COLOR_BGR2RGB=1, cvtColor=Mock(return_value=object()))),
            patch.object(hand_tracker_module, "mp", SimpleNamespace(
                Image=Mock(return_value=object()),
                ImageFormat=SimpleNamespace(SRGB=2),
            )),
        ):
            self.assertEqual(tracker.detect(object()), ((0.4, 0.5), False))

    def test_pinch_hysteresis_prevents_flickering_at_threshold(self):
        distances = iter((0.04, 0.06, 0.08))
        landmarks = [SimpleNamespace(x=0.2, y=0.3) for _ in range(21)]
        landmarks[8] = SimpleNamespace(x=0.4, y=0.5)
        landmarks[4] = SimpleNamespace(x=0.4, y=0.5)
        landmarker = Mock()
        landmarker.detect.side_effect = [
            SimpleNamespace(hand_landmarks=[landmarks]),
            SimpleNamespace(hand_landmarks=[landmarks]),
            SimpleNamespace(hand_landmarks=[landmarks]),
        ]
        tracker = HandTracker.__new__(HandTracker)
        tracker.landmarker = landmarker
        tracker._pinching = False
        cv2 = SimpleNamespace(COLOR_BGR2RGB=1, cvtColor=Mock(return_value=object()))
        mp = SimpleNamespace(
            Image=Mock(return_value=object()),
            ImageFormat=SimpleNamespace(SRGB=2),
        )

        with (
            patch.object(hand_tracker_module, "cv2", cv2),
            patch.object(hand_tracker_module, "mp", mp),
        ):
            states = []
            for distance in distances:
                landmarks[4] = SimpleNamespace(x=landmarks[8].x + distance, y=landmarks[8].y)
                states.append(tracker.detect(object())[1])

        self.assertEqual(states, [True, True, False])


if __name__ == "__main__":
    unittest.main()
