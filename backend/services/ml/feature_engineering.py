"""
Feature Engineering para o pipeline de ML.

Responsabilidades:
  1. Buscar registros de balanço e clima no banco
  2. Construir FeatureVectors com features temporais derivadas
  3. Preparar DataFrame para treinamento ou predição
  4. Normalização e imputação de ausentes
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import numpy as np
import pandas as pd
import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.ml_model import FEATURE_NAMES, FeatureVector, PredictionTarget
from backend.models.climate_record import ClimateRecord
from backend.models.transformer_balance import TransformerBalance

logger = structlog.get_logger(__name__)


class FeatureEngineer:
    """
    Constrói e transforma features para o pipeline ML.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ─────────────────────────────────────────────────────────────────────────
    # Construção do dataset completo
    # ─────────────────────────────────────────────────────────────────────────

    async def build_training_dataset(
        self,
        transformer_ids: Optional[list[str]] = None,
        date_start: Optional[date] = None,
        date_end: Optional[date] = None,
        target: PredictionTarget = PredictionTarget.ENERGY_LOSS_PCT,
    ) -> pd.DataFrame:
        """
        Constrói DataFrame de treinamento com features + target.
        Faz o join entre balanços e dados climáticos.
        """
        log = logger.bind(target=target.value)

        balances = await self._fetch_balances(transformer_ids, date_start, date_end)
        if not balances:
            log.warning("feature_eng.no_balances_found")
            return pd.DataFrame()

        log.info("feature_eng.balances_loaded", count=len(balances))

        rows: list[dict] = []
        for balance in balances:
            ref_date = balance.ref_date if isinstance(balance.ref_date, date) else \
                balance.ref_date.date()

            climate = await self._fetch_climate(balance.latitude, balance.longitude, ref_date)

            fv = self._build_feature_vector(balance, climate, ref_date)
            row = self._feature_vector_to_dict(fv, balance, target)
            rows.append(row)

        df = pd.DataFrame(rows)
        df = self._impute_and_clean(df)

        log.info("feature_eng.dataset_built", shape=str(df.shape))
        return df

    async def build_prediction_vector(
        self,
        transformer_id: str,
        ref_date: date,
        balance: TransformerBalance,
        climate: Optional[ClimateRecord],
    ) -> Optional[list[float]]:
        """
        Constrói vetor de features para predição em tempo real.
        Retorna None se dados insuficientes.
        """
        if balance is None:
            return None

        fv = self._build_feature_vector(balance, climate, ref_date)
        arr = self._feature_vector_to_array(fv)

        if any(np.isnan(v) for v in arr):
            logger.warning(
                "feature_eng.nan_in_vector",
                transformer_id=transformer_id,
                ref_date=str(ref_date),
            )
            arr = [0.0 if np.isnan(v) else v for v in arr]

        return arr

    # ─────────────────────────────────────────────────────────────────────────
    # Queries ao banco
    # ─────────────────────────────────────────────────────────────────────────

    async def _fetch_balances(
        self,
        transformer_ids: Optional[list[str]],
        date_start: Optional[date],
        date_end: Optional[date],
    ) -> list[TransformerBalance]:
        filters = []
        if transformer_ids:
            filters.append(TransformerBalance.transformer_id.in_(transformer_ids))
        if date_start:
            filters.append(TransformerBalance.ref_date >= date_start)
        if date_end:
            filters.append(TransformerBalance.ref_date <= date_end)
        # Apenas balances com dados suficientes
        filters.append(TransformerBalance.measured_energy_kwh > 0)

        stmt = select(TransformerBalance)
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.order_by(
            TransformerBalance.transformer_id,
            TransformerBalance.ref_date,
        )

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def _fetch_climate(
        self,
        latitude: float,
        longitude: float,
        ref_date: date,
    ) -> Optional[ClimateRecord]:
        return await self._session.scalar(
            select(ClimateRecord).where(
                and_(
                    ClimateRecord.latitude == round(latitude, 4),
                    ClimateRecord.longitude == round(longitude, 4),
                    ClimateRecord.ref_date == ref_date,
                )
            )
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Construção do FeatureVector
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_feature_vector(
        balance: TransformerBalance,
        climate: Optional[ClimateRecord],
        ref_date: date,
    ) -> FeatureVector:
        dt = datetime.combine(ref_date, datetime.min.time())

        # Defaults climáticos caso não haja dados
        irr_factor = float(getattr(climate, "irradiance_factor", 1.0) or 1.0)
        temp_factor = float(getattr(climate, "temperature_factor", 1.0) or 1.0)
        cloud_factor = float(getattr(climate, "cloud_factor", 1.0) or 1.0)
        composite = float(getattr(climate, "composite_factor", 1.0) or 1.0)
        irr_daily = float(getattr(climate, "irradiance_daily_kwh_m2", 0.0) or 0.0)
        temp_avg = float(getattr(climate, "temperature_avg_c", 25.0) or 25.0)
        cloud_avg = float(getattr(climate, "cloud_cover_avg_pct", 0.0) or 0.0)

        return FeatureVector(
            transformer_id=balance.transformer_id,
            ref_date=str(ref_date),
            measured_energy_kwh=float(balance.measured_energy_kwh or 0.0),
            total_consumption_kwh=float(balance.total_consumption_kwh or 0.0),
            total_generation_kwh=float(balance.total_generation_kwh or 0.0),
            total_injection_kwh=float(balance.total_injection_kwh or 0.0),
            residual_kwh=float(balance.residual_kwh or 0.0),
            error_pct=float(balance.error_pct or 0.0),
            num_consumer_units=int(balance.num_consumer_units or 0),
            avg_confidence_inference=float(balance.confidence or 0.8),
            irradiance_factor=irr_factor,
            temperature_factor=temp_factor,
            cloud_factor=cloud_factor,
            composite_climate_factor=composite,
            irradiance_daily_kwh_m2=irr_daily,
            temperature_avg_c=temp_avg,
            cloud_cover_avg_pct=cloud_avg,
            month=dt.month,
            day_of_week=dt.weekday(),
            is_weekend=dt.weekday() >= 5,
            quarter=((dt.month - 1) // 3) + 1,
        )

    @staticmethod
    def _feature_vector_to_dict(
        fv: FeatureVector,
        balance: TransformerBalance,
        target: PredictionTarget,
    ) -> dict:
        from backend.domain.ml_model import extract_feature_array

        arr = extract_feature_array(fv)
        row = dict(zip(FEATURE_NAMES, arr))
        row["transformer_id"] = fv.transformer_id
        row["ref_date"] = fv.ref_date

        # Label: definida a partir dos dados reais de balanço
        if target == PredictionTarget.ENERGY_LOSS_PCT:
            measured = float(balance.measured_energy_kwh or 1.0)
            consumption = float(balance.total_consumption_kwh or 0.0)
            row["target"] = round(
                max(0.0, (measured - consumption) / max(measured, 1.0) * 100.0), 4
            )
        elif target == PredictionTarget.ADJUSTED_BALANCE:
            row["target"] = float(balance.residual_kwh or 0.0)
        elif target == PredictionTarget.FRAUD_SCORE:
            # Heurística baseada no erro percentual
            error = abs(float(balance.error_pct or 0.0))
            row["target"] = min(error / 100.0, 1.0)

        return row

    @staticmethod
    def _feature_vector_to_array(fv: FeatureVector) -> list[float]:
        from backend.domain.ml_model import extract_feature_array
        return extract_feature_array(fv)

    # ─────────────────────────────────────────────────────────────────────────
    # Limpeza e imputação
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _impute_and_clean(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df

        feature_cols = [c for c in FEATURE_NAMES if c in df.columns]
        df[feature_cols] = df[feature_cols].fillna(df[feature_cols].median())
        df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["target"])
        df = df.reset_index(drop=True)
        return df
