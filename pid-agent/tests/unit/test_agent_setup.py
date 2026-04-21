from app.agent import zoomer_agent, extractor_agent, save_file_as_artifact

def test_zoomer_agent_defined():
    assert zoomer_agent is not None
    assert zoomer_agent.name == "zoomer_agent"
    assert zoomer_agent.code_executor is not None

def test_extractor_agent_updated():
    assert extractor_agent is not None
    assert "zoomer_agent" in [sa.name for sa in extractor_agent.sub_agents]
    assert save_file_as_artifact in extractor_agent.tools
