import structlog
from dataclasses import dataclass
from typing import Optional

logger = structlog.get_logger(__name__)


@dataclass
class GeoReferenceParams:
    """
    Parâmetros de georreferenciamento para conversão pixel → m².

    gsd_m_per_pixel: Ground Sample Distance em metros/pixel.
    altitude_m: altitude de voo em metros (usado para calcular GSD se não fornecido).
    focal_length_mm: distância focal da câmera em milímetros.
    sensor_width_mm: largura do sensor em milímetros.
    image_width_px: largura da imagem em pixels.
    perspective_correction: fator multiplicativo de correção de perspectiva (0.85–1.0).
    distortion_correction: fator multiplicativo de correção de distorção (0.90–1.0).
    """

    gsd_m_per_pixel: Optional[float] = None
    altitude_m: Optional[float] = None
    focal_length_mm: Optional[float] = None
    sensor_width_mm: Optional[float] = None
    image_width_px: Optional[int] = None
    perspective_correction: float = 1.0
    distortion_correction: float = 1.0


class PixelToAreaConverter:
    """
    Converte área em pixels para área real em m² aplicando:
    - GSD (Ground Sample Distance)
    - Correção de perspectiva
    - Correção de distorção
    """

    DEFAULT_GSD = 0.10  # 10 cm/pixel — resolução padrão para drones urbanos

    def __init__(self, params: GeoReferenceParams):
        self._params = params
        self._gsd = self._resolve_gsd()

    def _resolve_gsd(self) -> float:
        if self._params.gsd_m_per_pixel is not None:
            gsd = self._params.gsd_m_per_pixel
            logger.info("pixel_to_area.gsd_direct", gsd=gsd)
            return gsd

        if (
            self._params.altitude_m is not None
            and self._params.focal_length_mm is not None
            and self._params.sensor_width_mm is not None
            and self._params.image_width_px is not None
        ):
            gsd = self._calculate_gsd_from_camera()
            logger.info("pixel_to_area.gsd_calculated", gsd=gsd)
            return gsd

        logger.warning(
            "pixel_to_area.gsd_fallback",
            default=self.DEFAULT_GSD,
        )
        return self.DEFAULT_GSD

    def _calculate_gsd_from_camera(self) -> float:
        """
        GSD = (altitude_m * sensor_width_mm) / (focal_length_mm * image_width_px)
        Resultado em metros/pixel.
        """
        gsd = (
            self._params.altitude_m
            * self._params.sensor_width_mm
        ) / (
            self._params.focal_length_mm
            * self._params.image_width_px
        )
        return round(gsd, 6)

    def convert(self, area_pixels: float) -> float:
        """
        Converte área em pixels para m² com correções aplicadas.

        area_m2 = area_pixels * gsd² * perspective_correction * distortion_correction
        """
        if area_pixels <= 0:
            return 0.0

        area_m2 = (
            area_pixels
            * (self._gsd ** 2)
            * self._params.perspective_correction
            * self._params.distortion_correction
        )

        result = round(area_m2, 4)

        logger.debug(
            "pixel_to_area.converted",
            area_pixels=area_pixels,
            gsd=self._gsd,
            area_m2=result,
        )

        return result

    def convert_batch(self, areas_pixels: list[float]) -> list[float]:
        return [self.convert(a) for a in areas_pixels]

    @property
    def gsd(self) -> float:
        return self._gsd
