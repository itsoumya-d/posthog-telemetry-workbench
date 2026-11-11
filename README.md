# PostHog Telemetry Workbench

Dual-stack TypeScript + Python diagnostic workbench covering real-world product analytics & AI observability support workflows:

- **Client SDK Rate Limiter (`src/sdk/rate_limiter.ts`)**: Token-bucket limiter matching `posthog-js` defaults (`10` events/s, `100` burst) to diagnose and tune high-frequency bursts (e.g., HTML5 video player events).
- **HogQL Weekday Breakdown (`posthog_wb/hogql_weekday.py`)**: Timezone-aware `toDayOfWeek()` / `multiIf` query generator verified against local SQLite simulation.
- **GDPR Person & Property Erasure (`posthog_wb/gdpr_eraser.py`)**: Compares targeted `$unset` / `delete_property` profile scrubbing against full `DELETE /persons/:id?delete_events=true` erasure with late-arriving event tombstones.
- **LLM Observability Aggregator (`posthog_wb/llm_observability.py`)**: Summarizes `$ai_generation` costs, error rates, and p95 latencies.

```bash
npm test && pytest
```
