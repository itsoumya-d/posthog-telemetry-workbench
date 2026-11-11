import assert from "node:assert/strict";
import test from "node:test";
import { ClientRateLimiter } from "../src/sdk/rate_limiter.ts";

test("ClientRateLimiter enforces posthog-js defaults and explains video player burst drops", () => {
  let now = 1_700_000_000_000;
  const limiter = new ClientRateLimiter({ nowMs: () => now });

  // Consume default 100-event burst cleanly
  for (let i = 0; i < 100; i++) {
    const ok = limiter.tryCapture("video_timeupdate");
    assert.equal(ok.accepted, true);
  }

  const dropped = limiter.tryCapture("video_timeupdate");
  assert.equal(dropped.accepted, false);
  assert.match(dropped.diagnostic ?? "", /ignored due to client rate limiting/i);

  // Wait 2 seconds -> refills 20 tokens (10 eps * 2s)
  now += 2000;
  for (let i = 0; i < 20; i++) {
    assert.equal(limiter.tryCapture("video_timeupdate").accepted, true);
  }
  assert.equal(limiter.tryCapture("video_timeupdate").accepted, false);
});
