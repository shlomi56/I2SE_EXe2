"""F1 - Automated attendance: count faces in a class photo with MediaPipe (runs locally),
draw bounding boxes, and export a timestamped CSV."""
from __future__ import annotations

import io
import os
import tempfile
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple

import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageOps

# Used only when the installed MediaPipe no longer ships the legacy `solutions` API.
TASKS_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_detector/"
    "blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
)
MAX_SIDE_PX = 2400  # downscale huge phone photos to keep detection under ~5 s
DEFAULT_GRID = 16  # tuned on the lecture-hall photo supplied with the assignment


@dataclass
class Box:
    x: int
    y: int
    w: int
    h: int
    score: float

    @property
    def area(self) -> int:
        return max(self.w, 0) * max(self.h, 0)


def _overlap(a: Box, b: Box) -> Tuple[float, float]:
    """Return (IoU, intersection / smaller-box-area)."""
    x1, y1 = max(a.x, b.x), max(a.y, b.y)
    x2, y2 = min(a.x + a.w, b.x + b.w), min(a.y + a.h, b.y + b.h)
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    if inter == 0:
        return 0.0, 0.0
    union = a.area + b.area - inter
    return inter / union, inter / max(1, min(a.area, b.area))


def non_max_suppression(boxes: List[Box], iou_thr: float = 0.3, contain_thr: float = 0.6) -> List[Box]:
    kept: List[Box] = []
    for box in sorted(boxes, key=lambda b: b.score, reverse=True):
        if all(
            (lambda o: o[0] < iou_thr and o[1] < contain_thr)(_overlap(box, k)) for k in kept
        ):
            kept.append(box)
    return kept


class MediaPipeController:
    """Face counting with MediaPipe. Runs on the full image plus an overlapping tile grid
    so that small, distant faces at the back of a lecture hall are still detected."""

    def __init__(self, min_confidence: float = 0.5) -> None:
        self.min_confidence = min_confidence
        self._legacy = hasattr(mp, "solutions") and hasattr(mp.solutions, "face_detection")
        if self._legacy:
            # model_selection=1 -> full-range model (faces up to ~5 m away)
            self._detector = mp.solutions.face_detection.FaceDetection(
                model_selection=1, min_detection_confidence=min_confidence
            )
        else:
            from mediapipe.tasks.python import BaseOptions, vision

            options = vision.FaceDetectorOptions(
                base_options=BaseOptions(model_asset_path=_tasks_model_path()),
                min_detection_confidence=min_confidence,
            )
            self._detector = vision.FaceDetector.create_from_options(options)

    def close(self) -> None:
        self._detector.close()

    def __enter__(self) -> "MediaPipeController":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _detect(self, rgb: np.ndarray) -> List[Box]:
        h, w = rgb.shape[:2]
        rgb = np.ascontiguousarray(rgb)
        boxes: List[Box] = []
        if self._legacy:
            result = self._detector.process(rgb)
            for det in result.detections or []:
                bb = det.location_data.relative_bounding_box
                boxes.append(
                    Box(int(bb.xmin * w), int(bb.ymin * h), int(bb.width * w), int(bb.height * h), float(det.score[0]))
                )
        else:
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            for det in self._detector.detect(image).detections:
                bb = det.bounding_box
                score = det.categories[0].score if det.categories else 1.0
                boxes.append(Box(bb.origin_x, bb.origin_y, bb.width, bb.height, float(score)))
        return [b for b in boxes if b.w > 0 and b.h > 0 and b.score >= self.min_confidence]

    def count_faces(self, rgb: np.ndarray, grid: int = DEFAULT_GRID, overlap: float = 0.25) -> Tuple[int, np.ndarray]:
        h, w = rgb.shape[:2]
        boxes = self._detect(rgb)

        if grid > 1:
            tile_w, tile_h = int(w / grid * (1 + overlap)), int(h / grid * (1 + overlap))
            xs = np.linspace(0, w - tile_w, grid).astype(int)
            ys = np.linspace(0, h - tile_h, grid).astype(int)
            for y0 in ys:
                for x0 in xs:
                    tile = rgb[y0 : y0 + tile_h, x0 : x0 + tile_w]
                    for b in self._detect(tile):
                        boxes.append(Box(b.x + x0, b.y + y0, b.w, b.h, b.score))

        faces = self._drop_size_outliers(non_max_suppression(boxes))
        return len(faces), self._annotate(rgb, faces)

    @staticmethod
    def _drop_size_outliers(faces: List[Box], factor: float = 2.5) -> List[Box]:
        """Coarse passes occasionally fire on large non-face objects; in a class photo,
        real faces have similar sizes, so drop boxes far larger than the median face."""
        if len(faces) < 5:
            return faces
        median_side = float(np.median([np.sqrt(f.area) for f in faces]))
        return [f for f in faces if np.sqrt(f.area) <= factor * median_side]

    @staticmethod
    def _annotate(rgb: np.ndarray, faces: List[Box]) -> np.ndarray:
        out = rgb.copy()
        thickness = max(2, out.shape[1] // 600)
        for i, f in enumerate(faces, start=1):
            cv2.rectangle(out, (f.x, f.y), (f.x + f.w, f.y + f.h), (0, 220, 0), thickness)
            cv2.putText(
                out, str(i), (f.x, max(f.y - 4, 12)), cv2.FONT_HERSHEY_SIMPLEX,
                0.5 * thickness, (255, 255, 0), max(1, thickness - 1), cv2.LINE_AA,
            )
        return out


@st.cache_resource(show_spinner="Downloading MediaPipe face model...")
def _tasks_model_path() -> str:
    path = os.path.join(tempfile.gettempdir(), "blaze_face_short_range.tflite")
    if not os.path.isfile(path):
        urllib.request.urlretrieve(TASKS_MODEL_URL, path)
    return path


def _load_rgb(image_bytes: bytes) -> np.ndarray:
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGB")
    if max(img.size) > MAX_SIDE_PX:
        img.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX))
    return np.array(img)


def render(role: str) -> None:
    st.header("📸 Automated Attendance")
    if role != "Lecturer":
        st.info("Attendance is available to the lecturer only.")
        return

    st.session_state.setdefault("attendance_log", [])

    label = st.text_input("Course / lesson", value="Intro to SE - Lesson")
    source = st.radio("Image source", ["Camera", "Upload photo"], horizontal=True)
    if source == "Camera":
        image_file = st.camera_input("Point the camera at the class and capture")
    else:
        image_file = st.file_uploader("Upload a class photo", type=["jpg", "jpeg", "png", "webp"])

    with st.expander("Detection settings"):
        confidence = st.slider("Minimum confidence", 0.2, 0.9, 0.5, 0.05)
        grid = st.slider(
            "Tile grid (higher = finds smaller, distant faces)", 1, 20, DEFAULT_GRID,
            help="The image is split into an N×N grid of overlapping tiles so small faces at the back "
                 "of the hall are detected. Use ~4 for close-up photos.",
        )

    if image_file is None:
        return

    rgb = _load_rgb(image_file.getvalue())
    with st.spinner("Counting faces locally with MediaPipe..."):
        with MediaPipeController(min_confidence=confidence) as controller:
            count, annotated = controller.count_faces(rgb, grid=grid)

    st.metric("Students detected", count)
    st.image(annotated, caption="Detected faces (verify visually)", use_container_width=True)

    if st.button("➕ Add to attendance log", type="primary"):
        st.session_state.attendance_log.append(
            {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "course": label,
                "student_count": count,
            }
        )
        st.success(f"Logged {count} students.")

    log = st.session_state.attendance_log
    if log:
        df = pd.DataFrame(log)
        st.subheader("Attendance log")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Download CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"attendance_{datetime.now():%Y%m%d_%H%M}.csv",
            mime="text/csv",
        )
        if st.button("Clear log"):
            st.session_state.attendance_log = []
            st.rerun()
