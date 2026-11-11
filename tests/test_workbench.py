from posthog_wb import (
    AiGenerationEvent,
    TelemetryErasureStore,
    aggregate_events_by_weekday,
    build_weekday_hogql,
    summarize_ai_traces,
)


def test_hogql_weekday_generation_and_timezone_shift():
    sql = build_weekday_hogql("$pageview", tz="Europe/London", weekdays_only=True)
    assert "toDayOfWeek(toTimezone(timestamp, 'Europe/London'))" in sql
    assert "BETWEEN 1 AND 5" in sql

    # 2026-11-11 is Wednesday; 22:30Z becomes Thursday in Asia/Tokyo (+9)
    events = [
        {"event": "$pageview", "timestamp": "2026-11-11T10:00:00Z"},
        {"event": "$pageview", "timestamp": "2026-11-11T22:30:00Z"},
    ]
    utc_rows = aggregate_events_by_weekday(events, tz="UTC")
    assert utc_rows == [{"day_num": 3, "weekday_name": "Wednesday", "total_events": 2}]

    tokyo_rows = aggregate_events_by_weekday(events, tz="Asia/Tokyo")
    assert [r["weekday_name"] for r in tokyo_rows] == ["Wednesday", "Thursday"]


def test_gdpr_property_unset_vs_full_erasure_and_tombstones():
    store = TelemetryErasureStore()
    store.ingest_event(
        "usr_gdpr_1",
        "signup",
        properties={"plan": "pro"},
        set_props={"email": "alice@example.com", "role": "admin"},
    )
    unset_plan = store.unset_person_properties("usr_gdpr_1", ["email"])
    assert "email" not in store.persons["usr_gdpr_1"]
    assert store.persons["usr_gdpr_1"]["role"] == "admin"
    assert unset_plan.delete_events is False

    # Late-arriving retry carrying scrubbed PII must not re-populate 'email'
    store.ingest_event("usr_gdpr_1", "page_leave", set_props={"email": "alice@example.com"})
    assert "email" not in store.persons["usr_gdpr_1"]

    # Full GDPR Article 17 erasure deletes both person profile and event rows
    del_plan = store.gdpr_delete_person_and_events("usr_gdpr_1")
    assert del_plan.delete_events is True
    assert "usr_gdpr_1" not in store.persons
    assert len(store.raw_events) == 0
    assert store.ingest_event("usr_gdpr_1", "late_ping") is False


def test_ai_generation_trace_summary():
    out = summarize_ai_traces([
        AiGenerationEvent("tr1", "claude-sonnet", 500, 120, 410.0, 0.0033),
        AiGenerationEvent("tr2", "claude-sonnet", 900, 200, 1250.0, 0.0057, is_error=True),
    ])
    assert out["trace_count"] == 2
    assert out["error_rate"] == 0.5
    assert out["p95_latency_ms"] == 1250.0
