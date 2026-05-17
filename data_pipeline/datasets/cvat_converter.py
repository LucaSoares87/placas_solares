import structlog
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import shutil

logger = structlog.get_logger(__name__)


@dataclass
class CVATLabel:
    image_name: str
    image_width: int
    image_height: int
    polygons: list[list[tuple[float, float]]] = field(default_factory=list)
    class_name: str = "painel_solar"
    class_id: int = 0


@dataclass
class ConversionResult:
    total_images: int
    total_labels: int
    skipped: int
    output_dir: str


class CVATConverter:
    """
    Converte anotações exportadas do CVAT (formato XML/Segmentation)
    para o formato YOLO Segmentation (.txt por imagem).

    Formato YOLO Segmentation por linha:
        <class_id> <x1_norm> <y1_norm> <x2_norm> <y2_norm> ...
    """

    SUPPORTED_LABEL_CLASS = "painel_solar"

    def __init__(self, class_map: Optional[dict[str, int]] = None):
        self._class_map = class_map or {self.SUPPORTED_LABEL_CLASS: 0}

    def convert(
        self,
        cvat_xml_path: str,
        output_dir: str,
        images_dir: Optional[str] = None,
        split_ratio: tuple[float, float, float] = (0.7, 0.2, 0.1),
    ) -> ConversionResult:
        xml_path = Path(cvat_xml_path)
        out_path = Path(output_dir)

        if not xml_path.exists():
            raise FileNotFoundError(f"Arquivo CVAT não encontrado: {xml_path}")

        labels = self._parse_xml(xml_path)
        self._write_yolo_labels(labels, out_path)

        if images_dir:
            self._organize_dataset(labels, Path(images_dir), out_path, split_ratio)

        result = ConversionResult(
            total_images=len(labels),
            total_labels=sum(len(l.polygons) for l in labels),
            skipped=0,
            output_dir=str(out_path),
        )

        logger.info(
            "cvat_converter.done",
            total_images=result.total_images,
            total_labels=result.total_labels,
        )

        return result

    def _parse_xml(self, xml_path: Path) -> list[CVATLabel]:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        labels: list[CVATLabel] = []

        for image_elem in root.findall("image"):
            name = image_elem.get("name", "unknown")
            width = int(image_elem.get("width", 1))
            height = int(image_elem.get("height", 1))

            polygons: list[list[tuple[float, float]]] = []

            for polygon_elem in image_elem.findall("polygon"):
                label = polygon_elem.get("label", "")
                if label not in self._class_map:
                    continue

                points_str = polygon_elem.get("points", "")
                coords = self._parse_points(points_str, width, height)

                if len(coords) >= 3:
                    polygons.append(coords)

            if polygons:
                labels.append(
                    CVATLabel(
                        image_name=name,
                        image_width=width,
                        image_height=height,
                        polygons=polygons,
                        class_name=self.SUPPORTED_LABEL_CLASS,
                        class_id=self._class_map.get(self.SUPPORTED_LABEL_CLASS, 0),
                    )
                )

        logger.info("cvat_converter.parsed", total=len(labels))
        return labels

    def _parse_points(
        self, points_str: str, width: int, height: int
    ) -> list[tuple[float, float]]:
        coords = []
        try:
            for pair in points_str.split(";"):
                x_str, y_str = pair.strip().split(",")
                x_norm = float(x_str) / width
                y_norm = float(y_str) / height
                x_norm = max(0.0, min(x_norm, 1.0))
                y_norm = max(0.0, min(y_norm, 1.0))
                coords.append((x_norm, y_norm))
        except Exception as exc:
            logger.warning("cvat_converter.parse_points_error", error=str(exc))
        return coords

    def _write_yolo_labels(self, labels: list[CVATLabel], out_path: Path) -> None:
        labels_dir = out_path / "labels"
        labels_dir.mkdir(parents=True, exist_ok=True)

        for label in labels:
            stem = Path(label.image_name).stem
            label_file = labels_dir / f"{stem}.txt"

            lines = []
            for polygon in label.polygons:
                coords_flat = " ".join(
                    f"{x:.6f} {y:.6f}" for x, y in polygon
                )
                lines.append(f"{label.class_id} {coords_flat}")

            label_file.write_text("\n".join(lines), encoding="utf-8")

    def _organize_dataset(
        self,
        labels: list[CVATLabel],
        images_dir: Path,
        out_path: Path,
        split_ratio: tuple[float, float, float],
    ) -> None:
        import random

        random.shuffle(labels)
        n = len(labels)
        n_train = int(n * split_ratio[0])
        n_val = int(n * split_ratio[1])

        splits = {
            "train": labels[:n_train],
            "val": labels[n_train: n_train + n_val],
            "test": labels[n_train + n_val:],
        }

        for split_name, split_labels in splits.items():
            img_out = out_path / "images" / split_name
            lbl_out = out_path / "labels" / split_name
            img_out.mkdir(parents=True, exist_ok=True)
            lbl_out.mkdir(parents=True, exist_ok=True)

            for label in split_labels:
                src_img = images_dir / label.image_name
                if src_img.exists():
                    shutil.copy2(src_img, img_out / label.image_name)

                stem = Path(label.image_name).stem
                src_lbl = out_path / "labels" / f"{stem}.txt"
                if src_lbl.exists():
                    shutil.copy2(src_lbl, lbl_out / f"{stem}.txt")

        self._write_yaml(out_path)

    def _write_yaml(self, out_path: Path) -> None:
        yaml_content = (
            f"path: {out_path.resolve()}\n"
            "train: images/train\n"
            "val: images/val\n"
            "test: images/test\n\n"
            f"nc: {len(self._class_map)}\n"
            f"names: {list(self._class_map.keys())}\n"
        )
        (out_path / "dataset.yaml").write_text(yaml_content, encoding="utf-8")
        logger.info("cvat_converter.yaml_written", path=str(out_path / "dataset.yaml"))
