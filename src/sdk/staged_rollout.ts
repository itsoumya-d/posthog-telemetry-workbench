/**
 * Consistent hashing and staged feature rollout evaluator for client SDK experiments.
 */

export function hashDistinctId(distinctId: string, seed: string): number {
  let hash = 2166136261;
  const input = `${seed}:${distinctId}`;
  for (let i = 0; i < input.length; i++) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return Math.abs(hash) % 100;
}

export interface RolloutEvaluation {
  distinctId: string;
  experimentKey: string;
  rolloutPercentage: number;
  bucket: number;
  isEnrolled: boolean;
}

export function evaluateStagedRollout(
  distinctId: string,
  experimentKey: string,
  rolloutPercentage: number
): RolloutEvaluation {
  const clamped = Math.max(0, Math.min(100, rolloutPercentage));
  const bucket = hashDistinctId(distinctId, experimentKey);
  return {
    distinctId,
    experimentKey,
    rolloutPercentage: clamped,
    bucket,
    isEnrolled: bucket < clamped,
  };
}
