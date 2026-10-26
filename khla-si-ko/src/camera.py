from __future__ import annotations

import sys
from collections.abc import Callable

try:
    import cv2
except ImportError:  
    cv2 = None


class Camera:
    def __init__(
        self,
        camera_index: int | None = 0,
        on_status: Callable[[str], None] | None = None,
    ) -> None:
        self.capture = None
        self.available = False
        self.camera_index = None
        self.error = None

        if cv2 is None:
            self.error = "OpenCV is not installed."
            return

        camera_indices = [camera_index] if camera_index is not None else range(5)
        backends = [cv2.CAP_ANY]
        if sys.platform == "win32":
            backends = [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY]

        for index in camera_indices:
            for backend in backends:
                if on_status is not None:
                    backend_name = {
                        cv2.CAP_MSMF: "Media Foundation",
                        cv2.CAP_DSHOW: "DirectShow",
                        cv2.CAP_ANY: "automatic backend",
                    }.get(backend, "camera backend")
                    on_status(f"Trying camera {index} ({backend_name})...")
                capture = cv2.VideoCapture(index, backend)
                if capture is not None and capture.isOpened():
                    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    self.capture = capture
                    self.camera_index = index
                    self.available = True
                    return
                if capture is not None:
                    capture.release()

        self.error = "No camera could be opened at indexes 0-4."

    def read_frame(self):
        if self.capture is None or not self.available:
            return None
        ok, frame = self.capture.read()
        if not ok:
            return None
        return frame

    def release(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        self.available = False
