import test from "node:test";
import assert from "node:assert/strict";
import { hashDistinctId, evaluateStagedRollout } from "../src/sdk/staged_rollout.ts";

test("hashDistinctId returns consistent deterministic bucket 0-99", () => {
  const b1 = hashDistinctId("user_12345", "exp_tier_pricing");
  const b2 = hashDistinctId("user_12345", "exp_tier_pricing");
  assert.equal(b1, b2);
  assert.ok(b1 >= 0 && b1 < 100);
});

test("evaluateStagedRollout respects percentage threshold", () => {
  // 0% rollout enrolls nobody
  const zero = evaluateStagedRollout("user_test", "exp_1", 0);
  assert.equal(zero.isEnrolled, false);

  // 100% rollout enrolls everybody
  const full = evaluateStagedRollout("user_test", "exp_1", 100);
  assert.equal(full.isEnrolled, true);
});
