import structlog
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

logger = structlog.get_logger(__name__)


@dataclass
class TileConfig:
    tile_size: int = 640
    overlap: int = 64
    min_content_ratio: float = 0.05
    output_format: str = "jpg"
    quality: int = 95


@dataclass
class TileResult:
    tile_path: str
    row: int
    col: int
    x_offset: int
    y_offset: int
    width: int
    height: int


class TileGenerator:
    """
    Divide imagens aéreas de alta resolução em tiles menores
    compatíveis com entrada YOLO (padrão 640x640).

    Suporta overlap para evitar detecções perdidas nas bordas.
    """

    def __init__(self, config: Optional[TileConfig] = None):
        self._config = config or TileConfig()

    def generate(self, image_path: str, output_dir: str) -> list[TileResult]:
        try:
            import cv2
        except ImportError as exc:
            raise ImportError("opencv-python é necessário para TileGenerator") from exc

        img_path = Path(image_path)
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        image = cv2.imread(str(img_path))
        if image is None:
            raise ValueError(f"Imagem não encontrada ou inválida: {img_path}")

        height, width = image.shape[:2]
        tiles = self._slice_image(image, img_path.stem, out_path, width, height)

        logger.info(
            "tile_generator.done",
            source=str(img_path),
            total_tiles=len(tiles),
            tile_size=self._config.tile_size,
        )

        return tiles

    def _slice_image(
        self,
        image: np.ndarray,
        stem: str,
        out_path: Path,
        img_width: int,
        img_height: int,
    ) -> list[TileResult]:
        import cv2

        step = self._config.tile_size - self._config.overlap
        results: list[TileResult] = []
        row = 0

        y = 0
        while y < img_height:
            x = 0
            col = 0
            while x < img_width:
                x_end = min(x + self._config.tile_size, img_width)
                y_end = min(y + self._config.tile_size, img_height)

                tile = image[y:y_end, x:x_end]

                if not self._has_content(tile):
                    x += step
                    col += 1
                    continue

                tile_name = f"{stem}_r{row:03d}_c{col:03d}.{self._config.output_format}"
                tile_path = out_path / tile_name

                cv2.imwrite(
                    str(tile_path),
                    tile,
                    [cv2.IMWRITE_JPEG_QUALITY, self._config.quality],
                )

                results.append(
                    TileResult(
                        tile_path=str(tile_path),
                        row=row,
                        col=col,
                        x_offset=x,
                        y_offset=y,
                        width=x_end - x,
                        height=y_end - y,
                    )
                )

                x += step
                col += 1
            y += step
            row += 1

        return results

    def _has_content(self, tile: np.ndarray) -> bool:
        if tile.size == 0:
            return False
        total_pixels = tile.shape[0] * tile.shape[1]
        non_black = np.count_nonzero(tile.sum(axis=2))
        return (non_black / total_pixels) >= self._config.min_content_ratio
