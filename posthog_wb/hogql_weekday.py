from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


WEEKDAY_NAMES = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
    7: "Sunday",
}


def build_weekday_hogql(event_name: str = "$pageview", tz: str = "UTC", weekdays_only: bool = False) -> str:
    """Build valid PostHog HogQL SQL insight breaking down counts by weekday."""
    ts_expr = f"toTimezone(timestamp, '{tz}')" if tz != "UTC" else "timestamp"
    where_parts = [f"event = '{event_name}'"]
    if weekdays_only:
        where_parts.append(f"toDayOfWeek({ts_expr}) BETWEEN 1 AND 5")
    where_sql = " AND ".join(where_parts)
    return (
        "SELECT\n"
        f"    toDayOfWeek({ts_expr}) AS day_num,\n"
        "    multiIf(\n"
        f"        toDayOfWeek({ts_expr}) == 1, 'Monday',\n"
        f"        toDayOfWeek({ts_expr}) == 2, 'Tuesday',\n"
        f"        toDayOfWeek({ts_expr}) == 3, 'Wednesday',\n"
        f"        toDayOfWeek({ts_expr}) == 4, 'Thursday',\n"
        f"        toDayOfWeek({ts_expr}) == 5, 'Friday',\n"
        f"        toDayOfWeek({ts_expr}) == 6, 'Saturday',\n"
        "        'Sunday'\n"
        "    ) AS weekday_name,\n"
        "    count() AS total_events\n"
        "FROM events\n"
        f"WHERE {where_sql}\n"
        "GROUP BY day_num, weekday_name\n"
        "ORDER BY day_num ASC"
    )


def aggregate_events_by_weekday(events: list[dict], event_name: str = "$pageview", tz: str = "UTC") -> list[dict]:
    """Execute timezone-aware weekday aggregation in an in-memory SQLite store."""
    zone = ZoneInfo(tz)
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE events (event TEXT, day_num INTEGER, weekday_name TEXT)")
    rows = []
    for ev in events:
        dt = datetime.fromisoformat(ev["timestamp"].replace("Z", "+00:00")).astimezone(zone)
        day_num = dt.isoweekday()  # matches ClickHouse/HogQL toDayOfWeek (1=Mon..7=Sun)
        rows.append((ev["event"], day_num, WEEKDAY_NAMES[day_num]))
    conn.executemany("INSERT INTO events VALUES (?, ?, ?)", rows)
    cur = conn.execute(
        """
        SELECT day_num, weekday_name, COUNT(*) AS total_events
        FROM events
        WHERE event = ?
        GROUP BY day_num, weekday_name
        ORDER BY day_num ASC
        """,
        (event_name,),
    )
    out = [{"day_num": r[0], "weekday_name": r[1], "total_events": r[2]} for r in cur.fetchall()]
    conn.close()
    return out
