from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from urllib.request import urlopen

try:
    import cv2
except ImportError: 
    cv2 = None

try:
    import mediapipe as mp
except ImportError: 
    mp = None

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
FACE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
SMILE_START_THRESHOLD = 0.55
SMILE_RELEASE_THRESHOLD = 0.4
SMILE_HOLD_SECONDS = 0.8


class HandTracker:
    def __init__(self) -> None:
        self.landmarker = None
        self.face_landmarker = None
        self.error = None
        self.smile_error = None
        self._pinching = False
        self._smile_started_at = None
        self._smiling = False
        self.smile_triggered = False
        if cv2 is None or mp is None:
            self.error = "Install camera dependencies with pip install -r requirements.txt."
            self.smile_error = self.error
            return

        try:
            model_path = self._model_path()
            options = mp.tasks.vision.HandLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
                running_mode=mp.tasks.vision.RunningMode.IMAGE,
                num_hands=1,
                min_hand_detection_confidence=0.6,
                min_tracking_confidence=0.5,
            )
            self.landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)
        except (OSError, RuntimeError, ValueError) as exc:
            self.error = f"Could not start hand tracking: {exc}"

        try:
            face_model_path = self._face_model_path()
            face_options = mp.tasks.vision.FaceLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(face_model_path)),
                running_mode=mp.tasks.vision.RunningMode.IMAGE,
                num_faces=1,
                output_face_blendshapes=True,
            )
            self.face_landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(face_options)
        except (OSError, RuntimeError, ValueError) as exc:
            self.smile_error = f"Could not start smile detection: {exc}"

    @staticmethod
    def _model_path() -> Path:
        app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        model_path = app_data / "KlaSiKo" / "hand_landmarker.task"
        if model_path.is_file() and model_path.stat().st_size:
            return model_path
        return HandTracker._download_model(model_path, MODEL_URL, "hand")

    @staticmethod
    def _face_model_path() -> Path:
        app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        model_path = app_data / "KlaSiKo" / "face_landmarker.task"
        if model_path.is_file() and model_path.stat().st_size:
            return model_path
        return HandTracker._download_model(model_path, FACE_MODEL_URL, "face")

    @staticmethod
    def _download_model(model_path: Path, model_url: str, model_name: str) -> Path:
        model_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = model_path.with_suffix(".task.download")
        try:
            with urlopen(model_url, timeout=30) as response, temporary_path.open("wb") as output:
                shutil.copyfileobj(response, output)
            if not temporary_path.stat().st_size:
                raise RuntimeError(f"Downloaded {model_name} tracking model is empty.")
            temporary_path.replace(model_path)
        except OSError as exc:
            raise RuntimeError(f"Could not download the {model_name} tracking model; check internet access.") from exc
        finally:
            temporary_path.unlink(missing_ok=True)
        return model_path

    @property
    def available(self) -> bool:
        return self.landmarker is not None

    def detect(self, frame):
        if self.landmarker is None or frame is None:
            return None

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect(image)
        if not result.hand_landmarks:
            self._pinching = False
            return None

        handedness = result.handedness[0][0].category_name
      
        hand_side = {"Left": "Right", "Right": "Left"}.get(handedness)
        landmarks = result.hand_landmarks[0]
        tip = landmarks[8]
        thumb = landmarks[4]
        pinch_distance = ((tip.x - thumb.x) ** 2 + (tip.y - thumb.y) ** 2) ** 0.5
        if self._pinching:
            self._pinching = pinch_distance < 0.075
        else:
            self._pinching = pinch_distance < 0.05
        return (tip.x, tip.y), self._pinching, hand_side

    @staticmethod
    def _smile_score(blendshapes) -> float:
        scores = {
            category.category_name: category.score
            for category in blendshapes
        }
        left = scores.get("mouthSmileLeft", 0.0)
        right = scores.get("mouthSmileRight", 0.0)
        return min(left, right)

    def _update_smile(self, score: float, now: float) -> bool:
        self.smile_triggered = False
        if score < SMILE_RELEASE_THRESHOLD:
            self._smile_started_at = None
            self._smiling = False
            return False

        if score < SMILE_START_THRESHOLD:
            return False

        if self._smile_started_at is None:
            self._smile_started_at = now
        elif not self._smiling and now - self._smile_started_at >= SMILE_HOLD_SECONDS:
            self._smiling = True
            self.smile_triggered = True
        return self.smile_triggered

    def detect_smile(self, frame, now: float | None = None) -> bool:
        self.smile_triggered = False
        if self.face_landmarker is None or frame is None:
            return False

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.face_landmarker.detect(image)
        if not result.face_blendshapes:
            self._update_smile(0.0, time.monotonic() if now is None else now)
            return False

        score = self._smile_score(result.face_blendshapes[0])
        return self._update_smile(score, time.monotonic() if now is None else now)

    def close(self) -> None:
        if self.landmarker is not None:
            self.landmarker.close()
            self.landmarker = None
        if self.face_landmarker is not None:
            self.face_landmarker.close()
            self.face_landmarker = None
