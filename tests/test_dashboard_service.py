import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from backend.schemas.dashboard import (
    SnapshotRequest,
    ExportRequest,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
def transformer_id() -> str:
    return "TR-102"


@pytest.fixture
def snapshot_request(transformer_id: str) -> SnapshotRequest:
    return SnapshotRequest(
        transformer_id=transformer_id,
        reference_period="2025-05",
        total_ucs=120,
        total_ucs_fv=38,
        kwp_total_estimado=195.4,
        area_total_m2=1302.0,
        geracao_total_kwh=28800.0,
        consumo_total_kwh=41200.0,
        injecao_total_kwh=4800.0,
        balanco_estimado_kwh=8400.0,
        balanco_real_kwh=8100.0,
        erro_balanco_pct=3.7,
        kwp_factor_atual=0.150,
        loss_factor_atual=0.048,
        modelo_convergido=True,
        score_operacional="baixo_risco",
        total_anomalias_ativas=2,
        total_inspecoes_pendentes=1,
        confianca_media_deteccao=0.88,
        coordinates={"lat": -8.034, "lon": -34.941},
    )


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock()


class TestSnapshotRequest:
    def test_valid_request(self, snapshot_request: SnapshotRequest):
        assert snapshot_request.transformer_id == "TR-102"
        assert snapshot_request.total_ucs == 120
        assert snapshot_request.total_ucs_fv == 38

    def test_cobertura_fv_calculavel(self, snapshot_request: SnapshotRequest):
        cobertura = snapshot_request.total_ucs_fv / snapshot_request.total_ucs * 100
        assert round(cobertura, 1) == 31.7

    def test_coordinates_present(self, snapshot_request: SnapshotRequest):
        assert snapshot_request.coordinates is not None
        assert "lat" in snapshot_request.coordinates
        assert "lon" in snapshot_request.coordinates

    def test_default_score(self):
        req = SnapshotRequest(
            transformer_id="TR-001",
            reference_period="2025-05",
            total_ucs=10,
            total_ucs_fv=2,
        )
        assert req.score_operacional == "baixo_risco"
        assert req.total_anomalias_ativas == 0


class TestAlertService:
    def test_evaluate_snapshot_no_alerts(self, mock_db: MagicMock):
        from backend.services.alert_service import AlertService

        service = AlertService(mock_db)
        service._repo = MagicMock()
        service._repo.create = MagicMock(
            return_value=MagicMock(
                id=1,
                transformer_id="TR-102",
                uc_code=None,
                alert_type="test",
                severity="medio",
                title="t",
                message="m",
                threshold_value=None,
                observed_value=None,
                status="aberto",
                acknowledged_by=None,
                acknowledged_at=None,
                resolved_at=None,
                created_at=utc_now(),
            )
        )

        result = service.evaluate_snapshot(
            {
                "transformer_id": "TR-102",
                "erro_balanco_pct": 5.0,
                "total_anomalias_ativas": 1,
                "confianca_media_deteccao": 0.85,
                "score_operacional": "baixo_risco",
            }
        )
        assert result == []

    def test_evaluate_snapshot_critico(self, mock_db: MagicMock):
        from backend.services.alert_service import AlertService

        created_records = []

        def fake_create(data):
            mock = MagicMock()
            mock.id = len(created_records) + 1
            mock.transformer_id = data["transformer_id"]
            mock.uc_code = data.get("uc_code")
            mock.alert_type = data["alert_type"]
            mock.severity = data["severity"]
            mock.title = data["title"]
            mock.message = data["message"]
            mock.threshold_value = data.get("threshold_value")
            mock.observed_value = data.get("observed_value")
            mock.status = "aberto"
            mock.acknowledged_by = None
            mock.acknowledged_at = None
            mock.resolved_at = None
            mock.created_at = utc_now()
            created_records.append(mock)
            return mock

        service = AlertService(mock_db)
        service._repo = MagicMock()
        service._repo.create = MagicMock(side_effect=fake_create)

        result = service.evaluate_snapshot(
            {
                "transformer_id": "TR-102",
                "erro_balanco_pct": 40.0,
                "total_anomalias_ativas": 10,
                "confianca_media_deteccao": 0.40,
                "score_operacional": "prioridade_inspecao",
            }
        )

        assert len(result) >= 3
        severities = {alert.severity for alert in result}
        assert "critico" in severities

    def test_evaluate_snapshot_erro_alto(self, mock_db: MagicMock):
        from backend.services.alert_service import AlertService

        created = []

        def fake_create(data):
            mock = MagicMock(
                **{
                    **data,
                    "id": 1,
                    "uc_code": None,
                    "acknowledged_by": None,
                    "acknowledged_at": None,
                    "resolved_at": None,
                    "created_at": utc_now(),
                }
            )
            created.append(mock)
            return mock

        service = AlertService(mock_db)
        service._repo = MagicMock()
        service._repo.create = MagicMock(side_effect=fake_create)

        service.evaluate_snapshot(
            {
                "transformer_id": "TR-102",
                "erro_balanco_pct": 25.0,
                "total_anomalias_ativas": 0,
                "confianca_media_deteccao": 0.85,
                "score_operacional": "alto_risco",
            }
        )

        alert_types = [
            call.args[0]["alert_type"] for call in service._repo.create.call_args_list
        ]
        assert "erro_balanco_alto" in alert_types

    def test_evaluate_low_confidence_alert(self, mock_db: MagicMock):
        from backend.services.alert_service import AlertService

        created = []

        def fake_create(data):
            mock = MagicMock(
                **{
                    **data,
                    "id": 1,
                    "uc_code": None,
                    "acknowledged_by": None,
                    "acknowledged_at": None,
                    "resolved_at": None,
                    "created_at": utc_now(),
                }
            )
            created.append(mock)
            return mock

        service = AlertService(mock_db)
        service._repo = MagicMock()
        service._repo.create = MagicMock(side_effect=fake_create)

        service.evaluate_snapshot(
            {
                "transformer_id": "TR-102",
                "erro_balanco_pct": 5.0,
                "total_anomalias_ativas": 0,
                "confianca_media_deteccao": 0.45,
                "score_operacional": "baixo_risco",
            }
        )

        alert_types = [
            call.args[0]["alert_type"] for call in service._repo.create.call_args_list
        ]
        assert "baixa_confianca_deteccao" in alert_types


class TestDashboardRepositoryUnit:
    def test_get_risk_ranking_sorted(self):
        from backend.repositories.dashboard_repository import DashboardRepository

        repo = DashboardRepository.__new__(DashboardRepository)

        mock_snapshots = []
        data = [
            ("TR-A", "baixo_risco", 5.0, 0),
            ("TR-B", "prioridade_inspecao", 42.0, 12),
            ("TR-C", "alto_risco", 28.0, 5),
            ("TR-D", "medio_risco", 15.0, 2),
        ]

        for transformer_id, score, erro, anomalias in data:
            snapshot = MagicMock()
            snapshot.transformer_id = transformer_id
            snapshot.score_operacional = score
            snapshot.erro_balanco_pct = erro
            snapshot.total_anomalias_ativas = anomalias
            snapshot.kwp_total_estimado = 50.0
            snapshot.total_ucs_fv = 10
            snapshot.confianca_media_deteccao = 0.85
            snapshot.reference_period = "2025-05"
            mock_snapshots.append(snapshot)

        repo.list_all_latest = MagicMock(return_value=mock_snapshots)
        ranking = repo.get_risk_ranking(limit=10)

        assert ranking[0]["transformer_id"] == "TR-B"
        assert ranking[1]["transformer_id"] == "TR-C"
        assert ranking[0]["rank"] == 1

    def test_get_global_kpis_empty(self):
        from backend.repositories.dashboard_repository import DashboardRepository

        repo = DashboardRepository.__new__(DashboardRepository)
        repo.list_all_latest = MagicMock(return_value=[])
        kpis = repo.get_global_kpis()

        assert kpis["total_transformadores"] == 0
        assert kpis["kwp_total"] == 0.0
        assert kpis["total_anomalias_ativas"] == 0

    def test_get_global_kpis_aggregation(self):
        from backend.repositories.dashboard_repository import DashboardRepository

        repo = DashboardRepository.__new__(DashboardRepository)

        snapshots = []
        for _ in range(3):
            snapshot = MagicMock()
            snapshot.total_ucs = 100
            snapshot.total_ucs_fv = 30
            snapshot.kwp_total_estimado = 150.0
            snapshot.geracao_total_kwh = 10000.0
            snapshot.consumo_total_kwh = 20000.0
            snapshot.total_anomalias_ativas = 2
            snapshot.score_operacional = "baixo_risco"
            snapshot.erro_balanco_pct = 5.0
            snapshots.append(snapshot)

        repo.list_all_latest = MagicMock(return_value=snapshots)
        kpis = repo.get_global_kpis()

        assert kpis["total_transformadores"] == 3
        assert kpis["total_ucs"] == 300
        assert kpis["kwp_total"] == pytest.approx(450.0)
        assert kpis["total_anomalias_ativas"] == 6
        assert kpis["transformadores_criticos"] == 0


class TestExportService:
    def test_export_csv_has_header(self, mock_db: MagicMock):
        from backend.services.export_service import ExportService

        service = ExportService.__new__(ExportService)
        service._dash_repo = MagicMock()
        service._val_repo = MagicMock()
        service._anomaly_repo = MagicMock()
        service._calib_repo = MagicMock()

        mock_snap = MagicMock()
        mock_snap.transformer_id = "TR-102"
        mock_snap.reference_period = "2025-05"
        mock_snap.total_ucs = 120
        mock_snap.total_ucs_fv = 38
        mock_snap.cobertura_fv_pct = 31.7
        mock_snap.kwp_total_estimado = 195.4
        mock_snap.geracao_total_kwh = 28800.0
        mock_snap.consumo_total_kwh = 41200.0
        mock_snap.balanco_estimado_kwh = 8400.0
        mock_snap.balanco_real_kwh = 8100.0
        mock_snap.erro_balanco_pct = 3.7
        mock_snap.score_operacional = "baixo_risco"
        mock_snap.total_anomalias_ativas = 2
        mock_snap.total_inspecoes_pendentes = 1
        mock_snap.confianca_media_deteccao = 0.88
        mock_snap.kwp_factor_atual = 0.150
        mock_snap.loss_factor_atual = 0.048
        mock_snap.modelo_convergido = True

        service._dash_repo.list_all_latest = MagicMock(return_value=[mock_snap])
        service._val_repo.get_by_transformer = MagicMock(return_value=[])
        service._anomaly_repo.get_active_by_transformer = MagicMock(return_value=[])
        service._calib_repo.get_latest = MagicMock(return_value=None)

        req = ExportRequest(format="csv")
        csv_content = service.export_csv(req)

        assert "transformer_id" in csv_content
        assert "TR-102" in csv_content
        assert "erro_balanco_pct" in csv_content

    def test_export_json_structure(self, mock_db: MagicMock):
        from backend.services.export_service import ExportService

        service = ExportService.__new__(ExportService)
        service._dash_repo = MagicMock()
        service._val_repo = MagicMock()
        service._anomaly_repo = MagicMock()
        service._calib_repo = MagicMock()

        mock_snap = MagicMock()
        mock_snap.transformer_id = "TR-102"
        mock_snap.reference_period = "2025-05"
        mock_snap.total_ucs = 120
        mock_snap.total_ucs_fv = 38
        mock_snap.cobertura_fv_pct = 31.7
        mock_snap.kwp_total_estimado = 195.4
        mock_snap.geracao_total_kwh = 28800.0
        mock_snap.consumo_total_kwh = 41200.0
        mock_snap.balanco_estimado_kwh = 8400.0
        mock_snap.balanco_real_kwh = 8100.0
        mock_snap.erro_balanco_pct = 3.7
        mock_snap.score_operacional = "baixo_risco"
        mock_snap.total_anomalias_ativas = 2
        mock_snap.total_inspecoes_pendentes = 1
        mock_snap.confianca_media_deteccao = 0.88
        mock_snap.kwp_factor_atual = 0.150
        mock_snap.loss_factor_atual = 0.048
        mock_snap.modelo_convergido = True

        service._dash_repo.list_all_latest = MagicMock(return_value=[mock_snap])
        service._val_repo.get_by_transformer = MagicMock(return_value=[])
        service._anomaly_repo.get_active_by_transformer = MagicMock(return_value=[])
        service._calib_repo.get_latest = MagicMock(return_value=None)

        req = ExportRequest(format="json")
        result = service.export_json(req)

        assert "transformers" in result
        assert len(result["transformers"]) == 1
        assert result["transformers"][0]["transformer_id"] == "TR-102"
        assert "kpis" in result["transformers"][0]
        assert "risk" in result["transformers"][0]
        assert "calibration" in result["transformers"][0]

    def test_export_bi_payload_structure(self, mock_db: MagicMock):
        from backend.services.export_service import ExportService

        service = ExportService.__new__(ExportService)
        service._dash_repo = MagicMock()
        service._calib_repo = MagicMock()

        service._dash_repo.get_global_kpis = MagicMock(
            return_value={
                "total_transformadores": 1,
                "total_ucs": 120,
                "total_ucs_fv": 38,
                "cobertura_fv_pct": 31.7,
                "kwp_total": 195.4,
                "geracao_total_kwh": 28800.0,
                "consumo_total_kwh": 41200.0,
                "erro_medio_balanco_pct": 3.7,
                "total_anomalias_ativas": 2,
                "transformadores_criticos": 0,
            }
        )

        mock_snap = MagicMock()
        mock_snap.transformer_id = "TR-102"
        mock_snap.reference_period = "2025-05"
        mock_snap.score_operacional = "baixo_risco"
        mock_snap.total_ucs = 120
        mock_snap.total_ucs_fv = 38
        mock_snap.cobertura_fv_pct = 31.7
        mock_snap.kwp_total_estimado = 195.4
        mock_snap.geracao_total_kwh = 28800.0
        mock_snap.consumo_total_kwh = 41200.0
        mock_snap.erro_balanco_pct = 3.7
        mock_snap.total_anomalias_ativas = 0
        mock_snap.modelo_convergido = True
        mock_snap.kwp_factor_atual = 0.150
        mock_snap.loss_factor_atual = 0.048
        mock_snap.gerado_em = utc_now()

        service._dash_repo.list_all_latest = MagicMock(return_value=[mock_snap])
        service._calib_repo.get_latest = MagicMock(return_value=None)

        result = service.export_bi_payload()

        assert result.schema_version == "1.0"
        assert "total_transformadores" in result.kpis
        assert len(result.transformers) == 1
        assert isinstance(result.anomalies_summary, list)
        assert isinstance(result.calibration_summary, list)


class TestMapSchema:
    def test_map_response_geojson_type(self):
        from backend.schemas.dashboard import MapFeature, MapFeatureProperties, MapResponse

        feature = MapFeature(
            geometry={"type": "Point", "coordinates": [-34.941, -8.034]},
            properties=MapFeatureProperties(
                transformer_id="TR-102",
                score_operacional="baixo_risco",
                kwp_total_estimado=195.4,
                total_ucs_fv=38,
                erro_balanco_pct=3.7,
                total_anomalias_ativas=2,
                reference_period="2025-05",
            ),
        )

        response = MapResponse(total_features=1, features=[feature])
        assert response.type == "FeatureCollection"
        assert response.total_features == 1
        assert response.features[0].type == "Feature"
        assert response.features[0].geometry["type"] == "Point"

    def test_map_feature_without_geometry(self):
        from backend.schemas.dashboard import MapFeature, MapFeatureProperties

        feature = MapFeature(
            geometry=None,
            properties=MapFeatureProperties(
                transformer_id="TR-103",
                score_operacional="medio_risco",
                kwp_total_estimado=None,
                total_ucs_fv=None,
                erro_balanco_pct=None,
                total_anomalias_ativas=None,
                reference_period=None,
            ),
        )
        assert feature.geometry is None
        assert feature.properties.transformer_id == "TR-103"


class TestBIPayloadSchema:
    def test_schema_version(self):
        from backend.schemas.dashboard import BIPayloadResponse

        payload = BIPayloadResponse(
            kpis={"total_transformadores": 5},
            transformers=[],
            anomalies_summary=[],
            calibration_summary=[],
        )
        assert payload.schema_version == "1.0"
        assert isinstance(payload.generated_at, datetime)

    def test_fields_present(self):
        from backend.schemas.dashboard import BIPayloadResponse

        payload = BIPayloadResponse(
            kpis={"kwp_total": 900.5},
            transformers=[{"transformer_id": "TR-102"}],
            anomalies_summary=[{"transformer_id": "TR-102", "total_anomalias_ativas": 3}],
            calibration_summary=[{"kwp_factor_new": 0.152}],
        )
        assert payload.kpis["kwp_total"] == 900.5
        assert len(payload.transformers) == 1
        assert len(payload.anomalies_summary) == 1
        assert len(payload.calibration_summary) == 1