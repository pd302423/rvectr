import type { Landmark } from "@/lib/cv/angles";
import { getKneeAngle } from "@/lib/cv/angles";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Phases of a single squat repetition. */
export type RepPhase = "standing" | "descending" | "bottom" | "ascending";

/** Emitted when a full rep cycle completes (ascending → standing). */
export interface RepEvent {
  repNumber: number;
  startTime: number;
  endTime: number;
  phase: RepPhase;
}

/**
 * Immutable snapshot of the rep-counter state machine.
 *
 * All transition logic is driven by `updateRepCounter`, which returns a
 * **new** state object on every frame — the caller never mutates this
 * directly.
 */
export interface RepCounterState {
  /** Current phase of the squat cycle. */
  phase: RepPhase;
  /** Total completed reps since initialisation. */
  repCount: number;
  /** Timestamp (ms) when the current phase was entered. */
  phaseEnteredAt: number;
  /** Raw knee angle from the most recent frame (degrees). */
  currentKneeAngle: number;
  /** Minimum knee angle observed during the current rep attempt. */
  minKneeAngleThisRep: number;
  /** Timestamp (ms) when the current rep attempt began (descent start). */
  repStartTime: number;
  /** Rolling buffer of the last 5 frames used for smoothed decisions. */
  frameBuffer: Array<{ kneeAngle: number; timestamp: number }>;
}

// ---------------------------------------------------------------------------
// Thresholds
// ---------------------------------------------------------------------------

/** Knee angle above which the athlete is considered standing. */
const STANDING_THRESHOLD = 150;

/** Hysteresis gap: knee must drop below this to leave standing. */
const DESCENDING_ENTRY_THRESHOLD = 145;

/** Knee angle below which the athlete is at the bottom of the squat. */
const BOTTOM_THRESHOLD = 100;

/** Hysteresis gap: knee must rise above this to leave bottom. */
const ASCENDING_ENTRY_THRESHOLD = 105;

/** Minimum dwell time (ms) before standing → descending transition. */
const DESCENDING_HOLD_MS = 150;

/** Minimum dwell time (ms) before descending → bottom transition. */
const BOTTOM_HOLD_MS = 100;

/** Minimum dwell time (ms) before bottom → ascending transition. */
const ASCENDING_HOLD_MS = 100;

/** Minimum dwell time (ms) before ascending → standing (rep complete). */
const STANDING_HOLD_MS = 150;

/** Number of frames retained in the smoothing buffer. */
const BUFFER_SIZE = 5;

// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------

/**
 * Creates an initial rep-counter state.
 *
 * The counter starts in the `standing` phase with zero completed reps and
 * an empty frame buffer.
 */
export function createRepCounter(): RepCounterState {
  return {
    phase: "standing",
    repCount: 0,
    phaseEnteredAt: 0,
    currentKneeAngle: 180,
    minKneeAngleThisRep: 180,
    repStartTime: 0,
    frameBuffer: [],
  };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Computes the arithmetic mean of buffered knee-angle readings.
 *
 * If the buffer is empty the raw `fallback` value is returned instead.
 */
function averageBufferAngle(
  buffer: RepCounterState["frameBuffer"],
  fallback: number,
): number {
  if (buffer.length === 0) return fallback;
  const sum = buffer.reduce((acc, f) => acc + f.kneeAngle, 0);
  return sum / buffer.length;
}

/**
 * Returns a new frame buffer with `entry` appended, trimmed to
 * {@link BUFFER_SIZE} most-recent entries.
 */
function pushFrame(
  buffer: RepCounterState["frameBuffer"],
  entry: { kneeAngle: number; timestamp: number },
): RepCounterState["frameBuffer"] {
  const next = [...buffer, entry];
  return next.length > BUFFER_SIZE ? next.slice(next.length - BUFFER_SIZE) : next;
}

// ---------------------------------------------------------------------------
// State machine
// ---------------------------------------------------------------------------

/**
 * Pure update function for the squat rep-counter state machine.
 *
 * Call this once per video / pose-estimation frame with the latest knee
 * angle and a monotonic timestamp. It returns a **new** state object plus a
 * flag indicating whether a rep just completed on this frame.
 *
 * ### Transition graph
 *
 * ```
 * standing ──(knee < 145° for 150 ms)──▶ descending
 * descending ──(knee < 100° for 100 ms)──▶ bottom
 * bottom ──(knee > 105° for 100 ms)──▶ ascending
 * ascending ──(knee > 150° for 150 ms)──▶ standing  ← rep counted here
 * ```
 *
 * @param state     - Current counter state (not mutated).
 * @param kneeAngle - Raw knee-joint angle in degrees for this frame.
 * @param timestamp - Frame timestamp in milliseconds.
 * @returns Updated state and whether a rep was just completed.
 */
export function updateRepCounter(
  state: RepCounterState,
  kneeAngle: number,
  timestamp: number,
): { state: RepCounterState; repCompleted: boolean } {
  // 1. Update the rolling frame buffer and compute a smoothed angle.
  const nextBuffer = pushFrame(state.frameBuffer, { kneeAngle, timestamp });
  const smoothed = averageBufferAngle(nextBuffer, kneeAngle);

  // 2. Track the deepest knee angle observed during this rep attempt.
  const minKnee = Math.min(state.minKneeAngleThisRep, kneeAngle);

  // 3. Start with an unchanged next-state, then evaluate transitions.
  let nextPhase: RepPhase = state.phase;
  let nextPhaseEnteredAt = state.phaseEnteredAt;
  let nextRepCount = state.repCount;
  let nextRepStartTime = state.repStartTime;
  let nextMinKnee = minKnee;
  let repCompleted = false;

  const elapsed = timestamp - state.phaseEnteredAt;

  switch (state.phase) {
    // -----------------------------------------------------------------
    // STANDING  →  knee drops below hysteresis band for ≥ 150 ms
    // -----------------------------------------------------------------
    case "standing": {
      if (smoothed < DESCENDING_ENTRY_THRESHOLD && elapsed >= DESCENDING_HOLD_MS) {
        nextPhase = "descending";
        nextPhaseEnteredAt = timestamp;
        nextRepStartTime = timestamp;
        nextMinKnee = kneeAngle; // reset for the new rep
      }
      break;
    }

    // -----------------------------------------------------------------
    // DESCENDING  →  knee drops below bottom threshold for ≥ 100 ms
    // -----------------------------------------------------------------
    case "descending": {
      if (smoothed < BOTTOM_THRESHOLD && elapsed >= BOTTOM_HOLD_MS) {
        nextPhase = "bottom";
        nextPhaseEnteredAt = timestamp;
      }
      break;
    }

    // -----------------------------------------------------------------
    // BOTTOM  →  knee rises above hysteresis band for ≥ 100 ms
    // -----------------------------------------------------------------
    case "bottom": {
      if (smoothed > ASCENDING_ENTRY_THRESHOLD && elapsed >= ASCENDING_HOLD_MS) {
        nextPhase = "ascending";
        nextPhaseEnteredAt = timestamp;
      }
      break;
    }

    // -----------------------------------------------------------------
    // ASCENDING  →  knee returns above standing threshold for ≥ 150 ms
    //               This completes one full rep.
    // -----------------------------------------------------------------
    case "ascending": {
      if (smoothed > STANDING_THRESHOLD && elapsed >= STANDING_HOLD_MS) {
        nextPhase = "standing";
        nextPhaseEnteredAt = timestamp;
        nextRepCount = state.repCount + 1;
        nextMinKnee = 180; // reset for next rep
        repCompleted = true;
      }
      break;
    }
  }

  return {
    state: {
      phase: nextPhase,
      repCount: nextRepCount,
      phaseEnteredAt: nextPhaseEnteredAt,
      currentKneeAngle: kneeAngle,
      minKneeAngleThisRep: nextMinKnee,
      repStartTime: nextRepStartTime,
      frameBuffer: nextBuffer,
    },
    repCompleted,
  };
}
