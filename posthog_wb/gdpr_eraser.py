from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ErasurePlan:
    person_id: str
    unset_properties: list[str]
    delete_events: bool
    api_calls: list[dict]
    tombstone_active: bool


@dataclass
class TelemetryErasureStore:
    """Simulates PostHog person state, immutable raw event log, and GDPR tombstone suppression."""

    persons: dict[str, dict] = field(default_factory=dict)
    raw_events: list[dict] = field(default_factory=list)
    tombstones: dict[str, set[str]] = field(default_factory=dict)

    def ingest_event(self, distinct_id: str, event: str, properties: dict | None = None, set_props: dict | None = None) -> bool:
        props = dict(properties or {})
        person_set = dict(set_props or {})

        blocked = self.tombstones.get(distinct_id, set())
        if "__ALL__" in blocked:
            return False  # Drop late-arriving event under active GDPR erasure mask

        for k in blocked:
            props.pop(k, None)
            person_set.pop(k, None)

        self.raw_events.append({"distinct_id": distinct_id, "event": event, "properties": props})
        prof = self.persons.setdefault(distinct_id, {})
        prof.update(person_set)
        return True

    def unset_person_properties(self, distinct_id: str, property_keys: list[str]) -> ErasurePlan:
        """Clear property on person profile state ($unset); does NOT rewrite past immutable events."""
        prof = self.persons.get(distinct_id, {})
        for k in property_keys:
            prof.pop(k, None)
        self.tombstones.setdefault(distinct_id, set()).update(property_keys)
        return ErasurePlan(
            person_id=distinct_id,
            unset_properties=list(property_keys),
            delete_events=False,
            api_calls=[
                {
                    "method": "POST",
                    "endpoint": f"/api/projects/:project_id/persons/{distinct_id}/delete_property",
                    "body": {"$unset": key},
                }
                for key in property_keys
            ],
            tombstone_active=True,
        )

    def gdpr_delete_person_and_events(self, distinct_id: str) -> ErasurePlan:
        """Full GDPR Article 17 deletion across person profile + historical event store."""
        self.persons.pop(distinct_id, None)
        self.raw_events = [e for e in self.raw_events if e["distinct_id"] != distinct_id]
        self.tombstones[distinct_id] = {"__ALL__"}
        return ErasurePlan(
            person_id=distinct_id,
            unset_properties=["*"],
            delete_events=True,
            api_calls=[
                {
                    "method": "DELETE",
                    "endpoint": f"/api/projects/:project_id/persons/{distinct_id}?delete_events=true",
                }
            ],
            tombstone_active=True,
        )
