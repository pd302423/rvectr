import {
  type Landmark,
  angleBetweenPoints,
  getHipAngle,
  getKneeAngle,
  getHeelLiftRatio,
  LANDMARKS,
} from "@/lib/cv/angles";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Classifiable form faults detected during a squat rep. */
export type SquatFormFault =
  | "insufficient_depth"
  | "knee_cave"
  | "excessive_forward_lean"
  | "heel_rise"
  | "asymmetry";

/** Per-rep score breakdown returned by {@link gradeSquatRep}. */
export interface SquatRepScore {
  /** Composite score, 0-100. */
  total: number;
  /** Depth sub-score, 0-25. Based on minimum knee angle. */
  depthScore: number;
  /** Hip-knee tracking sub-score, 0-25. Based on minimum hip angle at bottom. */
  hipKneeScore: number;
  /** Torso stability sub-score, 0-25. Based on average torso lean during bottom phase. */
  torsoScore: number;
  /** Symmetry sub-score, 0-25. Based on bilateral knee angle difference. */
  symmetryScore: number;
  /** Detected form faults for this rep. */
  faults: SquatFormFault[];
  /** Lowest knee angle reached (degrees). Lower = deeper squat. */
  minKneeAngle: number;
  /** Lowest hip angle reached (degrees). */
  minHipAngle: number;
  /** Rep duration in milliseconds. */
  duration: number;
}

/** Extracted angle data from a single pose frame, used as input to grading. */
export interface SquatFrameData {
  /** Left knee angle — hip → knee → ankle (degrees). */
  leftKnee: number;
  /** Right knee angle — hip → knee → ankle (degrees). */
  rightKnee: number;
  /** Left hip angle — shoulder → hip → knee (degrees). */
  leftHip: number;
  /** Right hip angle — shoulder → hip → knee (degrees). */
  rightHip: number;
  /** Torso lean from vertical (degrees). 0° = perfectly upright. */
  torsoLean: number;
  /** Left heel lift ratio (normalized, >0.35 indicates lifted heel). */
  leftHeelLift?: number;
  /** Right heel lift ratio (normalized, >0.35 indicates lifted heel). */
  rightHeelLift?: number;
  /** Frame capture timestamp (ms, monotonic). */
  timestamp: number;
}

// ---------------------------------------------------------------------------
// Angle extraction
// ---------------------------------------------------------------------------

/**
 * Measures the angle of the torso relative to vertical.
 *
 * Constructs a torso vector from the midpoint of both hips to the midpoint of
 * both shoulders, then computes the angle between that vector and the vertical
 * axis (straight up = 0°).
 *
 * @returns Torso lean in degrees. 0° = perfectly upright, 90° = horizontal.
 */
export function calculateTorsoLean(landmarks: Landmark[]): number {
  const lShoulder = landmarks[LANDMARKS.LEFT_SHOULDER];
  const rShoulder = landmarks[LANDMARKS.RIGHT_SHOULDER];
  const lHip = landmarks[LANDMARKS.LEFT_HIP];
  const rHip = landmarks[LANDMARKS.RIGHT_HIP];

  if (!lShoulder || !rShoulder || !lHip || !rHip) return 0;

  // Midpoints
  const midShoulderX = (lShoulder.x + rShoulder.x) / 2;
  const midShoulderY = (lShoulder.y + rShoulder.y) / 2;
  const midHipX = (lHip.x + rHip.x) / 2;
  const midHipY = (lHip.y + rHip.y) / 2;

  // Torso vector (hip → shoulder). In screen-space Y increases downward,
  // so "up" is negative-Y. We measure the angle between the torso vector
  // and the true vertical (0, -1).
  const dx = midShoulderX - midHipX;
  const dy = midShoulderY - midHipY;

  // Vertical reference: (0, -1) in screen-space (straight up).
  // cos(θ) = dot(torso, vertical) / |torso|
  // dot = dx * 0 + dy * (-1) = -dy
  const magnitude = Math.sqrt(dx * dx + dy * dy);
  if (magnitude === 0) return 0;

  let cosTheta = -dy / magnitude;
  cosTheta = Math.max(-1, Math.min(1, cosTheta));

  return (Math.acos(cosTheta) * 180) / Math.PI;
}

/**
 * Extracts all biomechanically relevant squat angles from a single frame
 * of MediaPipe Pose landmarks.
 *
 * @param landmarks  33-landmark array from MediaPipe Pose.
 * @returns Structured angle data for this frame. Timestamp defaults to 0;
 *          the caller should overwrite it with the actual capture time.
 */
export function extractSquatFrame(landmarks: Landmark[]): SquatFrameData {
  return {
    leftKnee: getKneeAngle(landmarks, "left"),
    rightKnee: getKneeAngle(landmarks, "right"),
    leftHip: getHipAngle(landmarks, "left"),
    rightHip: getHipAngle(landmarks, "right"),
    torsoLean: calculateTorsoLean(landmarks),
    leftHeelLift: getHeelLiftRatio(landmarks, "left"),
    rightHeelLift: getHeelLiftRatio(landmarks, "right"),
    timestamp: 0,
  };
}

// ---------------------------------------------------------------------------
// Internal scoring helpers
// ---------------------------------------------------------------------------

/**
 * Linear interpolation between two score boundaries.
 * Returns `highScore` when `value ≤ lowThreshold`, `lowScore` when
 * `value ≥ highThreshold`, and interpolates linearly between them.
 */
function linearScale(
  value: number,
  lowThreshold: number,
  highThreshold: number,
  highScore: number,
  lowScore: number,
): number {
  if (value <= lowThreshold) return highScore;
  if (value >= highThreshold) return lowScore;
  const t = (value - lowThreshold) / (highThreshold - lowThreshold);
  return highScore + t * (lowScore - highScore);
}

/**
 * Computes the depth sub-score (0-25).
 *
 * | Min knee angle | Score |
 * |----------------|-------|
 * | ≤ 90°          | 25    |
 * | 90–120°        | 25→10 |
 * | 120–140°       | 10→0  |
 * | > 140°         | 0     |
 */
function scoreDepth(minKneeAngle: number): number {
  if (minKneeAngle <= 90) return 25;
  if (minKneeAngle <= 120) return linearScale(minKneeAngle, 90, 120, 25, 10);
  if (minKneeAngle <= 140) return linearScale(minKneeAngle, 120, 140, 10, 0);
  return 0;
}

/**
 * Computes the hip-knee tracking sub-score (0-25).
 *
 * | Min hip angle | Score |
 * |---------------|-------|
 * | ≤ 100°        | 25    |
 * | 100–130°      | 25→10 |
 * | > 130°        | 10→0  |
 */
function scoreHipKnee(minHipAngle: number): number {
  if (minHipAngle <= 100) return 25;
  if (minHipAngle <= 130) return linearScale(minHipAngle, 100, 130, 25, 10);
  // Graceful degradation above 130° — treat 160° as the effective floor.
  if (minHipAngle <= 160) return linearScale(minHipAngle, 130, 160, 10, 0);
  return 0;
}

/**
 * Computes the torso stability sub-score (0-25).
 *
 * Evaluates average torso lean during the bottom phase (knee < 110°).
 * The ideal range is 15–45°. Outside this window, a linear penalty applies
 * until 5° / 60° where the score reaches 0.
 */
function scoreTorso(avgLeanBottom: number): number {
  if (avgLeanBottom >= 15 && avgLeanBottom <= 45) return 25;

  // Too upright
  if (avgLeanBottom < 15) {
    if (avgLeanBottom <= 5) return 0;
    return linearScale(avgLeanBottom, 5, 15, 0, 25);
  }

  // Too forward
  if (avgLeanBottom >= 60) return 0;
  return linearScale(avgLeanBottom, 45, 60, 25, 0);
}

/**
 * Computes the symmetry sub-score (0-25).
 *
 * | Avg |L-R knee| diff | Score |
 * |---------------------|-------|
 * | < 5°                | 25    |
 * | 5–15°               | 25→10 |
 * | > 15°               | 10→0  |
 */
function scoreSymmetry(avgKneeDiff: number): number {
  if (avgKneeDiff < 5) return 25;
  if (avgKneeDiff <= 15) return linearScale(avgKneeDiff, 5, 15, 25, 10);
  // Graceful degradation — treat 25° as floor.
  if (avgKneeDiff <= 25) return linearScale(avgKneeDiff, 15, 25, 10, 0);
  return 0;
}

// ---------------------------------------------------------------------------
// Grading
// ---------------------------------------------------------------------------

/**
 * Grades a single squat rep from its collected frame data.
 *
 * Expects an array of {@link SquatFrameData} captured between the start of
 * descent and return to standing. At minimum, two frames are required.
 *
 * The composite score is the sum of four equally-weighted sub-scores
 * (depth, hip-knee tracking, torso stability, symmetry), each scored 0-25.
 *
 * @param frames  Ordered frame data for one complete rep.
 * @returns Detailed score breakdown and detected faults.
 */
export function gradeSquatRep(frames: SquatFrameData[]): SquatRepScore {
  const empty: SquatRepScore = {
    total: 0,
    depthScore: 0,
    hipKneeScore: 0,
    torsoScore: 0,
    symmetryScore: 0,
    faults: [],
    minKneeAngle: 180,
    minHipAngle: 180,
    duration: 0,
  };

  if (frames.length < 2) return empty;

  // --------------------------------------------------
  // 1. Aggregate metrics across all frames
  // --------------------------------------------------

  let minKneeAngle = Infinity;
  let minHipAngle = Infinity;
  let totalKneeDiff = 0;

  // Bottom-phase accumulators (knee < 110°)
  let bottomLeanSum = 0;
  let bottomFrameCount = 0;
  let heelLiftFramesCount = 0;

  for (let i = 0; i < frames.length; i++) {
    const f = frames[i];
    const avgKnee = (f.leftKnee + f.rightKnee) / 2;
    const avgHip = (f.leftHip + f.rightHip) / 2;

    // Ignore invalid/occluded landmark readings (angles <= 10°)
    if (avgKnee > 10 && avgKnee < minKneeAngle) minKneeAngle = avgKnee;
    if (avgHip > 10 && avgHip < minHipAngle) minHipAngle = avgHip;

    totalKneeDiff += Math.abs(f.leftKnee - f.rightKnee);

    // Bottom phase analysis
    if (avgKnee < 110) {
      bottomLeanSum += f.torsoLean;
      bottomFrameCount++;

      // Check direct heel elevation relative to toe (lift ratio > 0.35)
      const maxLift = Math.max(f.leftHeelLift ?? 0, f.rightHeelLift ?? 0);
      if (maxLift > 0.35) {
        heelLiftFramesCount++;
      }
    }
  }

  // Flag heel rise only if significant heel lift is sustained during bottom phase
  const heelRiseDetected =
    bottomFrameCount >= 2 &&
    (heelLiftFramesCount >= 2 || (bottomFrameCount > 0 && heelLiftFramesCount / bottomFrameCount > 0.2));

  const avgKneeDiff = totalKneeDiff / frames.length;
  const avgLeanBottom =
    bottomFrameCount > 0 ? bottomLeanSum / bottomFrameCount : 0;
  const duration =
    frames[frames.length - 1].timestamp - frames[0].timestamp;

  // --------------------------------------------------
  // 2. Compute sub-scores
  // --------------------------------------------------

  const depthScore = Math.round(scoreDepth(minKneeAngle) * 10) / 10;
  const hipKneeScore = Math.round(scoreHipKnee(minHipAngle) * 10) / 10;
  const torsoScore =
    bottomFrameCount > 0
      ? Math.round(scoreTorso(avgLeanBottom) * 10) / 10
      : 0;
  const symmetryScore = Math.round(scoreSymmetry(avgKneeDiff) * 10) / 10;
  const total =
    Math.round((depthScore + hipKneeScore + torsoScore + symmetryScore) * 10) /
    10;

  // --------------------------------------------------
  // 3. Fault detection
  // --------------------------------------------------

  const faults: SquatFormFault[] = [];

  if (minKneeAngle > 100) {
    faults.push("insufficient_depth");
  }

  if (bottomFrameCount > 0 && avgLeanBottom > 50) {
    faults.push("excessive_forward_lean");
  }

  if (avgKneeDiff > 10) {
    faults.push("asymmetry");
  }

  if (heelRiseDetected) {
    faults.push("heel_rise");
  }

  // --------------------------------------------------
  // 4. Assemble result
  // --------------------------------------------------

  return {
    total,
    depthScore,
    hipKneeScore,
    torsoScore,
    symmetryScore,
    faults,
    minKneeAngle: Math.round(minKneeAngle * 10) / 10,
    minHipAngle: Math.round(minHipAngle * 10) / 10,
    duration,
  };
}
