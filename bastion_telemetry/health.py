"""Local health snapshot models for telemetry dashboards."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class HealthSnapshot(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    component: str
    status: str
    detail: str = ""
    latency_ms: float | None = None

    @property
    def is_ok(self) -> bool:
        return self.status.upper() in {"OK", "PASS", "HEALTHY"}
