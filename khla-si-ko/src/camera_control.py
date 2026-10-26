from __future__ import annotations

import threading
import time

from src.camera import Camera
from src.hand_tracker import HandTracker

HAND_DETECTION_FPS = 30


class CameraControl:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._frame = None
        self._point = None
        self._pinching = False
        self._hand_side = None
        self._smile_triggered = False
        self._smile_detection_enabled = True
        self._status = "Starting camera..."
        self._ready = False
        self._camera = None
        self._tracker = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            camera = Camera(
                camera_index=None,
                on_status=lambda status: self._publish(status=status),
            )
            if not camera.available:
                self._publish(status="No webcam found (indexes 0-4)", ready=True)
                camera.release()
                return

            self._publish(status="Camera found; starting hand tracking...")
            tracker = HandTracker()
            with self._lock:
                self._camera = camera
                self._tracker = tracker
                status_parts = []
                if tracker.available:
                    status_parts.append("Point and pinch to click")
                elif tracker.error:
                    status_parts.append(tracker.error)
                if tracker.face_landmarker is not None:
                    status_parts.append("Smile to start")
                elif tracker.smile_error:
                    status_parts.append("Smile detection unavailable")
                self._status = "; ".join(status_parts) or "Camera ready"
                self._ready = True

            detection_interval = 1 / HAND_DETECTION_FPS
            next_detection = 0.0
            point = None
            pinching = False
            hand_side = None
            while not self._stop_event.is_set():
                frame = camera.read_frame()
                if frame is None:
                    self._publish(status="Webcam opened; waiting for video", ready=True)
                    point = None
                    pinching = False
                    time.sleep(0.02)
                    continue

                now = time.monotonic()
                if (tracker.available or tracker.face_landmarker is not None) and now >= next_detection:
                    detected = tracker.detect(frame)
                    point, pinching, hand_side = detected if detected is not None else (None, False, None)
                    with self._lock:
                        smile_detection_enabled = self._smile_detection_enabled
                    if (
                        smile_detection_enabled
                        and tracker.face_landmarker is not None
                        and tracker.detect_smile(frame)
                    ):
                        with self._lock:
                            self._smile_triggered = True
                    next_detection = now + detection_interval
                self._publish(
                    frame=frame,
                    point=point,
                    pinching=pinching,
                    hand_side=hand_side,
                    ready=True,
                )
        except Exception as exc:
            self._publish(status=f"Camera error: {exc}", ready=True)
        finally:
            if self._tracker is not None:
                self._tracker.close()
                self._tracker = None
            if self._camera is not None:
                self._camera.release()
                self._camera = None

    def _publish(
        self,
        frame=None,
        point=None,
        pinching=False,
        hand_side=None,
        status=None,
        ready=None,
    ) -> None:
        with self._lock:
            if frame is not None:
                self._frame = frame
            self._point = point
            self._pinching = pinching
            self._hand_side = hand_side
            if status is not None:
                self._status = status
            if ready is not None:
                self._ready = ready

    def get_state(self):
        with self._lock:
            return self._frame, self._point, self._pinching, self._status, self._ready

    def get_hand_side(self) -> str | None:
        with self._lock:
            return self._hand_side

    def consume_smile_trigger(self) -> bool:
        with self._lock:
            triggered = self._smile_triggered
            self._smile_triggered = False
            return triggered

    def set_smile_detection_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._smile_detection_enabled = enabled
            if not enabled:
                self._smile_triggered = False

    def close(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=3)
