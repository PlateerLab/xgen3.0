"""xgen 특수 도구 — 이메일, PDF, Excel/CSV, ML 추론, 워크플로우 실행."""

from __future__ import annotations

import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import httpx

from src.tools.decorator import tool

CORE_URL = os.environ.get("CORE_SERVICE_BASE_URL", "http://xgen-core:8000")
API_KEY = os.environ.get("XGEN_INTERNAL_API_KEY", "xgen-internal-key-2024")


# ═══════════════════════════════════════════════════
# 이메일 전송
# ═══════════════════════════════════════════════════

@tool(
    name="send_email",
    description="SMTP를 통해 이메일을 전송한다. 제목, 본문, 수신자를 지정하며 HTML 본문도 지원한다. SMTP 설정은 환경변수(SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD)에서 읽는다.",
    parameters={
        "to": {"type": "string", "description": "수신자 이메일 주소 (쉼표로 복수 가능)"},
        "subject": {"type": "string", "description": "이메일 제목"},
        "body": {"type": "string", "description": "이메일 본문 (텍스트 또는 HTML)"},
        "html": {"type": "boolean", "description": "HTML 본문 여부 (기본 false)", "optional": True},
    },
)
async def send_email(to: str, subject: str, body: str, html: bool = False) -> dict:
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASSWORD", "")
    from_addr = os.environ.get("SMTP_FROM", smtp_user)

    if not smtp_user:
        return {"success": False, "error": "SMTP_USER 환경변수가 설정되지 않았습니다"}

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to

    if html:
        msg.attach(MIMEText(body, "html", "utf-8"))
    else:
        msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            recipients = [addr.strip() for addr in to.split(",")]
            server.sendmail(from_addr, recipients, msg.as_string())
        return {"success": True, "to": to, "subject": subject}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════
# Excel/CSV 읽기·쓰기
# ═══════════════════════════════════════════════════

@tool(
    name="read_table_data",
    description="Excel(.xlsx) 또는 CSV 파일을 읽어서 JSON 배열로 반환한다. 시트 이름을 지정하거나 행 수를 제한할 수 있다.",
    parameters={
        "file_path": {"type": "string", "description": "파일 경로 (로컬 또는 MinIO URL)"},
        "sheet_name": {"type": "string", "description": "Excel 시트 이름 (기본: 첫 번째 시트)", "optional": True},
        "max_rows": {"type": "integer", "description": "최대 읽을 행 수 (기본 1000)", "optional": True},
    },
)
async def read_table_data(file_path: str, sheet_name: str | None = None, max_rows: int = 1000) -> dict:
    try:
        import pandas as pd
    except ImportError:
        return {"success": False, "error": "pandas가 설치되지 않았습니다. pip install pandas openpyxl"}

    try:
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path, nrows=max_rows)
        else:
            df = pd.read_excel(file_path, sheet_name=sheet_name or 0, nrows=max_rows)

        records = df.head(max_rows).to_dict(orient="records")
        return {
            "success": True,
            "rows": len(records),
            "columns": list(df.columns),
            "data": records,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="write_table_data",
    description="JSON 데이터를 Excel(.xlsx) 또는 CSV 파일로 저장한다.",
    parameters={
        "file_path": {"type": "string", "description": "저장할 파일 경로 (.xlsx 또는 .csv)"},
        "data": {"type": "array", "description": "저장할 데이터 (딕셔너리 배열)"},
        "sheet_name": {"type": "string", "description": "Excel 시트 이름 (기본: Sheet1)", "optional": True},
    },
)
async def write_table_data(data: list, file_path: str, sheet_name: str = "Sheet1") -> dict:
    try:
        import pandas as pd
    except ImportError:
        return {"success": False, "error": "pandas가 설치되지 않았습니다"}

    try:
        df = pd.DataFrame(data)
        if file_path.endswith(".csv"):
            df.to_csv(file_path, index=False)
        else:
            df.to_excel(file_path, index=False, sheet_name=sheet_name)
        return {"success": True, "file_path": file_path, "rows": len(df)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════
# ML 모델 추론
# ═══════════════════════════════════════════════════

@tool(
    name="ml_inference",
    description="등록된 ML 모델에 추론 요청을 보낸다. model_id로 모델을 지정하고 input_data로 입력을 전달한다. MLflow 또는 커스텀 모델 서버를 지원한다.",
    parameters={
        "model_id": {"type": "string", "description": "모델 ID 또는 이름"},
        "input_data": {"type": "object", "description": "모델 입력 데이터 (JSON)"},
    },
)
async def ml_inference(model_id: str, input_data: dict) -> dict:
    # xgen-core DB에서 모델 엔드포인트 조회
    async with httpx.AsyncClient(timeout=60) as client:
        # 모델 정보 조회
        resp = await client.post(
            f"{CORE_URL}/api/data/db/find-by-condition",
            headers={"Content-Type": "application/json", "X-API-Key": API_KEY},
            json={"table_name": "ml_models", "conditions": {"name": model_id}},
        )
        resp.raise_for_status()
        result = resp.json()

        models = result.get("data", [])
        if not models:
            return {"success": False, "error": f"모델 '{model_id}'을 찾을 수 없습니다"}

        model = models[0]
        endpoint = model.get("endpoint_url", "")
        if not endpoint:
            return {"success": False, "error": f"모델 '{model_id}'의 엔드포인트가 설정되지 않았습니다"}

        # 추론 요청
        infer_resp = await client.post(
            endpoint,
            json={"inputs": input_data},
            timeout=120,
        )
        infer_resp.raise_for_status()
        return {"success": True, "model_id": model_id, "result": infer_resp.json()}


# ═══════════════════════════════════════════════════
# 워크플로우 실행 (다른 에이전트 호출)
# ═══════════════════════════════════════════════════

@tool(
    name="run_workflow",
    description="다른 에이전트(워크플로우)를 실행한다. 에이전트 이름과 입력 메시지를 지정하면 해당 에이전트가 결과를 반환한다. 복잡한 작업을 여러 에이전트로 분할할 때 사용한다.",
    parameters={
        "agent_name": {"type": "string", "description": "실행할 에이전트 이름 (예: data-analyst)"},
        "message": {"type": "string", "description": "에이전트에게 보낼 메시지"},
    },
)
async def run_workflow(agent_name: str, message: str) -> dict:
    # 자기 자신의 API를 호출하여 다른 에이전트 실행
    agent_url = os.environ.get("AGENT_SELF_URL", "http://localhost:8000")
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{agent_url}/api/agent/run",
            json={
                "workflow_name": agent_name,
                "workflow_id": agent_name,
                "input_data": message,
            },
        )
        resp.raise_for_status()
        result = resp.json()
        return {"success": True, "agent": agent_name, "result": result.get("result", "")}
