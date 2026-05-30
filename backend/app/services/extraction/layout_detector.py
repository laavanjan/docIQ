"""YOLOv8 document-layout detection (ultralytics).

Detects regions (text / table / figure / title …) on a rendered page image and returns
them ordered roughly in human reading order (top-to-bottom, then left-to-right). The OCR
extractor uses these regions to OCR each block separately, which preserves structure far
better than running Tesseract blindly over a whole page — mirroring the YOLO "layout
analysis" stage of the original project.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Region:
    bbox: tuple[float, float, float, float]  # x0, y0, x1, y1
    label: str
    confidence: float


class LayoutDetector:
    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path or settings.yolo_model_path
        self._model = None

    def _load(self):
        if self._model is None:
            from ultralytics import YOLO  # heavy import (pulls torch) — load lazily

            logger.info("loading YOLO layout model: %s", self.model_path)
            self._model = YOLO(self.model_path)
        return self._model

    def detect(self, image) -> list[Region]:
        """Return detected regions for a PIL image, in reading order."""
        model = self._load()
        results = model(image, verbose=False)
        regions: list[Region] = []
        names = getattr(model, "names", {})
        for res in results:
            boxes = getattr(res, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
                x0, y0, x1, y1 = (float(v) for v in box.xyxy[0].tolist())
                cls = int(box.cls[0])
                regions.append(
                    Region(
                        bbox=(x0, y0, x1, y1),
                        label=str(names.get(cls, cls)),
                        confidence=float(box.conf[0]),
                    )
                )
        # Reading order: bucket y into coarse rows so side-by-side blocks stay aligned.
        regions.sort(key=lambda r: (round(r.bbox[1] / 20.0), r.bbox[0]))
        return regions


@lru_cache
def get_layout_detector() -> LayoutDetector:
    return LayoutDetector()
