export interface RateLimitConfig {
  eventsPerSecond: number;
  burstLimit: number;
  nowMs?: () => number;
}

export interface CaptureOutcome {
  accepted: boolean;
  diagnostic?: string;
  remainingTokens: number;
  recommendedFix?: string;
}

export class ClientRateLimiter {
  private readonly eventsPerSecond: number;
  private readonly burstLimit: number;
  private readonly nowMs: () => number;
  private tokens: number;
  private lastRefillMs: number;
  private ignoredCount = 0;

  constructor(config?: Partial<RateLimitConfig>) {
    this.eventsPerSecond = config?.eventsPerSecond ?? 10; // posthog-js default
    this.burstLimit = config?.burstLimit ?? this.eventsPerSecond * 10; // posthog-js default 100
    this.nowMs = config?.nowMs ?? (() => Date.now());
    this.tokens = this.burstLimit;
    this.lastRefillMs = this.nowMs();
  }

  private refill(): void {
    const now = this.nowMs();
    const elapsedSec = Math.max(0, (now - this.lastRefillMs) / 1000);
    if (elapsedSec > 0) {
      this.tokens = Math.min(this.burstLimit, this.tokens + elapsedSec * this.eventsPerSecond);
      this.lastRefillMs = now;
    }
  }

  tryCapture(eventName: string, count = 1): CaptureOutcome {
    this.refill();
    if (this.tokens >= count) {
      this.tokens -= count;
      return { accepted: true, remainingTokens: Number(this.tokens.toFixed(2)) };
    }
    this.ignoredCount += count;
    return {
      accepted: false,
      remainingTokens: Number(this.tokens.toFixed(2)),
      diagnostic: `[Posthog error]: This capture call is ignored due to client rate limiting (event=${eventName}, droppedTotal=${this.ignoredCount}).`,
      recommendedFix:
        "Throttle high-frequency DOM/player events (e.g. timeupdate -> playback milestones), fix runaway React effects, or tune rate_limiting: { events_per_second, events_burst_limit } / server-side /batch ingestion.",
    };
  }
}
