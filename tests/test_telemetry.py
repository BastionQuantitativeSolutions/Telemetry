from bastion_telemetry.health import HealthSnapshot
from bastion_telemetry.redaction import redact_record


def test_health_snapshot_ok_status():
    assert HealthSnapshot(component="feed", status="OK").is_ok


def test_redact_record_removes_sensitive_fields():
    record = redact_record({"ticket_id": "123", "symbol": "EURUSD"})
    assert record["ticket_id"] == "<redacted>"
    assert record["symbol"] == "EURUSD"
