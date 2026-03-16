"""API 모델 테스트 — WorkflowRequest 호환 검증."""

from src.api.models import WorkflowRequest, SaveWorkflowRequest, WorkflowData


def test_workflow_request_string_input():
    """input_data가 문자열일 때 message 변환."""
    req = WorkflowRequest(
        workflow_name="test",
        workflow_id="wf-1",
        input_data="안녕하세요",
    )
    assert req.message == "안녕하세요"


def test_workflow_request_dict_input_message():
    """input_data가 dict이고 message 키가 있을 때."""
    req = WorkflowRequest(
        workflow_name="test",
        workflow_id="wf-1",
        input_data={"message": "질문입니다"},
    )
    assert req.message == "질문입니다"


def test_workflow_request_dict_input_input():
    """input_data가 dict이고 input 키가 있을 때."""
    req = WorkflowRequest(
        workflow_name="test",
        workflow_id="wf-1",
        input_data={"input": "데이터"},
    )
    assert req.message == "데이터"


def test_workflow_request_dict_input_other():
    """input_data가 dict이고 알려진 키가 없을 때."""
    req = WorkflowRequest(
        workflow_name="test",
        workflow_id="wf-1",
        input_data={"custom_field": "값"},
    )
    assert "custom_field" in req.message


def test_workflow_request_list_input():
    """input_data가 list일 때."""
    req = WorkflowRequest(
        workflow_name="test",
        workflow_id="wf-1",
        input_data=[{"a": 1}, {"b": 2}],
    )
    assert req.message != ""


def test_workflow_request_none_input():
    """input_data가 None일 때."""
    req = WorkflowRequest(
        workflow_name="test",
        workflow_id="wf-1",
    )
    assert req.message == ""


def test_workflow_request_defaults():
    """기본값 확인."""
    req = WorkflowRequest(workflow_name="w", workflow_id="1")
    assert req.interaction_id == "default"
    assert req.include_logs is True
    assert req.include_tool_events is True
    assert req.response_format == "json"
    assert req.resume is False


def test_workflow_request_all_fields():
    """모든 필드 설정."""
    req = WorkflowRequest(
        workflow_name="customer-support",
        workflow_id="wf-123",
        input_data="도움이 필요합니다",
        interaction_id="int-456",
        selected_collections=["col1"],
        selected_files=["file1.pdf"],
        user_id=42,
        additional_params={"node1": {"key": "val"}},
        bypass_agents=["agent-x"],
        include_logs=False,
        response_format="stream",
    )
    assert req.workflow_name == "customer-support"
    assert req.user_id == 42
    assert req.include_logs is False


def test_save_workflow_request():
    """SaveWorkflowRequest 호환."""
    req = SaveWorkflowRequest(
        workflow_name="my-wf",
        workflow_id="wf-001",
        content=WorkflowData(
            workflow_name="my-wf",
            workflow_id="wf-001",
            view={"zoom": 1.0},
            nodes=[{"id": "n1", "type": "start"}],
            edges=[{"source": "n1", "target": "n2"}],
        ),
        user_id=1,
    )
    assert req.workflow_name == "my-wf"
    assert isinstance(req.content, WorkflowData)
    assert len(req.content.nodes) == 1
