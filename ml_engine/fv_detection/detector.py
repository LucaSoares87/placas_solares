import structlog
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = structlog.get_logger(__name__)

ALLOWED_CLASSES = {"painel_solar"}
REJECTED_CLASSES = {"telhado", "sombra", "vegetacao", "caixa_dagua", "estrutura_metalica"}


@dataclass
class DetectionResult:
    has_fv: bool
    confidence: float
    detections: list[dict] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)
    model_version: str = "unknown"
    raw_output: Optional[object] = field(default=None, repr=False)


class FVDetector:
    """
    Realiza detecção de painéis fotovoltaicos em imagens aéreas
    utilizando YOLO Ultralytics com suporte a segmentação de instâncias.
    """

    def __init__(self, model_path: str, confidence_threshold: float = 0.45):
        self._model_path = Path(model_path)
        self._confidence_threshold = confidence_threshold
        self._model = None
        self._model_version = self._resolve_version()

    def _resolve_version(self) -> str:
        return self._model_path.stem if self._model_path.exists() else "not_loaded"

    def _load_model(self):
        if self._model is not None:
            return

        try:
            from ultralytics import YOLO
            self._model = YOLO(str(self._model_path))
            self._model_version = self._model_path.stem
            logger.info("fv_detector.model_loaded", path=str(self._model_path))
        except Exception as exc:
            logger.error("fv_detector.load_failed", error=str(exc))
            raise RuntimeError(f"Falha ao carregar modelo YOLO: {exc}") from exc

    def detect(self, image: np.ndarray) -> DetectionResult:
        self._load_model()

        try:
            results = self._model.predict(
                source=image,
                conf=self._confidence_threshold,
                verbose=False,
            )
            return self._parse_results(results)
        except Exception as exc:
            logger.error("fv_detector.predict_failed", error=str(exc))
            raise RuntimeError(f"Falha na inferência YOLO: {exc}") from exc

    def _parse_results(self, results) -> DetectionResult:
        accepted = []
        rejected = []

        for result in results:
            names = result.names
            boxes = result.boxes

            if boxes is None:
                continue

            for i, box in enumerate(boxes):
                class_id = int(box.cls[0])
                class_name = names.get(class_id, "unknown")
                confidence = float(box.conf[0])

                detection = {
                    "class": class_name,
                    "confidence": round(confidence, 4),
                    "bbox_xyxy": box.xyxy[0].tolist(),
                    "mask_polygon": self._extract_mask(result, i),
                }

                if class_name in ALLOWED_CLASSES:
                    accepted.append(detection)
                else:
                    rejected.append(detection)

        has_fv = len(accepted) > 0
        confidence = self._aggregate_confidence(accepted)

        logger.info(
            "fv_detector.result",
            has_fv=has_fv,
            accepted=len(accepted),
            rejected=len(rejected),
            confidence=confidence,
        )

        return DetectionResult(
            has_fv=has_fv,
            confidence=confidence,
            detections=accepted,
            rejected=rejected,
            model_version=self._model_version,
        )

    def _extract_mask(self, result, index: int) -> list[list[float]]:
        try:
            if result.masks is not None:
                mask_xy = result.masks.xy[index]
                return mask_xy.tolist()
        except (IndexError, AttributeError):
            pass
        return []

    def _aggregate_confidence(self, detections: list[dict]) -> float:
        if not detections:
            return 0.0
        confidences = [d["confidence"] for d in detections]
        return round(float(np.mean(confidences)), 4)
