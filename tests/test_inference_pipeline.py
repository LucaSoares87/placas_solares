from ml_engine.pipeline.inference_pipeline import (
    EnergyInferencePipeline,
    InferenceRequest,
)


def test_inference_pipeline_returns_expected_shape():
    pipeline = EnergyInferencePipeline()

    request = InferenceRequest(
        uc_code="123456",
        transformer_id="TR-102",
        latitude=-8.034,
        longitude=-34.941,
        area_m2=28.0,
        consumption_estimated_kw=2.6,
        irradiance_wm2=[
            0, 0, 0, 0, 50, 150, 350, 600, 800, 900, 850, 700,
            550, 400, 250, 120, 40, 0, 0, 0, 0, 0, 0, 0,
        ],
        temperature_c=[
            24, 24, 24, 24, 25, 26, 27, 28, 30, 31, 32, 33,
            33, 32, 31, 30, 28, 27, 26, 25, 25, 24, 24, 24,
        ],
        detection_confidence=0.84,
    )

    result = pipeline.run(request)

    assert result.uc_code == "123456"
    assert result.transformer_id == "TR-102"
    assert result.has_fv is True
    assert result.kwp_estimated > 0
    assert result.generation_kw >= 0
    assert result.confidence > 0
    assert result.status in {"injetando", "equilibrado", "consumindo"}
    assert result.score_operacional in {"baixo_risco", "medio_risco", "alto_risco"}


def test_inference_pipeline_rejects_invalid_area():
    pipeline = EnergyInferencePipeline()

    request = InferenceRequest(
        uc_code="123456",
        transformer_id="TR-102",
        latitude=-8.034,
        longitude=-34.941,
        area_m2=-1.0,
        consumption_estimated_kw=2.6,
        irradiance_wm2=[800],
        temperature_c=[30],
    )

    try:
        pipeline.run(request)
    except ValueError as exc:
        assert "area_m2" in str(exc)
    else:
        raise AssertionError("Expected ValueError")