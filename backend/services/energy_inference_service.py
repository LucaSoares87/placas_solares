import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import ConflictException, EntityNotFoundException
from backend.domain.constants import (
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    INJECTION_RATIO_MAX,
    INJECTION_RATIO_MIN,
    PERFORMANCE_RATIO_DEFAULT,
    PROFILE_CONSUMPTION_KW,
    TECHNICAL_LOSS_FACTOR,
)
from backend.domain.entities import (
    BalanceStatus,
    EnergyStatus,
    InferenceMethod,
    RiskScore,
)
from backend.models.energy_inference import EnergyInference
from backend.models.transformer_balance import TransformerBalance
from backend.repositories.consumer_unit_repository import ConsumerUnitRepository
from backend.repositories.energy_inference_repository import EnergyInferenceRepository
from backend.repositories.transformer_balance_repository import TransformerBalanceRepository
from backend.repositories.transformer_repository import TransformerRepository
from backend.schemas.energy_inference import EnergyInferenceCreate, EnergyInferenceUpdate
from backend.schemas.transformer_balance import TransformerBalanceCreate

logger = structlog.get_logger(__name__)


class EnergyInferenceService:
    def __init__(self, session: AsyncSession) -> None:
        self._inf_repo = EnergyInferenceRepository(session)
        self._bal_repo = TransformerBalanceRepository(session)
        self._uc_repo = ConsumerUnitRepository(session)
        self._tr_repo = TransformerRepository(session)

    async def register_inference(
        self, data: EnergyInferenceCreate
    ) -> EnergyInference:
        exists = await self._uc_repo.exists_by_uc_code(data.uc_code)
        if not exists:
            raise EntityNotFoundException(
                message=f"UC {data.uc_code} não encontrada.",
                details={"uc_code": data.uc_code},
            )

        inference = EnergyInference(**data.model_dump())
        saved = await self._inf_repo.save(inference)
        logger.info(
            "energy_inference.registered",
            uc_code=data.uc_code,
            status=data.status.value,
            confidence=data.confidence,
        )
        return saved

    async def get_latest_inference(self, uc_code: str) -> EnergyInference:
        inference = await self._inf_repo.get_latest_by_uc(uc_code)
        if not inference:
            raise EntityNotFoundException(
                message=f"Nenhuma inferência encontrada para UC {uc_code}.",
                details={"uc_code": uc_code},
            )
        return inference

    async def update_inference(
        self, inference_id: int, data: EnergyInferenceUpdate
    ) -> EnergyInference:
        inference = await self._inf_repo.get_by_id(inference_id)
        if not inference:
            raise EntityNotFoundException(
                message=f"Inferência {inference_id} não encontrada.",
                details={"id": inference_id},
            )

        for field, value in data.model_dump(exclude_none=True).items():
            if hasattr(value, "value"):
                value = value.value
            setattr(inference, field, value)

        saved = await self._inf_repo.save(inference)
        logger.info("energy_inference.updated", inference_id=inference_id)
        return saved

    async def list_by_transformer(
        self, transformer_id: str, offset: int = 0, limit: int = 100
    ) -> list[EnergyInference]:
        return await self._inf_repo.list_by_transformer(transformer_id, offset, limit)

    async def infer_from_profile(self, uc_code: str) -> EnergyInference:
        uc = await self._uc_repo.get_by_uc_code(uc_code)
        if not uc:
            raise EntityNotFoundException(
                message=f"UC {uc_code} não encontrada.",
                details={"uc_code": uc_code},
            )

        profile_key = uc.profile if uc.profile in PROFILE_CONSUMPTION_KW else "residential"
        base_consumption = PROFILE_CONSUMPTION_KW[profile_key]

        has_fv = uc.has_gd
        kwp = uc.gd_installed_kwp or 0.0
        generation_kw: float | None = None
        injection_min: float | None = None
        injection_max: float | None = None
        status = EnergyStatus.NORMAL
        confidence = CONFIDENCE_MEDIUM

        if has_fv and kwp > 0:
            from backend.domain.constants import IRRADIANCE_NORDESTE_AVG

            generation_kw = round(
                kwp * IRRADIANCE_NORDESTE_AVG * PERFORMANCE_RATIO_DEFAULT / 24, 4
            )
            injection_min = round(generation_kw * INJECTION_RATIO_MIN, 4)
            injection_max = round(generation_kw * INJECTION_RATIO_MAX, 4)
            status = EnergyStatus.GENERATION_DETECTED
            confidence = CONFIDENCE_HIGH

        risk = self._classify_risk(confidence)

        data = EnergyInferenceCreate(
            uc_code=uc_code,
            transformer_id=uc.transformer_id,
            has_fv=has_fv,
            kwp_estimated=kwp if has_fv else None,
            generation_kw=generation_kw,
            consumption_estimated_kw=base_consumption,
            injection_kw_min=injection_min,
            injection_kw_max=injection_max,
            status=status,
            confidence=confidence,
            operational_score=risk,
            inference_method=InferenceMethod.STATISTICAL,
        )

        return await self.register_inference(data)

    async def compute_transformer_balance(
        self,
        transformer_id: str,
        measured_kwh: float,
        period_start,
        period_end,
    ) -> TransformerBalance:
        transformer = await self._tr_repo.get_by_transformer_id(transformer_id)
        if not transformer:
            raise EntityNotFoundException(
                message=f"Transformador {transformer_id} não encontrado.",
                details={"transformer_id": transformer_id},
            )

        uc_list = await self._uc_repo.list_by_transformer(transformer_id)
        uc_count = len(uc_list)
        telemetered = sum(1 for uc in uc_list if uc.is_telemetered)
        gd_count = sum(1 for uc in uc_list if uc.has_gd)

        total_consumption = 0.0
        total_generation = 0.0
        total_injection = 0.0

        for uc in uc_list:
            inf = await self._inf_repo.get_latest_by_uc(uc.uc_code)
            if inf:
                total_consumption += inf.consumption_estimated_kw
                total_generation += inf.generation_kw or 0.0
                total_injection += inf.injection_kw_mid or 0.0

        technical_losses = round(total_consumption * TECHNICAL_LOSS_FACTOR, 4)
        residual = round(
            measured_kwh
            - total_consumption
            + total_injection
            - technical_losses,
            4,
        )
        absolute_error = round(abs(residual), 4)
        percentage_error = round(
            (residual / measured_kwh * 100) if measured_kwh > 0 else 0.0, 4
        )

        balance_status = self._classify_balance(percentage_error)
        operational_score = self._classify_risk(
            1 - min(abs(percentage_error) / 100, 1.0)
        )

        payload = TransformerBalanceCreate(
            transformer_id=transformer_id,
            period_start=period_start,
            period_end=period_end,
            measured_kwh=measured_kwh,
            estimated_consumption_kwh=round(total_consumption, 4),
            estimated_generation_kwh=round(total_generation, 4),
            estimated_injection_kwh=round(total_injection, 4),
            technical_losses_kwh=technical_losses,
            residual_kwh=residual,
            absolute_error=absolute_error,
            percentage_error=percentage_error,
            balance_status=balance_status,
            operational_score=operational_score,
            uc_count=uc_count,
            telemetered_count=telemetered,
            gd_count=gd_count,
        )

        balance = TransformerBalance(**payload.model_dump())
        saved = await self._bal_repo.save(balance)
        logger.info(
            "transformer_balance.computed",
            transformer_id=transformer_id,
            percentage_error=percentage_error,
            balance_status=balance_status.value,
        )
        return saved

    async def get_latest_balance(self, transformer_id: str) -> TransformerBalance:
        balance = await self._bal_repo.get_latest_by_transformer(transformer_id)
        if not balance:
            raise EntityNotFoundException(
                message=f"Nenhum balanço encontrado para transformador {transformer_id}.",
                details={"transformer_id": transformer_id},
            )
        return balance

    @staticmethod
    def _classify_risk(confidence: float) -> RiskScore:
        if confidence >= 0.80:
            return RiskScore.LOW
        if confidence >= 0.60:
            return RiskScore.MEDIUM
        if confidence >= 0.30:
            return RiskScore.HIGH
        return RiskScore.CRITICAL

    @staticmethod
    def _classify_balance(percentage_error: float) -> BalanceStatus:
        abs_err = abs(percentage_error)

        if abs_err <= 5.0:
            return BalanceStatus.BALANCED

        if percentage_error > 10.0:
            return BalanceStatus.OVER_INJECTED

        if percentage_error < -10.0:
            return BalanceStatus.UNDER_GENERATED

        if abs_err >= 25.0:
            return BalanceStatus.CRITICAL

        if abs_err >= 15.0:
            return BalanceStatus.HIGH_LOSS

        return BalanceStatus.UNKNOWN