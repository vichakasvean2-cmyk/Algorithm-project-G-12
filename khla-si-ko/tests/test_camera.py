import unittest
from unittest.mock import Mock, call, patch

import src.camera as camera_module
from src.camera import Camera


class CameraTests(unittest.TestCase):
    def test_reports_backend_attempt_and_uses_windows_fallback(self):
        failed_capture = Mock()
        failed_capture.isOpened.return_value = False
        working_capture = Mock()
        working_capture.isOpened.return_value = True
        cv2 = Mock()
        cv2.CAP_MSMF = 1400
        cv2.CAP_DSHOW = 700
        cv2.CAP_ANY = 0
        cv2.VideoCapture.side_effect = [failed_capture, working_capture]
        statuses = []

        with (
            patch.object(camera_module, "cv2", cv2),
            patch.object(camera_module.sys, "platform", "win32"),
        ):
            camera = Camera(camera_index=0, on_status=statuses.append)

        self.assertTrue(camera.available)
        self.assertEqual(camera.camera_index, 0)
        self.assertEqual(
            cv2.VideoCapture.call_args_list,
            [call(0, cv2.CAP_MSMF), call(0, cv2.CAP_DSHOW)],
        )
        self.assertEqual(
            statuses,
            [
                "Trying camera 0 (Media Foundation)...",
                "Trying camera 0 (DirectShow)...",
            ],
        )
        failed_capture.release.assert_called_once_with()
        camera.release()

    def test_missing_opencv_returns_clear_error(self):
        with patch.object(camera_module, "cv2", None):
            camera = Camera()

        self.assertFalse(camera.available)
        self.assertEqual(camera.error, "OpenCV is not installed.")
        camera.release()


if __name__ == "__main__":
    unittest.main()
