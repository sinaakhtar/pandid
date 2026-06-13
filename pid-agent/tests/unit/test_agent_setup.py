import pytest
from app.agent import extractor_agent, save_file_as_artifact, zoomer_agent, validate_dataset_id


def test_zoomer_agent_defined():
    assert zoomer_agent is not None
    assert zoomer_agent.name == "zoomer_agent"
    assert zoomer_agent.code_executor is not None


def test_extractor_agent_updated():
    assert extractor_agent is not None
    assert "zoomer_agent" in [sa.name for sa in extractor_agent.sub_agents]
    assert save_file_as_artifact in extractor_agent.tools


def test_validate_dataset_id_valid():
    # These should pass without throwing any exceptions
    validate_dataset_id("pandid")
    validate_dataset_id("pandid_dataset")
    validate_dataset_id("pandid_123_abc")


def test_validate_dataset_id_invalid():
    with pytest.raises(ValueError, match="must contain only letters"):
        validate_dataset_id("pandid-dataset")  # contains hyphen
    
    with pytest.raises(ValueError, match="must contain only letters"):
        validate_dataset_id("pandid dataset")  # contains space

    with pytest.raises(ValueError, match="environment variable is empty"):
        validate_dataset_id("")  # empty

    with pytest.raises(ValueError, match="at most 1024 characters"):
        validate_dataset_id("a" * 1025)  # too long


def test_extraction_result_has_session_id():
    from app.agent import ExtractionResult
    res = ExtractionResult(diagram_id="test_diag", nodes=[], edges=[])
    assert res.session_id is None
    res.session_id = "test_session_123"
    assert res.session_id == "test_session_123"

