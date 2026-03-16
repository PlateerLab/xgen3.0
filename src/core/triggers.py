"""트리거 — Webhook / 스케줄 기반 Agent 자동 실행."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class TriggerType(str, Enum):
    WEBHOOK = "webhook"
    SCHEDULE = "schedule"


@dataclass
class TriggerConfig:
    """트리거 설정."""

    trigger_type: TriggerType
    agent_name: str

    # Webhook
    path: str | None = None  # 예: "/support"

    # Schedule
    cron: str | None = None  # 예: "0 9 * * *"

    # 공통
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class TriggerManager:
    """트리거 관리 — Agent 자동 실행 스케줄링.

    Webhook: FastAPI 라우터에 동적 경로 추가
    Schedule: asyncio 기반 cron-like 스케줄러
    """

    def __init__(self):
        self._triggers: dict[str, TriggerConfig] = {}
        self._schedule_tasks: dict[str, asyncio.Task] = {}
        self._handlers: dict[str, Callable[..., Awaitable]] = {}

    def register(
        self, trigger_id: str, config: TriggerConfig, handler: Callable[..., Awaitable]
    ) -> None:
        """트리거 등록."""
        self._triggers[trigger_id] = config
        self._handlers[trigger_id] = handler
        logger.info("트리거 등록: %s (%s)", trigger_id, config.trigger_type.value)

    def unregister(self, trigger_id: str) -> None:
        """트리거 제거."""
        self._triggers.pop(trigger_id, None)
        self._handlers.pop(trigger_id, None)
        task = self._schedule_tasks.pop(trigger_id, None)
        if task:
            task.cancel()

    async def fire_webhook(self, path: str, payload: dict) -> dict | None:
        """Webhook 트리거 실행."""
        for trigger_id, config in self._triggers.items():
            if (
                config.trigger_type == TriggerType.WEBHOOK
                and config.path == path
                and config.enabled
            ):
                handler = self._handlers.get(trigger_id)
                if handler:
                    logger.info("Webhook 트리거 실행: %s → %s", path, config.agent_name)
                    return await handler(payload)
        return None

    def start_schedules(self) -> None:
        """모든 스케줄 트리거 시작."""
        for trigger_id, config in self._triggers.items():
            if config.trigger_type == TriggerType.SCHEDULE and config.enabled:
                if config.cron:
                    task = asyncio.create_task(
                        self._schedule_loop(trigger_id, config)
                    )
                    self._schedule_tasks[trigger_id] = task

    async def _schedule_loop(self, trigger_id: str, config: TriggerConfig) -> None:
        """Cron 스케줄 루프 (간단 구현).

        정확한 cron 파싱은 croniter 등 외부 라이브러리 필요.
        Phase 4에서는 기본 interval 방식으로 대체.
        """
        # 간이 구현: cron 문자열에서 분 간격 추출
        interval = self._parse_interval(config.cron or "")
        if interval <= 0:
            logger.warning("cron 파싱 불가: %s, 기본 1시간 간격", config.cron)
            interval = 3600

        while True:
            await asyncio.sleep(interval)
            handler = self._handlers.get(trigger_id)
            if handler and config.enabled:
                try:
                    logger.info("스케줄 트리거 실행: %s", config.agent_name)
                    await handler({})
                except Exception as e:
                    logger.error("스케줄 트리거 실패: %s — %s", trigger_id, e)

    def _parse_interval(self, cron: str) -> int:
        """간이 cron → 초 변환. '*/5 * * * *' → 300."""
        parts = cron.strip().split()
        if not parts:
            return 0
        minute_part = parts[0]
        if minute_part.startswith("*/"):
            try:
                return int(minute_part[2:]) * 60
            except ValueError:
                return 0
        if minute_part == "0" and len(parts) >= 2:
            # "0 9 * * *" → 매일 → 86400
            return 86400
        return 3600  # 기본

    def list_triggers(self) -> list[dict]:
        """등록된 트리거 목록."""
        return [
            {
                "id": tid,
                "type": config.trigger_type.value,
                "agent": config.agent_name,
                "path": config.path,
                "cron": config.cron,
                "enabled": config.enabled,
            }
            for tid, config in self._triggers.items()
        ]

    def stop_all(self) -> None:
        """모든 스케줄 중지."""
        for task in self._schedule_tasks.values():
            task.cancel()
        self._schedule_tasks.clear()
