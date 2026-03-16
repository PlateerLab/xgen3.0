"""트리거 매니저 테스트."""

import pytest
from src.core.triggers import TriggerManager, TriggerConfig, TriggerType


def test_trigger_register():
    """트리거 등록."""
    mgr = TriggerManager()

    config = TriggerConfig(
        trigger_type=TriggerType.WEBHOOK,
        agent_name="support",
        path="/support",
    )

    async def handler(payload):
        return {"ok": True}

    mgr.register("t1", config, handler)
    triggers = mgr.list_triggers()
    assert len(triggers) == 1
    assert triggers[0]["type"] == "webhook"
    assert triggers[0]["path"] == "/support"


def test_trigger_unregister():
    """트리거 제거."""
    mgr = TriggerManager()

    config = TriggerConfig(trigger_type=TriggerType.WEBHOOK, agent_name="test")

    async def handler(p):
        pass

    mgr.register("t1", config, handler)
    assert len(mgr.list_triggers()) == 1

    mgr.unregister("t1")
    assert len(mgr.list_triggers()) == 0


@pytest.mark.asyncio
async def test_webhook_fire():
    """Webhook 트리거 실행."""
    mgr = TriggerManager()

    received = {}

    async def handler(payload):
        received.update(payload)
        return {"processed": True}

    config = TriggerConfig(
        trigger_type=TriggerType.WEBHOOK,
        agent_name="webhook-agent",
        path="/hook",
    )
    mgr.register("wh1", config, handler)

    result = await mgr.fire_webhook("/hook", {"event": "new_ticket"})
    assert result == {"processed": True}
    assert received["event"] == "new_ticket"


@pytest.mark.asyncio
async def test_webhook_no_match():
    """매칭되는 webhook이 없을 때."""
    mgr = TriggerManager()
    result = await mgr.fire_webhook("/없는경로", {})
    assert result is None


def test_parse_interval():
    """cron 간격 파싱."""
    mgr = TriggerManager()
    assert mgr._parse_interval("*/5 * * * *") == 300
    assert mgr._parse_interval("*/10 * * * *") == 600
    assert mgr._parse_interval("0 9 * * *") == 86400


def test_schedule_trigger_config():
    """스케줄 트리거 설정."""
    config = TriggerConfig(
        trigger_type=TriggerType.SCHEDULE,
        agent_name="batch",
        cron="*/30 * * * *",
    )
    assert config.trigger_type == TriggerType.SCHEDULE
    assert config.cron == "*/30 * * * *"
    assert config.enabled is True
